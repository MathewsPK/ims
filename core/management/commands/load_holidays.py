"""
python manage.py load_holidays

Loads the 2026 holiday calendar (idempotent — safe to re-run).

Regions:
  NATIONAL — Central Govt gazetted holidays 2026 (Ministry of Personnel list)
  ODISHA   — Odisha Govt holiday list 2026 (state-specific days beyond national)
  VADODARA — Gujarat Govt holiday list 2026 (state-specific days beyond national)

Sources (checked Jul 2026): CAG/DoPT gazetted list 2026; Odisha Govt
holiday notification 2026; Gujarat GAD holiday notification 2026.
For future years: add the new lists below and re-run, or add entries
manually in Django admin → Core → Holidays.
"""
from datetime import date

from django.core.management.base import BaseCommand

NATIONAL_2026 = [
    (date(2026, 1, 26), "Republic Day"),
    (date(2026, 3, 4), "Holi"),
    (date(2026, 3, 21), "Id-ul-Fitr"),
    (date(2026, 3, 26), "Ram Navami"),
    (date(2026, 3, 31), "Mahavir Jayanti"),
    (date(2026, 4, 3), "Good Friday"),
    (date(2026, 5, 1), "Buddha Purnima"),
    (date(2026, 5, 27), "Id-ul-Zuha (Bakrid)"),
    (date(2026, 6, 26), "Muharram"),
    (date(2026, 8, 15), "Independence Day"),
    (date(2026, 8, 26), "Id-e-Milad"),
    (date(2026, 9, 4), "Janmashtami"),
    (date(2026, 10, 2), "Gandhi Jayanti"),
    (date(2026, 10, 20), "Dussehra"),
    (date(2026, 11, 8), "Diwali"),
    (date(2026, 11, 24), "Guru Nanak Jayanti"),
    (date(2026, 12, 25), "Christmas"),
]

# Odisha state holidays 2026 that are NOT already national holidays
ODISHA_2026 = [
    (date(2026, 1, 14), "Makar Sankranti"),
    (date(2026, 1, 23), "Netaji Jayanti / Vir Surendra Sai Jayanti / Basanta Panchami"),
    (date(2026, 2, 15), "Maha Shivratri"),
    (date(2026, 3, 27), "Shree Rama Navami (Odisha)"),
    (date(2026, 4, 1), "Utkal Divas"),
    (date(2026, 4, 14), "Ambedkar Jayanti / Maha Visuba Sankranti"),
    (date(2026, 6, 15), "Raja Sankranti"),
    (date(2026, 7, 16), "Rath Yatra"),
    (date(2026, 9, 14), "Ganesh Puja"),
    (date(2026, 9, 15), "Nuakhai"),
    (date(2026, 10, 18), "Mahasthami"),
    (date(2026, 10, 19), "Mahanavami"),
    (date(2026, 11, 24), "Rahas Purnima"),
]

# Gujarat state holidays 2026 (for Vadodara) that are NOT already national
VADODARA_2026 = [
    (date(2026, 1, 14), "Uttarayan (Makar Sankranti)"),
    (date(2026, 2, 15), "Maha Shivaratri"),
    (date(2026, 3, 19), "Cheti Chand"),
    (date(2026, 4, 4), "Easter Saturday"),
    (date(2026, 4, 14), "Dr. Ambedkar Jayanti"),
    (date(2026, 7, 16), "Rath Yatra"),
    (date(2026, 8, 28), "Raksha Bandhan"),
    (date(2026, 9, 17), "Samvatsari"),
    (date(2026, 9, 25), "Anant Chaturdashi"),
    (date(2026, 10, 25), "Sharad Purnima"),
    (date(2026, 11, 9), "Gujarati New Year (Bestu Varsh)"),
    (date(2026, 11, 11), "Bhai Bij"),
]


class Command(BaseCommand):
    help = "Load 2026 national + Odisha + Vadodara/Gujarat holidays (idempotent)"

    def handle(self, *args, **kwargs):
        from core.models import Holiday
        created = 0
        for region, entries in (
            ('NATIONAL', NATIONAL_2026),
            ('ODISHA', ODISHA_2026),
            ('VADODARA', VADODARA_2026),
        ):
            for d, name in entries:
                _, was_created = Holiday.objects.get_or_create(
                    date=d, region=region, name=name,
                )
                created += was_created
        total = Holiday.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"Holidays loaded: {created} new, {total} total in database."
        ))
