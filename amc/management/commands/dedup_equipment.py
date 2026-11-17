"""
python manage.py dedup_equipment

Finds Equipment rows that share the same (amc_project_id, name, serial_number)
and deletes all but the one with the lowest pk.
"""
from django.core.management.base import BaseCommand
from django.db.models import Count
from amc.models import Equipment


class Command(BaseCommand):
    help = 'Remove duplicate Equipment records, keeping the earliest (lowest pk).'

    def handle(self, *args, **options):
        total_before = Equipment.objects.count()
        self.stdout.write(f'Equipment records before: {total_before}')

        dupes = (
            Equipment.objects
            .values('amc_project_id', 'name', 'serial_number')
            .annotate(cnt=Count('id'))
            .filter(cnt__gt=1)
        )

        deleted = 0
        for d in dupes:
            qs = Equipment.objects.filter(
                amc_project_id=d['amc_project_id'],
                name=d['name'],
                serial_number=d['serial_number'],
            ).order_by('id')
            ids_to_delete = list(qs.values_list('id', flat=True)[1:])
            Equipment.objects.filter(id__in=ids_to_delete).delete()
            deleted += len(ids_to_delete)

        self.stdout.write(
            self.style.SUCCESS(
                f'Deleted {deleted} duplicates. '
                f'Remaining: {Equipment.objects.count()}'
            )
        )
