"""
Management command to import Projects and Equipment from the exported CSVs.

Usage:
    python manage.py import_csv_export --projects "Projects CSV.csv"
    python manage.py import_csv_export --equipment Equipment.csv
    python manage.py import_csv_export --projects "Projects CSV.csv" --equipment Equipment.csv
    python manage.py import_csv_export --projects "Projects CSV.csv" --equipment Equipment.csv --dry-run

CSV formats expected
--------------------
Projects CSV columns:
    id, name, client, location, status, start_date, end_date, description,
    created_by, assigned_users, created_at, updated_at, project_official_name

Equipment CSV columns:
    id, amc_project_id, name, brand, model_number, serial_number, location,
    installation_date, warranty_expiry, amc_date, amc_end_date, invoice_date,
    invoice_no, win_license, project_name, client, notes

Safe to re-run — uses update_or_create keyed on the CSV id so records are
updated in place rather than duplicated.
"""

import csv
import re
import os
from datetime import datetime, date
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clean(val):
    """Strip whitespace; return None for blank/null-ish strings."""
    if val is None:
        return None
    s = str(val).strip()
    return s if s and s.lower() not in ('none', 'null', 'n/a', '-', '') else None


def parse_date(val):
    """
    Parse a wide variety of date strings into a Python date, or return None.

    Handles formats such as:
      - 2025-12-25  (ISO)
      - 24-02-2023  (DD-MM-YYYY)
      - 01-Jul-12   (DD-Mon-YY)
      - 9th Oct, 2025  (ordinal with month name)
      - 20th November, 2020
      - 6th Jan 2023
    """
    if not val:
        return None
    if isinstance(val, (datetime,)):
        return val.date()
    if isinstance(val, date):
        return val

    s = str(val).strip()
    if not s or s.lower() in ('none', 'null', 'n/a', '-', ''):
        return None

    # Strip ordinal suffixes: 1st → 1, 2nd → 2, 3rd → 3, 4th → 4 …
    s_clean = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', s, flags=re.IGNORECASE)

    formats = [
        # ISO / numeric
        '%Y-%m-%d',
        '%d-%m-%Y',
        '%d/%m/%Y',
        '%Y/%m/%d',
        '%d-%m-%y',
        '%d/%m/%y',
        # DD-Mon-YYYY / DD-Mon-YY
        '%d-%b-%Y',
        '%d-%b-%y',
        '%d %b %Y',
        '%d %b, %Y',
        '%d %B %Y',
        '%d %B, %Y',
        # Mon-YY
        '%b-%y',
        # Month DD, YYYY
        '%B %d, %Y',
        '%b %d, %Y',
        # DD Month YYYY (after ordinal strip)
        '%d %B %Y',
        '%d %b %Y',
    ]

    for s_try in (s_clean, s):
        for fmt in formats:
            try:
                return datetime.strptime(s_try.strip(), fmt).date()
            except ValueError:
                continue

    # Last resort: try splitting on space and recurse on first part
    if ' ' in s:
        first = s.split(' ')[0]
        if first != s:
            result = parse_date(first)
            if result:
                return result

    return None


STATUS_MAP = {
    'complete':   'COMPLETED',
    'completed':  'COMPLETED',
    'ongoing':    'ONGOING',
    'on hold':    'ON_HOLD',
    'on_hold':    'ON_HOLD',
    'planning':   'PLANNING',
    'cancelled':  'CANCELLED',
    'canceled':   'CANCELLED',
}

VALID_STATUSES = ('PLANNING', 'ONGOING', 'ON_HOLD', 'COMPLETED', 'CANCELLED')


