"""
Management command to load Project, AMCProject and Equipment data from CSV exports.

Usage:
    python manage.py load_csv_data

CSVs expected in  <project_root>/data/
    Project-2026-05-27.csv
    AMCProject-2026-05-27.csv
    Equipment-2026-05-27.csv
"""

import csv
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings


BASE_DIR = settings.BASE_DIR   # project root

CSV_DIR = os.path.join(BASE_DIR, 'data')

PROJECT_CSV   = os.path.join(CSV_DIR, 'Project-2026-05-27.csv')
AMC_CSV       = os.path.join(CSV_DIR, 'AMCProject-2026-05-27.csv')
EQUIPMENT_CSV = os.path.join(CSV_DIR, 'Equipment-2026-05-27.csv')


def _parse_date(val):
    if not val or not str(val).strip():
        return None
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(str(val).strip(), fmt).date()
        except ValueError:
            pass
    return None


def _clean(val):
    return (val or '').strip() or None


class Command(BaseCommand):
    help = 'Load Projects, AMCProjects and Equipment from CSV exports in data/'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Validate CSVs without writing to the database',
        )

    def handle(self, *args, **options):
        dry = options['dry_run']
        if dry:
            self.stdout.write(self.style.WARNING('DRY RUN — no changes will be written\n'))

        self._load_projects(dry)
        self._load_amc(dry)
        self._load_equipment(dry)

        self.stdout.write(self.style.SUCCESS('\n✅  Done.'))

    # ------------------------------------------------------------------ #
    def _load_projects(self, dry):
        from projects.models import Project

        self.stdout.write('\n=== Projects ===')
        created = updated = errors = 0

        with open(PROJECT_CSV, encoding='utf-8-sig', newline='') as f:
            for row in csv.DictReader(f):
                try:
                    pk = int(row['id'])
                except (KeyError, ValueError):
                    self.stdout.write(self.style.ERROR(f'  ! Bad row (no id): {row}'))
                    errors += 1
                    continue

                data = dict(
                    name        = _clean(row.get('name'))        or 'Unknown',
                    client      = _clean(row.get('client'))      or 'Unknown',
                    location    = _clean(row.get('location'))    or '',
                    status      = _clean(row.get('status'))      or 'PLANNING',
                    start_date  = _parse_date(row.get('start_date')) or datetime.today().date(),
                    end_date    = _parse_date(row.get('end_date')),
                    description = _clean(row.get('description')) or '',
                )

                if not dry:
                    obj, was_created = Project.objects.update_or_create(pk=pk, defaults=data)
                    if was_created:
                        created += 1
                        self.stdout.write(f"  + [{pk}] {data['name']}")
                    else:
                        updated += 1
                else:
                    self.stdout.write(f"  ~ [{pk}] {data['name']}")

        self.stdout.write(
            self.style.SUCCESS(f"  → {created} created, {updated} updated, {errors} errors")
        )

    # ------------------------------------------------------------------ #
    def _load_amc(self, dry):
        from projects.models import Project
        from amc.models import AMCProject

        self.stdout.write('\n=== AMCProjects ===')
        created = updated = skipped = errors = 0

        with open(AMC_CSV, encoding='utf-8-sig', newline='') as f:
            for row in csv.DictReader(f):
                try:
                    pk       = int(row['id'])
                    proj_id  = int(row['project'])
                except (KeyError, ValueError):
                    self.stdout.write(self.style.ERROR(f'  ! Bad row: {row}'))
                    errors += 1
                    continue

                try:
                    project = Project.objects.get(pk=proj_id)
                except Project.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'  ! [{pk}] Project {proj_id} not found — skipped')
                    )
                    skipped += 1
                    continue

                contract_no = _clean(row.get('contract_number')) or f'AUTO-{proj_id}'
                data = dict(
                    project         = project,
                    contract_number = contract_no,
                    notes           = _clean(row.get('notes')) or '',
                )

                amc_start = _parse_date(row.get('amc_start_date'))
                amc_end   = _parse_date(row.get('amc_end_date'))
                if amc_start:
                    data['amc_start_date'] = amc_start
                if amc_end:
                    data['amc_end_date'] = amc_end

                cv = _clean(row.get('contract_value'))
                if cv:
                    try:
                        data['contract_value'] = float(cv)
                    except ValueError:
                        pass

                if not dry:
                    obj, was_created = AMCProject.objects.update_or_create(pk=pk, defaults=data)
                    if was_created:
                        created += 1
                        self.stdout.write(f"  + [{pk}] → Project {proj_id}")
                    else:
                        updated += 1
                else:
                    self.stdout.write(f"  ~ [{pk}] → Project {proj_id}")

        self.stdout.write(
            self.style.SUCCESS(
                f"  → {created} created, {updated} updated, {skipped} skipped, {errors} errors"
            )
        )

    # ------------------------------------------------------------------ #
    def _load_equipment(self, dry):
        from amc.models import AMCProject, Equipment

        self.stdout.write('\n=== Equipment ===')
        created = updated = skipped = errors = 0

        with open(EQUIPMENT_CSV, encoding='utf-8-sig', newline='') as f:
            for row in csv.DictReader(f):
                try:
                    pk = int(row['id'])
                except (KeyError, ValueError):
                    errors += 1
                    continue

                name = _clean(row.get('name'))
                if not name:
                    skipped += 1
                    continue

                raw_amc = _clean(row.get('amc_project_id'))
                amc_id  = int(raw_amc) if raw_amc else None

                try:
                    amc = AMCProject.objects.get(pk=amc_id) if amc_id else None
                except AMCProject.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  ! [{pk}] "{name}" — AMCProject {amc_id} not found — skipped'
                        )
                    )
                    skipped += 1
                    continue

                data = dict(
                    amc_project       = amc,
                    name              = name,
                    brand             = _clean(row.get('brand'))        or '',
                    model_number      = _clean(row.get('model_number')) or '',
                    serial_number     = _clean(row.get('serial_number'))or '',
                    location          = _clean(row.get('location'))     or '',
                    installation_date = _parse_date(row.get('installation_date')),
                    warranty_expiry   = _parse_date(row.get('warranty_expiry')),
                    amc_date          = _parse_date(row.get('amc_date')),
                    amc_end_date      = _parse_date(row.get('amc_end_date')),
                    invoice_date      = _parse_date(row.get('invoice_date')),
                    invoice_no        = _clean(row.get('invoice_no'))   or '',
                    win_license       = _clean(row.get('win_license'))  or '',
                    notes             = _clean(row.get('notes'))        or '',
                )

                if not dry:
                    obj, was_created = Equipment.objects.update_or_create(pk=pk, defaults=data)
                    if was_created:
                        created += 1
                    else:
                        updated += 1
                else:
                    self.stdout.write(f"  ~ [{pk}] {name}")

        self.stdout.write(
            self.style.SUCCESS(
                f"  → {created} created, {updated} updated, {skipped} skipped, {errors} errors"
            )
        )
