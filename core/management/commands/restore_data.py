"""
python manage.py restore_data

Restores Projects, AMCProjects, and Equipment from CSV exports.
Pass the folder containing the three CSV files:

    python manage.py restore_data --dir "C:/path/to/folder"

The script matches files by looking for any CSV whose name contains
'Project', 'AMCProject', and 'Equipment' (case-insensitive).
Existing records with the same ID are skipped (not overwritten).
"""

import csv
import os
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


DATE_FMTS = [
    '%Y-%m-%d',
    '%d-%m-%Y',
    '%d/%m/%Y',
    '%m/%d/%Y',
]


def parse_date(val):
    if not val or not val.strip():
        return None
    val = val.strip()
    for fmt in DATE_FMTS:
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


def clean(val):
    return val.strip() if val else ''


class Command(BaseCommand):
    help = 'Restore Projects, AMCProjects, and Equipment from CSV exports'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dir',
            required=True,
            help='Folder containing the exported CSV files',
        )

    def handle(self, *args, **options):
        folder = Path(options['dir'])
        if not folder.exists():
            raise CommandError(f'Folder not found: {folder}')

        # Find each CSV by keyword in filename
        project_csv = amc_csv = equip_csv = None
        for f in folder.glob('*.csv'):
            name_lower = f.name.lower()
            if 'amcproject' in name_lower or 'amc_project' in name_lower:
                amc_csv = f
            elif 'project' in name_lower:
                project_csv = f
            elif 'equipment' in name_lower:
                equip_csv = f

        missing = [
            label for label, path in [
                ('Project CSV', project_csv),
                ('AMCProject CSV', amc_csv),
                ('Equipment CSV', equip_csv),
            ] if path is None
        ]
        if missing:
            raise CommandError(
                f'Could not find: {", ".join(missing)}\n'
                f'Files in folder: {[f.name for f in folder.glob("*.csv")]}'
            )

        self.stdout.write(f'Project CSV  : {project_csv.name}')
        self.stdout.write(f'AMCProject CSV: {amc_csv.name}')
        self.stdout.write(f'Equipment CSV: {equip_csv.name}')
        self.stdout.write('')

        with transaction.atomic():
            p_created, p_skipped = self._restore_projects(project_csv)
            a_created, a_skipped = self._restore_amc(amc_csv)
            e_created, e_skipped = self._restore_equipment(equip_csv)

        self.stdout.write(self.style.SUCCESS(
            f'\nDone!\n'
            f'  Projects  : {p_created} created, {p_skipped} skipped\n'
            f'  AMC       : {a_created} created, {a_skipped} skipped\n'
            f'  Equipment : {e_created} created, {e_skipped} skipped'
        ))

    # ------------------------------------------------------------------ #

    def _restore_projects(self, path):
        from projects.models import Project
        created = skipped = 0

        with open(path, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                pk = int(row['id'])
                if Project.objects.filter(pk=pk).exists():
                    skipped += 1
                    continue
                Project.objects.create(
                    id=pk,
                    name=clean(row.get('name', '')),
                    client=clean(row.get('client', '')) or 'Unknown',
                    location=clean(row.get('location', '')),
                    description=clean(row.get('description', '')),
                    status=clean(row.get('status', 'COMPLETED')) or 'COMPLETED',
                    start_date=parse_date(row.get('start_date')) or __import__('datetime').date.today(),
                    end_date=parse_date(row.get('end_date')),
                )
                created += 1
                self.stdout.write(f'  [Project] Created #{pk}: {row["name"]}')

        # Reset the auto-increment sequence so new projects don't collide
        self._reset_sequence('projects_project', Project)
        return created, skipped

    def _restore_amc(self, path):
        from amc.models import AMCProject
        from projects.models import Project
        created = skipped = 0

        with open(path, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                pk = int(row['id'])
                if AMCProject.objects.filter(pk=pk).exists():
                    skipped += 1
                    continue
                project_pk = int(row['project'])
                try:
                    project = Project.objects.get(pk=project_pk)
                except Project.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  [AMC] Skipping #{pk}: project {project_pk} not found'
                        )
                    )
                    skipped += 1
                    continue

                start = parse_date(row.get('amc_start_date'))
                end = parse_date(row.get('amc_end_date'))
                if not start:
                    import datetime
                    start = datetime.date.today()
                if not end:
                    end = start

                AMCProject.objects.create(
                    id=pk,
                    project=project,
                    contract_number=clean(row.get('contract_number', '')),
                    amc_start_date=start,
                    amc_end_date=end,
                    contract_value=row.get('contract_value') or None,
                    notes=clean(row.get('notes', '')),
                )
                created += 1
                self.stdout.write(f'  [AMC] Created #{pk} for project: {project.name}')

        self._reset_sequence('amc_amcproject', AMCProject)
        return created, skipped

    def _restore_equipment(self, path):
        from amc.models import AMCProject, Equipment
        created = skipped = 0
        seen_ids = set()

        with open(path, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                pk = int(row['id'])
                if pk in seen_ids:
                    # duplicate row in CSV (same id, different location)
                    # create without forcing pk so it gets a new id
                    amc_pk = int(row['amc_project_id'])
                    try:
                        amc = AMCProject.objects.get(pk=amc_pk)
                    except AMCProject.DoesNotExist:
                        skipped += 1
                        continue
                    Equipment.objects.create(
                        amc_project=amc,
                        name=clean(row.get('name', '')),
                        brand=clean(row.get('brand', '')),
                        model_number=clean(row.get('model_number', '')),
                        serial_number=clean(row.get('serial_number', '')),
                        location=clean(row.get('location', '')),
                        installation_date=parse_date(row.get('installation_date')),
                        warranty_expiry=parse_date(row.get('warranty_expiry')),
                        amc_date=parse_date(row.get('amc_date')),
                        amc_end_date=parse_date(row.get('amc_end_date')),
                        invoice_date=parse_date(row.get('invoice_date')),
                        invoice_no=clean(row.get('invoice_no', '')),
                        win_license=clean(row.get('win_license', '')),
                        notes=clean(row.get('notes', '')),
                    )
                    created += 1
                    continue

                seen_ids.add(pk)

                if Equipment.objects.filter(pk=pk).exists():
                    skipped += 1
                    continue

                amc_pk = int(row['amc_project_id'])
                try:
                    amc = AMCProject.objects.get(pk=amc_pk)
                except AMCProject.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  [Equipment] Skipping #{pk}: AMC {amc_pk} not found'
                        )
                    )
                    skipped += 1
                    continue

                Equipment.objects.create(
                    id=pk,
                    amc_project=amc,
                    name=clean(row.get('name', '')),
                    brand=clean(row.get('brand', '')),
                    model_number=clean(row.get('model_number', '')),
                    serial_number=clean(row.get('serial_number', '')),
                    location=clean(row.get('location', '')),
                    installation_date=parse_date(row.get('installation_date')),
                    warranty_expiry=parse_date(row.get('warranty_expiry')),
                    amc_date=parse_date(row.get('amc_date')),
                    amc_end_date=parse_date(row.get('amc_end_date')),
                    invoice_date=parse_date(row.get('invoice_date')),
                    invoice_no=clean(row.get('invoice_no', '')),
                    win_license=clean(row.get('win_license', '')),
                    notes=clean(row.get('notes', '')),
                )
                created += 1

        self._reset_sequence('amc_equipment', Equipment)
        return created, skipped

    def _reset_sequence(self, table, model):
        """
        SQLite doesn't need explicit sequence resets, but for safety
        we update the sqlite_sequence table so new auto-increments
        start above the highest restored id.
        """
        from django.db import connection
        max_id = model.objects.order_by('-id').values_list('id', flat=True).first()
        if max_id:
            with connection.cursor() as cursor:
                try:
                    cursor.execute(
                        "UPDATE sqlite_sequence SET seq = %s WHERE name = %s",
                        [max_id, table]
                    )
                except Exception:
                    pass  # table may not exist if no auto-increment rows yet
