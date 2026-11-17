"""
Google Calendar → IMS sync via secret iCal URLs.

Requires:  pip install icalendar recurring-ical-events
Setup:     Google Calendar → Settings → [your calendar] → Integrate calendar
           → copy "Secret address in iCal format" → add it on the
           "My Google Calendars" page (private) or in Django admin
           (company-wide feeds).

Sync runs automatically (throttled) whenever the IMS calendar is opened,
or manually via:  python manage.py sync_gcal
"""
import logging
import urllib.request
from datetime import datetime, date, time, timedelta

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Re-sync at most every N minutes when triggered by page loads
SYNC_INTERVAL_MIN = getattr(settings, 'GCAL_SYNC_INTERVAL_MIN', 15)
# How far back / forward to expand recurring events
WINDOW_PAST_DAYS = getattr(settings, 'GCAL_WINDOW_PAST_DAYS', 60)
WINDOW_FUTURE_DAYS = getattr(settings, 'GCAL_WINDOW_FUTURE_DAYS', 180)
# Upcoming window mirrored into the Meetings/Events list
EVENT_IMPORT_DAYS = getattr(settings, 'GCAL_EVENT_IMPORT_DAYS', 60)


def _to_aware(value):
    """Normalise ical date/datetime to an aware datetime in the current TZ."""
    tz = timezone.get_current_timezone()
    if isinstance(value, datetime):
        if timezone.is_naive(value):
            return timezone.make_aware(value, tz)
        return value.astimezone(tz)
    if isinstance(value, date):
        return timezone.make_aware(datetime.combine(value, time.min), tz)
    return value


def sync_feed(feed):
    """Fetch one feed, expand recurrences, upsert GoogleCalendarEvent rows.

    Returns the number of events stored. Raises on hard failures
    (callers record feed.last_error).
    """
    import icalendar
    import recurring_ical_events
    from .models import GoogleCalendarEvent, NotificationEvent

    req = urllib.request.Request(
        feed.ical_url, headers={'User-Agent': 'IMS-GCalSync/1.0'}
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read()

    cal = icalendar.Calendar.from_ical(raw)
    now = timezone.localtime()
    window_start = now - timedelta(days=WINDOW_PAST_DAYS)
    window_end = now + timedelta(days=WINDOW_FUTURE_DAYS)
    occurrences = recurring_ical_events.of(cal).between(window_start, window_end)

    seen = set()
    count = 0
    for ev in occurrences:
        uid = str(ev.get('UID', ''))[:300]
        start = _to_aware(ev.get('DTSTART').dt)
        dtend = ev.get('DTEND')
        end = _to_aware(dtend.dt) if dtend else start + timedelta(hours=1)
        all_day = not isinstance(ev.get('DTSTART').dt, datetime)
        key = (uid, start)
        if key in seen:
            continue
        seen.add(key)
        GoogleCalendarEvent.objects.update_or_create(
            feed=feed, uid=uid, start=start,
            defaults={
                'title': str(ev.get('SUMMARY', '') or '(no title)')[:300],
                'description': str(ev.get('DESCRIPTION', '') or ''),
                'location': str(ev.get('LOCATION', '') or '')[:300],
                'end': end,
                'all_day': all_day,
            },
        )
        count += 1

    # Drop events that disappeared from the feed (within the window)
    stale_pks = [
        e.pk
        for e in feed.events.filter(start__gte=window_start, start__lte=window_end)
        if (e.uid, e.start) not in seen
    ]
    if stale_pks:
        feed.events.filter(pk__in=stale_pks).delete()

    if feed.import_as_events and feed.owner_id is None:
        # Only company-wide feeds are mirrored into the shared
        # Meetings/Events list. Private feeds are never mirrored —
        # their events stay visible to the owner alone.
        _mirror_to_notification_events(feed, now)
    else:
        _purge_mirrored_events(feed)

    return count


def _purge_mirrored_events(feed):
    """Remove any previously mirrored events for this feed."""
    from .models import NotificationEvent
    NotificationEvent.objects.filter(gcal_uid__startswith=f"gcal:{feed.pk}:").delete()


def _mirror_to_notification_events(feed, now):
    """Mirror upcoming feed events into the Meetings/Events list."""
    from .models import GoogleCalendarEvent, NotificationEvent

    horizon = now + timedelta(days=EVENT_IMPORT_DAYS)
    upcoming = feed.events.filter(start__gte=now, start__lte=horizon)
    keep_uids = []
    for e in upcoming:
        marker = f"gcal:{feed.pk}:{e.uid}:{e.start.isoformat()}"[:300]
        keep_uids.append(marker)
        NotificationEvent.objects.update_or_create(
            gcal_uid=marker,
            defaults={
                'title': f"{e.title} ({feed.name})"[:200],
                'description': e.description,
                'event_type': NotificationEvent.EventType.MEETING,
                'event_datetime': e.start,
                'location': e.location[:200],
                'all_users': True,
            },
        )
    # Remove mirrored events no longer in the feed's upcoming window
    NotificationEvent.objects.filter(
        gcal_uid__startswith=f"gcal:{feed.pk}:"
    ).exclude(gcal_uid__in=keep_uids).delete()


def sync_all(force=False):
    """Sync every enabled feed. Throttled unless force=True.

    Never raises — errors are stored on feed.last_error so a bad
    feed URL can't break the calendar page.
    """
    from .models import GoogleCalendarFeed

    now = timezone.now()
    threshold = now - timedelta(minutes=SYNC_INTERVAL_MIN)
    for feed in GoogleCalendarFeed.objects.filter(enabled=True):
        if not force and feed.last_synced and feed.last_synced > threshold:
            continue
        try:
            sync_feed(feed)
            feed.last_error = ''
        except ImportError:
            feed.last_error = (
                "Missing packages — run: pip install icalendar recurring-ical-events"
            )
            logger.warning("gcal sync skipped: %s", feed.last_error)
        except Exception as exc:  # noqa: BLE001 — must never break the calendar
            feed.last_error = str(exc)[:2000]
            logger.exception("gcal sync failed for feed %s", feed.pk)
        feed.last_synced = now
        feed.save(update_fields=['last_synced', 'last_error'])
