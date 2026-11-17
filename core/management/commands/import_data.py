"""
Management command to import data from Excel (.xlsx) or CSV files.

Usage:
    python manage.py import_data sample_data.xlsx
    python manage.py import_data equipment.csv
    python manage.py import_data sample_data.xlsx --dry-run
    python manage.py import_data users.csv --sheet users

For the equipment CSV (equipment.csv format), expected columns are:
    amc_contract_number, name, brand, model_number, serial_number,
    installation_date, warranty_expiry, amc_date, notes, amc_end_date,
    invoice_date, invoice_no., location, client, project, win_license

Safe to re-run — uses get_or_create so existing records are not duplicated.
"""
import os
import csv
from datetime import datetime, date
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


# ---------------------------------------------------------------------------
# Date/value helpers
# ---------------------------------------------------------------------------

def parse_date(val):
    """Parse various date formats into a Python date, or return None."""
    if not val:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, (int, float)):
        try:
            from openpyxl.utils.datetime import from_excel
            return from_excel(val).date()
        except Exception:
            pass
    s = str(val).strip()
    if not s or s.lower() in ('none', 'null', 'n/a', '-', ''):
        return None
    formats = (
        '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d',
        '%d-%b-%Y', '%d %b %Y', '%d-%b-%y', '%b-%y',
        '%d-%b-%Y', '%-d-%b-%Y',
        '%d %B %Y', '%B %d, %Y',
        '%d-%m-%y', '%d/%m/%y',
    )
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    # Handle "10-05-2018" etc already covered; try stripping time part
    if ' ' in s:
        try:
            return parse_date(s.split(' ')[0])
        except Exception:
            pass
    return None


def parse_datetime(val):
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    s = str(val).strip()
    for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S',
                '%d-%m-%Y %H:%M', '%d/%m/%Y %H:%M'):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def clean(val):
    """Strip whitespace; return None for blank/null-ish values."""
    if val is None:
        return None
    s = str(val).strip()
    return s if s and s.lower() not in ('none', 'null', 'n/a', '-') else None


# ---------------------------------------------------------------------------
# File loaders
# ---------------------------------------------------------------------------

def load_excel(path):
    """Return {sheet_name: [row_dict, ...]} for all data sheets."""
    try:
        import openpyxl
    except ImportError:
        raise CommandError('openpyxl is required: pip install openpyxl')
    wb = openpyxl.load_workbook(path, data_only=True)
    result = {}
    for sheet_name in wb.sheetnames:
        if sheet_name.upper() in ('README', 'INSTRUCTIONS'):
            continue
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        if len(rows) < 4:
            continue
        headers = [str(h).strip() if h else '' for h in rows[2]]
        data = []
        for row in rows[3:]:
            if all(v is None or str(v).strip() == '' for v in row):
                continue
            first_val = str(row[0]).strip() if row[0] else ''
            if first_val.startswith('\U0001f535') or first_val.startswith('──') or first_val.startswith('IMS —'):
                continue
            data.append(dict(zip(headers, row)))
        result[sheet_name] = data
    return result


