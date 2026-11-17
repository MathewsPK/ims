from django.core.management.base import BaseCommand

from notifications import gcal
from notifications.models import GoogleCalendarFeed


class Command(BaseCommand):
    help = "Sync Google Calendar iCal feeds into the IMS"

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='Ignore the sync-interval throttle')

    def handle(self, *args, **opts):
        gcal.sync_all(force=opts['force'])
        for feed in GoogleCalendarFeed.objects.filter(enabled=True):
            status = feed.last_error or 'OK'
            self.stdout.write(f"{feed.name}: {feed.events.count()} events — {status}")