def map_status(raw):
    if not raw:
        return 'PLANNING'
    mapped = STATUS_MAP.get(str(raw).strip().lower(), str(raw).strip().upper())
    return mapped if mapped in VALID_STATUSES else 'PLANNING'


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = 'Import/update Projects and Equipment from exported CSV files'

    def add_arguments(self, parser):
        parser.add_argument('--projects',  type=str, default=None, help='Path to Projects CSV file')
        parser.add_argument('--equipment', type=str, default=None, help='Path to Equipment CSV file')
        parser.add_argument('--dry-run',   action='store_true',    help='Validate without saving')

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.counts  = {}
        self.errors  = []

        if self.dry_run:
            self.stdout.write(self.style.WARNING('\n  DRY RUN — nothing will be saved\n'))

        proj_path = options['projects']
        eq_path   = options['equipment']

        if not proj_path and not eq_path:
            raise CommandError('Provide at least --projects or --equipment (or both).')

        try:
            with transaction.atomic():
                if proj_path:
                    self._import_projects(proj_path)
                if eq_path:
                    self._import_equipment(eq_path)
                if self.dry_run:
                    raise Exception('dry-run-rollback')
        except Exception as exc:
            if 'dry-run-rollback' not in str(exc):
                self.errors.append(str(exc))
                self.stdout.write(self.style.ERROR(f'\n  Fatal error: {exc}'))

        self._summary()

    # -----------------------------------------------------------------------
    # Projects importer
    # -----------------------------------------------------------------------

    def _import_projects(self, path):
        from projects.models import Project

        if not os.path.exists(path):
            raise CommandError(f'Projects file not found: {path}')

        self.stdout.write(f'\n  Importing projects from: {path}')

        with open(path, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.stdout.write(f'  {len(rows)} rows found\n')

        created_count = updated_count = skipped_count = 0

        for i, row in enumerate(rows, 1):
            proj_id  = clean(row.get('id'))
            name     = clean(row.get('name'))
            client   = clean(row.get('client'))
            status   = map_status(clean(row.get('status')))
            start    = parse_date(row.get('start_date'))
            end      = parse_date(row.get('end_date'))
            location = clean(row.get('location')) or ''
            desc     = clean(row.get('description')) or ''

            # Validation
            if not name:
                self.stdout.write(self.style.WARNING(f'  Row {i}: skipped — name is empty'))
                skipped_count += 1
                continue
            if not client:
                self.stdout.write(self.style.WARNING(f'  Row {i} ({name}): skipped — client is empty'))
                skipped_count += 1
                continue
            if not start:
                self.stdout.write(self.style.WARNING(
                    f'  Row {i} ({name}): skipped — could not parse start_date "{row.get("start_date")}"'))
                skipped_count += 1
                continue

            defaults = {
                'name':        name,
                'client':      client,
                'location':    location,
                'description': desc,
                'start_date':  start,
                'end_date':    end,
                'status':      status,
            }

            # Use explicit id if available for keyed upsert
            if proj_id and proj_id.isdigit():
                obj, created = Project.objects.update_or_create(
                    id=int(proj_id),
                    defaults=defaults,
                )
            else:
                # Fall back to name-based upsert for rows without an id
                obj, created = Project.objects.update_or_create(
                    name=name,
                    defaults={k: v for k, v in defaults.items() if k != 'name'},
                )

            action = 'Created' if created else 'Updated'
            self.stdout.write(f'  {"+" if created else "~"}  {action}: [{obj.id}] {name}')
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\n  Projects — created: {created_count}  updated: {updated_count}  skipped: {skipped_count}'
            )
        )
        self.counts['projects'] = (created_count, updated_count, skipped_count)

    # -----------------------------------------------------------------------
    # Equipment importer
    # -----------------------------------------------------------------------

    def _import_equipment(self, path):
        from amc.models import AMCProject, Equipment

        if not os.path.exists(path):
            raise CommandError(f'Equipment file not found: {path}')

        self.stdout.write(f'\n  Importing equipment from: {path}')

        with open(path, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.stdout.write(f'  {len(rows)} rows found\n')

        # Pre-load all AMCProject IDs into a set for fast lookup
        existing_amc_ids = set(AMCProject.objects.values_list('id', flat=True))

        created_count = updated_count = skipped_count = 0

        for i, row in enumerate(rows, 1):
            eq_id        = clean(row.get('id'))
            amc_proj_id  = clean(row.get('amc_project_id'))
            name         = clean(row.get('name'))

            # Skip rows with no name (the "Myth" office equipment at the bottom has no amc_project_id)
            if not name:
                skipped_count += 1
                continue

            # Skip rows without a valid amc_project_id
            if not amc_proj_id or not amc_proj_id.isdigit():
                self.stdout.write(self.style.WARNING(
                    f'  Row {i} ({name}): skipped — no amc_project_id'))
                skipped_count += 1
                continue

            amc_id_int = int(amc_proj_id)
            if amc_id_int not in existing_amc_ids:
                self.stdout.write(self.style.ERROR(
                    f'  Row {i} ({name}): skipped — AMCProject id={amc_id_int} not found in DB'))
                skipped_count += 1
                continue

            defaults = {
                'amc_project_id':   amc_id_int,
                'name':             name,
                'brand':            clean(row.get('brand'))        or '',
                'model_number':     clean(row.get('model_number')) or '',
                'serial_number':    clean(row.get('serial_number'))or '',
                'location':         clean(row.get('location'))     or '',
                'installation_date':parse_date(row.get('installation_date')),
                'warranty_expiry':  parse_date(row.get('warranty_expiry')),
                'amc_date':         parse_date(row.get('amc_date')),
                'amc_end_date':     parse_date(row.get('amc_end_date')),
                'invoice_date':     parse_date(row.get('invoice_date')),
                'invoice_no':       clean(row.get('invoice_no'))   or '',
                'win_license':      clean(row.get('win_license'))  or '',
                'notes':            clean(row.get('notes'))        or '',
            }

            if eq_id and eq_id.isdigit():
                obj, created = Equipment.objects.update_or_create(
                    id=int(eq_id),
                    defaults=defaults,
                )
            else:
                # No id — fall back to amc_project + name + serial upsert
                serial = defaults.pop('serial_number', '') or ''
                obj, created = Equipment.objects.update_or_create(
                    amc_project_id=amc_id_int,
                    name=name,
                    serial_number=serial,
                    defaults=defaults,
                )

            action = 'Created' if created else 'Updated'
            serial_display = obj.serial_number or 'no serial'
            self.stdout.write(f'  {"+" if created else "~"}  {action}: [{obj.id}] {name} ({serial_display})')
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\n  Equipment — created: {created_count}  updated: {updated_count}  skipped: {skipped_count}'
            )
        )
        self.counts['equipment'] = (created_count, updated_count, skipped_count)

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------

    def _summary(self):
        self.stdout.write('\n' + '─' * 55)
        if self.dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN complete — database unchanged'))
        else:
            self.stdout.write(self.style.SUCCESS('Import complete'))

        for section, (created, updated, skipped) in self.counts.items():
            self.stdout.write(
                f'   {section:12s}  created={created}  updated={updated}  skipped={skipped}'
            )

        if self.errors:
            self.stdout.write(self.style.ERROR('\nErrors:'))
            for e in self.errors:
                self.stdout.write(self.style.ERROR(f'  * {e}'))
        self.stdout.write('')