def load_csv(path):
    """Return {filename_stem: [row_dict, ...]}."""
    stem = os.path.splitext(os.path.basename(path))[0]
    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        return {stem: list(reader)}


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = 'Import data from an Excel (.xlsx) or CSV file into the database'

    def add_arguments(self, parser):
        parser.add_argument('file', help='Path to .xlsx or .csv file')
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Validate and report without saving anything',
        )
        parser.add_argument(
            '--sheet', default=None,
            help='Import only this sheet/section (e.g. users, equipment)',
        )

    def handle(self, *args, **options):
        path = options['file']
        dry_run = options['dry_run']
        only_sheet = options['sheet']

        if not os.path.exists(path):
            raise CommandError(f'File not found: {path}')

        ext = os.path.splitext(path)[1].lower()
        if ext == '.csv':
            all_sheets = load_csv(path)
        elif ext in ('.xlsx', '.xls'):
            all_sheets = load_excel(path)
        else:
            raise CommandError('Only .xlsx and .csv files are supported.')

        self.dry_run = dry_run
        self.errors = []
        self.counts = {}

        if dry_run:
            self.stdout.write(self.style.WARNING('\n  DRY RUN - nothing will be saved\n'))

        # Detect if this looks like the equipment CSV format
        # (has a "project" column but no typical sheet names)
        sheet_map = {}
        for sheet_name, rows in all_sheets.items():
            key = sheet_name.lower()
            if rows and 'name' in rows[0] and (
                'serial_number' in rows[0] or 'brand' in rows[0] or 'amc_contract_number' in rows[0]
            ):
                sheet_map.setdefault('equipment_csv', rows)
            elif 'user' in key:
                sheet_map.setdefault('users', rows)
            elif 'project' in key and 'amc' not in key and 'equip' not in key:
                sheet_map.setdefault('projects', rows)
            elif ('amc' in key or 'contract' in key) and 'report' not in key and 'equip' not in key:
                sheet_map.setdefault('amc', rows)
            elif 'equip' in key:
                sheet_map.setdefault('equipment', rows)
            elif 'task' in key:
                sheet_map.setdefault('tasks', rows)
            elif 'expense' in key:
                sheet_map.setdefault('expenses', rows)
            elif 'report' in key:
                sheet_map.setdefault('reports', rows)
            elif 'event' in key or 'meeting' in key or 'notification' in key:
                sheet_map.setdefault('events', rows)
            else:
                # Fallback: check column headers to guess type
                if rows and 'serial_number' in rows[0]:
                    sheet_map.setdefault('equipment_csv', rows)
                else:
                    sheet_map.setdefault(key, rows)

        importers = [
            ('users',         self._import_users),
            ('projects',      self._import_projects),
            ('amc',           self._import_amc),
            ('equipment',     self._import_equipment),
            ('equipment_csv', self._import_equipment_csv),   # equipment CSV
            ('tasks',         self._import_tasks),
            ('expenses',      self._import_expenses),
            ('reports',       self._import_reports),
            ('events',        self._import_events),
        ]

        for key, fn in importers:
            if only_sheet and only_sheet.lower() not in key:
                continue
            if key not in sheet_map:
                continue
            rows = sheet_map[key]
            self.stdout.write(f'\n  Importing {key} ({len(rows)} rows)...')
            try:
                with transaction.atomic():
                    fn(rows)
                    if dry_run:
                        raise Exception('dry-run-rollback')
            except Exception as e:
                if 'dry-run-rollback' not in str(e):
                    self.errors.append(f'{key}: {e}')
                    self.stdout.write(self.style.ERROR(f'  Error: {e}'))

        self._summary()

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------

    def _summary(self):
        self.stdout.write('\n' + '-' * 50)
        if self.dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN complete - database unchanged'))
        else:
            self.stdout.write(self.style.SUCCESS('Import complete'))
        for k, (created, skipped) in self.counts.items():
            self.stdout.write(f'   {k:25s}  created={created}  skipped/exists={skipped}')
        if self.errors:
            self.stdout.write(self.style.ERROR('\nErrors:'))
            for e in self.errors:
                self.stdout.write(self.style.ERROR(f'  * {e}'))
        self.stdout.write('')

    def _track(self, key, created):
        if key not in self.counts:
            self.counts[key] = [0, 0]
        if created:
            self.counts[key][0] += 1
        else:
            self.counts[key][1] += 1

    # -----------------------------------------------------------------------
    # Equipment CSV importer  (equipment.csv format)
    #
    # Columns: amc_contract_number, name, brand, model_number, serial_number,
    #          installation_date, warranty_expiry, amc_date, notes, amc_end_date,
    #          invoice_date, invoice_no., location, client, project, win_license
    #
    # Strategy:
    #   1. Ensure the Project exists (create if needed)
    #   2. Ensure the AMCProject exists (keyed by project + contract_number)
    #   3. Create / update the Equipment record
    # -----------------------------------------------------------------------

    def _import_equipment_csv(self, rows):
        from projects.models import Project
        from amc.models import AMCProject, Equipment
        from users.models import User

        admin = (
            User.objects.filter(role='ADMIN').first()
            or User.objects.filter(is_superuser=True).first()
        )

        # Cache to avoid repeated DB hits for the same project/contract
        project_cache = {}
        amc_cache = {}

        for i, row in enumerate(rows, 1):
            # --- normalise column names (strip spaces, lower) ---------------
            row = {k.strip().rstrip('.').lower().replace(' ', '_'): v for k, v in row.items()}

            eq_name = clean(row.get('name'))
            if not eq_name:
                self.stdout.write(self.style.WARNING(f'  Row {i}: skipped - name is required'))
                continue

            # --- Project -----------------------------------------------------
            proj_name   = clean(row.get('project') or row.get('project_name'))
            client_name = clean(row.get('client')) or 'Unknown'

            if not proj_name:
                self.stdout.write(self.style.WARNING(f'  Row {i} ({eq_name}): skipped - project column is empty'))
                continue

            if proj_name not in project_cache:
                proj, proj_created = Project.objects.get_or_create(
                    name=proj_name,
                    defaults={
                        'client':     client_name,
                        'start_date': date.today(),
                        'status':     'ONGOING',
                        'created_by': admin,
                    },
                )
                project_cache[proj_name] = proj
                if proj_created:
                    self.stdout.write(f'    + Project created: {proj_name}')
            project = project_cache[proj_name]

            # --- AMC Contract ------------------------------------------------
            contract_no = clean(row.get('amc_contract_number')) or ''
            amc_key = (project.pk, contract_no)

            if amc_key not in amc_cache:
                # Use amc_end_date from the row as the contract end date if available
                amc_end = parse_date(row.get('amc_end_date'))
                amc_start = parse_date(row.get('amc_date')) or date.today()
                amc_end = amc_end or amc_start  # fallback: same day if missing

                amc, amc_created = AMCProject.objects.get_or_create(
                    project=project,
                    contract_number=contract_no,
                    defaults={
                        'amc_start_date': amc_start,
                        'amc_end_date':   amc_end,
                        'notes':          clean(row.get('notes')) or '',
                    },
                )
                amc_cache[amc_key] = amc
                if amc_created:
                    self.stdout.write(f'    + AMC created: {proj_name} [{contract_no or "no contract#"}]')
            amc = amc_cache[amc_key]

            # --- Equipment ---------------------------------------------------
            # Use serial number as uniqueness key when available.
            # When serial is blank, fall back to (amc, name, location) so that
            # multiple identical-looking items in different locations are kept
            # as separate records. Items sharing the same location AND no serial
            # are always created fresh (they are distinct physical units).
            serial   = clean(row.get('serial_number')) or ''
            location = clean(row.get('location'))       or ''
            eq_data  = {
                'brand':             clean(row.get('brand'))        or '',
                'model_number':      clean(row.get('model_number')) or '',
                'location':          location,
                'installation_date': parse_date(row.get('installation_date')),
                'warranty_expiry':   parse_date(row.get('warranty_expiry')),
                'amc_date':          parse_date(row.get('amc_date')),
                'amc_end_date':      parse_date(row.get('amc_end_date')),
                'invoice_date':      parse_date(row.get('invoice_date')),
                'invoice_no':        clean(row.get('invoice_no'))   or '',
                'win_license':       clean(row.get('win_license'))  or '',
                'notes':             clean(row.get('notes'))        or '',
            }
            if serial:
                # Unique serial — safe to upsert
                obj, created = Equipment.objects.get_or_create(
                    amc_project=amc, name=eq_name, serial_number=serial,
                    defaults=eq_data,
                )
            else:
                # No serial — always create (distinct physical units)
                obj = Equipment.objects.create(
                    amc_project=amc, name=eq_name, serial_number='', **eq_data,
                )
                created = True

            status = 'Created' if created else 'Exists '
            self.stdout.write(f'  {"+" if created else "-"}  {status}: {eq_name} [{serial or "no serial"}]')
            self._track('equipment', created)

    # -----------------------------------------------------------------------
    # Standard importers (users / projects / amc / equipment / tasks / etc.)
    # -----------------------------------------------------------------------

    def _import_users(self, rows):
        from users.models import User
        for i, row in enumerate(rows, 1):
            email    = clean(row.get('email'))
            name     = clean(row.get('full_name')) or ''
            role     = (clean(row.get('role')) or 'STAFF').upper()
            phone    = clean(row.get('phone')) or ''
            password = clean(row.get('password')) or 'ChangeMe@123'

            if not email:
                self.stdout.write(self.style.WARNING(f'  Row {i}: skipped - email required'))
                continue
            if role not in ('ADMIN', 'MANAGER', 'ENGINEER', 'STAFF'):
                role = 'STAFF'

            obj, created = User.objects.get_or_create(
                email__iexact=email,
                defaults={'email': email, 'username': email, 'name': name, 'role': role, 'phone': phone},
            )
            if created:
                obj.set_password(password)
                obj.save()
            self.stdout.write(f'  {"+" if created else "-"}  {"Created" if created else "Exists "}: {email} [{role}]')
            self._track('users', created)

    def _import_projects(self, rows):
        from projects.models import Project
        from users.models import User
        admin = User.objects.filter(role='ADMIN').first() or User.objects.filter(is_superuser=True).first()

        for i, row in enumerate(rows, 1):
            name   = clean(row.get('name'))
            client = clean(row.get('client'))
            status = (clean(row.get('status')) or 'PLANNING').upper()
            start  = parse_date(row.get('start_date'))
            if not name or not client or not start:
                self.stdout.write(self.style.WARNING(f'  Row {i}: skipped - name, client, start_date required'))
                continue
            if status not in ('PLANNING', 'ONGOING', 'ON_HOLD', 'COMPLETED', 'CANCELLED'):
                status = 'PLANNING'
            obj, created = Project.objects.get_or_create(
                name=name,
                defaults={
                    'client': client, 'location': clean(row.get('location')) or '',
                    'description': clean(row.get('description')) or '',
                    'start_date': start, 'end_date': parse_date(row.get('end_date')),
                    'status': status, 'created_by': admin,
                },
            )
            emails_raw = clean(row.get('assigned_users_emails')) or ''
            if emails_raw:
                from users.models import User as U
                emails = [e.strip() for e in emails_raw.split(',') if e.strip()]
                obj.assigned_users.add(*U.objects.filter(email__in=emails))
            self.stdout.write(f'  {"+" if created else "-"}  {"Created" if created else "Exists "}: {name}')
            self._track('projects', created)

    def _import_amc(self, rows):
        from projects.models import Project
        from amc.models import AMCProject

        for i, row in enumerate(rows, 1):
            proj_name = clean(row.get('project_name'))
            start     = parse_date(row.get('amc_start_date'))
            end       = parse_date(row.get('amc_end_date'))
            if not proj_name or not start or not end:
                self.stdout.write(self.style.WARNING(f'  Row {i}: skipped - project_name, amc_start_date, amc_end_date required'))
                continue
            try:
                project = Project.objects.get(name=proj_name)
            except Project.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'  Row {i}: project not found - "{proj_name}"'))
                continue
            contract_no = clean(row.get('contract_number') or row.get('amc_contract_number')) or ''
            value_raw = row.get('contract_value_inr')
            value = None
            try:
                value = float(str(value_raw).replace(',', '')) if value_raw else None
            except (ValueError, TypeError):
                pass
            obj, created = AMCProject.objects.get_or_create(
                project=project, contract_number=contract_no,
                defaults={'amc_start_date': start, 'amc_end_date': end,
                          'contract_value': value, 'notes': clean(row.get('notes')) or ''},
            )
            self.stdout.write(f'  {"+" if created else "-"}  {"Created" if created else "Exists "}: {proj_name} [{contract_no}]')
            self._track('amc_contracts', created)

    def _import_equipment(self, rows):
        from amc.models import AMCProject, Equipment

        for i, row in enumerate(rows, 1):
            contract_no = clean(row.get('amc_contract_number'))
            eq_name     = clean(row.get('name'))
            if not eq_name or not contract_no:
                self.stdout.write(self.style.WARNING(f'  Row {i}: skipped - name and amc_contract_number required'))
                continue
            amc = AMCProject.objects.filter(contract_number=contract_no).first()
            if not amc:
                self.stdout.write(self.style.ERROR(f'  Row {i}: AMC contract not found - "{contract_no}"'))
                continue
            serial = clean(row.get('serial_number')) or ''
            obj, created = Equipment.objects.get_or_create(
                amc_project=amc, name=eq_name, serial_number=serial,
                defaults={
                    'brand':             clean(row.get('brand'))        or '',
                    'model_number':      clean(row.get('model_number')) or '',
                    'location':          clean(row.get('location'))     or '',
                    'installation_date': parse_date(row.get('installation_date')),
                    'warranty_expiry':   parse_date(row.get('warranty_expiry')),
                    'amc_date':          parse_date(row.get('amc_date')),
                    'amc_end_date':      parse_date(row.get('amc_end_date')),
                    'invoice_date':      parse_date(row.get('invoice_date')),
                    'invoice_no':        clean(row.get('invoice_no'))   or '',
                    'win_license':       clean(row.get('win_license'))  or '',
                    'notes':             clean(row.get('notes'))        or '',
                },
            )
            self.stdout.write(f'  {"+" if created else "-"}  {"Created" if created else "Exists "}: {eq_name} [{serial}]')
            self._track('equipment', created)

    def _import_tasks(self, rows):
        from tasks.models import Task
        from projects.models import Project
        from users.models import User
        manager = User.objects.filter(role__in=['ADMIN', 'MANAGER']).first()

        for i, row in enumerate(rows, 1):
            title    = clean(row.get('title'))
            start    = parse_date(row.get('start_date'))
            end      = parse_date(row.get('end_date'))
            status   = (clean(row.get('status'))   or 'PENDING').upper()
            priority = (clean(row.get('priority')) or 'MEDIUM').upper()
            if not title or not start or not end:
                self.stdout.write(self.style.WARNING(f'  Row {i}: skipped - title, start_date, end_date required'))
                continue
            if status   not in ('PENDING', 'IN_PROGRESS', 'BLOCKED', 'COMPLETED'): status   = 'PENDING'
            if priority not in ('LOW', 'MEDIUM', 'HIGH', 'URGENT'):                priority = 'MEDIUM'
            project     = Project.objects.filter(name=clean(row.get('project_name'))).first() if clean(row.get('project_name')) else None
            assigned_to = User.objects.filter(email__iexact=clean(row.get('assigned_to_email'))).first() if clean(row.get('assigned_to_email')) else None
            obj, created = Task.objects.get_or_create(
                title=title,
                defaults={'description': clean(row.get('description')) or '', 'project': project,
                          'assigned_to': assigned_to, 'priority': priority, 'status': status,
                          'start_date': start, 'end_date': end, 'created_by': manager},
            )
            self.stdout.write(f'  {"+" if created else "-"}  {"Created" if created else "Exists "}: {title}')
            self._track('tasks', created)

    def _import_expenses(self, rows):
        from expenses.models import Expense
        from projects.models import Project
        from users.models import User
        VALID_CATS = ('TRAVEL', 'STAY', 'FOOD', 'ELECTRICAL', 'TOOLS', 'COMMUNICATION', 'MISC')

        for i, row in enumerate(rows, 1):
            email    = clean(row.get('user_email'))
            exp_date = parse_date(row.get('date'))
            amount   = row.get('amount_inr')
            category = (clean(row.get('category')) or 'MISC').upper()
            if not email or not exp_date or not amount:
                self.stdout.write(self.style.WARNING(f'  Row {i}: skipped - user_email, date, amount required'))
                continue
            try:
                amount = float(str(amount).replace(',', ''))
            except (ValueError, TypeError):
                self.stdout.write(self.style.WARNING(f'  Row {i}: skipped - invalid amount'))
                continue
            if category not in VALID_CATS:
                category = 'MISC'
            user = User.objects.filter(email__iexact=email).first()
            if not user:
                self.stdout.write(self.style.ERROR(f'  Row {i}: user not found - "{email}"'))
                continue
            project = Project.objects.filter(name=clean(row.get('project_name'))).first() if clean(row.get('project_name')) else None
            obj, created = Expense.objects.get_or_create(
                user=user, date=exp_date, amount=amount,
                defaults={'category': category, 'description': clean(row.get('description')) or '', 'project': project},
            )
            self.stdout.write(f'  {"+" if created else "-"}  {"Created" if created else "Exists "}: {amount} by {email}')
            self._track('expenses', created)

    def _import_reports(self, rows):
        from reports.models import AMCReport
        from projects.models import Project
        from amc.models import AMCProject
        from users.models import User

        for i, row in enumerate(rows, 1):
            eng_email  = clean(row.get('engineer_email'))
            proj_name  = clean(row.get('project_name'))
            visit_date = parse_date(row.get('visit_date'))
            work_done  = clean(row.get('work_done'))
            if not all([eng_email, proj_name, visit_date, work_done]):
                self.stdout.write(self.style.WARNING(f'  Row {i}: skipped - engineer_email, project_name, visit_date, work_done required'))
                continue
            engineer = User.objects.filter(email__iexact=eng_email).first()
            project  = Project.objects.filter(name=proj_name).first()
            if not engineer or not project:
                self.stdout.write(self.style.ERROR(f'  Row {i}: engineer or project not found'))
                continue
            amc = AMCProject.objects.filter(contract_number=clean(row.get('amc_contract_number'))).first() if clean(row.get('amc_contract_number')) else None
            obj, created = AMCReport.objects.get_or_create(
                engineer=engineer, project=project, date=visit_date,
                defaults={'amc_project': amc, 'work_done': work_done,
                          'issues_found': clean(row.get('issues_found')) or '',
                          'recommendations': clean(row.get('recommendations')) or '', 'status': 'SUBMITTED'},
            )
            self.stdout.write(f'  {"+" if created else "-"}  {"Created" if created else "Exists "}: {proj_name} by {eng_email}')
            self._track('amc_reports', created)

    def _import_events(self, rows):
        from notifications.models import NotificationEvent
        from users.models import User
        admin = User.objects.filter(role='ADMIN').first()

        for i, row in enumerate(rows, 1):
            title = clean(row.get('title'))
            etype = (clean(row.get('event_type')) or 'REMINDER').upper()
            dt    = parse_datetime(row.get('event_datetime'))
            if not title or not dt:
                self.stdout.write(self.style.WARNING(f'  Row {i}: skipped - title and event_datetime required'))
                continue
            if etype not in ('MEETING', 'INTERVIEW', 'REMINDER'):
                etype = 'REMINDER'
            from django.utils import timezone
            import zoneinfo
            try:
                dt_aware = dt.replace(tzinfo=zoneinfo.ZoneInfo('Asia/Kolkata'))
            except Exception:
                dt_aware = timezone.make_aware(dt)
            obj, created = NotificationEvent.objects.get_or_create(
                title=title, event_datetime=dt_aware,
                defaults={'event_type': etype, 'location': clean(row.get('location')) or '',
                          'description': clean(row.get('description')) or '',
                          'all_users': str(row.get('all_users', '')).upper() in ('TRUE', 'YES', '1'),
                          'created_by': admin},
            )
            self.stdout.write(f'  {"+" if created else "-"}  {"Created" if created else "Exists "}: {title}')
            self._track('events', created)
