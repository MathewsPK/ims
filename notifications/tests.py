"""Tests for the Google Calendar iCal sync."""
import tempfile
from pathlib import Path

from django.test import TestCase
from django.utils import timezone

from . import gcal
from .models import GoogleCalendarEvent, GoogleCalendarFeed, NotificationEvent

ICS_TEMPLATE = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//EN
BEGIN:VEVENT
UID:single-1@test
DTSTART;TZID=Asia/Kolkata:{d1}T100000
DTEND;TZID=Asia/Kolkata:{d1}T110000
SUMMARY:Client Review Meeting
LOCATION:Office
END:VEVENT
BEGIN:VEVENT
UID:allday-1@test
DTSTART;VALUE=DATE:{d2}
DTEND;VALUE=DATE:{d3}
SUMMARY:Site Visit
END:VEVENT
BEGIN:VEVENT
UID:weekly-1@test
DTSTART;TZID=Asia/Kolkata:{d1}T160000
DTEND;TZID=Asia/Kolkata:{d1}T163000
RRULE:FREQ=WEEKLY;COUNT=4
SUMMARY:Weekly Standup
END:VEVENT
END:VCALENDAR
"""


class GcalSyncTests(TestCase):
    def _make_feed(self):
        now = timezone.localtime()
        d1 = (now + timezone.timedelta(days=1)).strftime('%Y%m%d')
        d2 = (now + timezone.timedelta(days=2)).strftime('%Y%m%d')
        d3 = (now + timezone.timedelta(days=3)).strftime('%Y%m%d')
        ics = ICS_TEMPLATE.format(d1=d1, d2=d2, d3=d3)
        f = Path(tempfile.gettempdir()) / 'gcal_test.ics'
        f.write_text(ics)
        return GoogleCalendarFeed.objects.create(
            name='Test Cal', ical_url=f.as_uri(),
        )

    def test_sync_creates_events(self):
        feed = self._make_feed()
        n = gcal.sync_feed(feed)
        self.assertEqual(n, 6)  # 1 single + 1 all-day + 4 weekly occurrences
        self.assertEqual(GoogleCalendarEvent.objects.count(), 6)
        e = GoogleCalendarEvent.objects.get(uid='single-1@test')
        self.assertEqual(e.title, 'Client Review Meeting')
        self.assertFalse(e.all_day)
        self.assertTrue(GoogleCalendarEvent.objects.get(uid='allday-1@test').all_day)

    def test_company_feed_mirrors_to_events(self):
        feed = self._make_feed()  # owner=None -> company-wide
        gcal.sync_feed(feed)
        mirrored = NotificationEvent.objects.filter(gcal_uid__startswith=f'gcal:{feed.pk}:')
        self.assertEqual(mirrored.count(), 6)
        self.assertTrue(all(m.all_users for m in mirrored))

    def test_private_feed_never_mirrors(self):
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create(
            email='private@test.local', username='private@test.local', name='P',
        )
        feed = self._make_feed()
        feed.owner = user
        feed.save()
        gcal.sync_feed(feed)
        # Events synced for the calendar view...
        self.assertEqual(feed.events.count(), 6)
        # ...but nothing lands in the shared Meetings/Events list
        self.assertEqual(NotificationEvent.objects.count(), 0)

    def test_feed_turned_private_purges_mirrored_events(self):
        from django.contrib.auth import get_user_model
        feed = self._make_feed()
        gcal.sync_feed(feed)
        self.assertEqual(NotificationEvent.objects.count(), 6)
        user = get_user_model().objects.create(
            email='p2@test.local', username='p2@test.local', name='P2',
        )
        feed.owner = user
        feed.save()
        gcal.sync_feed(feed)
        self.assertEqual(NotificationEvent.objects.count(), 0)

    def test_resync_is_idempotent(self):
        feed = self._make_feed()
        gcal.sync_feed(feed)
        gcal.sync_feed(feed)
        self.assertEqual(GoogleCalendarEvent.objects.count(), 6)
        self.assertEqual(
            NotificationEvent.objects.filter(gcal_uid__startswith='gcal:').count(), 6)

    def test_sync_all_records_error_without_raising(self):
        feed = GoogleCalendarFeed.objects.create(
            name='Bad', ical_url='https://invalid.invalid/basic.ics',
        )
        gcal.sync_all(force=True)
        feed.refresh_from_db()
        self.assertNotEqual(feed.last_error, '')
