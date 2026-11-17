# Google Calendar → IMS Sync (read-only, free, private)

Pulls events from Google Calendars into the IMS. Two kinds of feeds:

- **Private (per-user)** — each user connects their own calendar on the
  **My Calendars** page. Their events appear ONLY in their own calendar
  view. Other users — including admins — cannot see them anywhere in the
  app, and they are never copied into the shared Meetings/Events list.
- **Company-wide** — added by an admin in Django admin. Visible to
  everyone in the calendar view, and upcoming entries (next 60 days) also
  appear in the Meetings/Events list.

## One-time setup

1. Install new packages + migrate (or just re-run `setup.bat`):

       .venv\Scripts\pip install icalendar recurring-ical-events
       .venv\Scripts\python manage.py migrate

2. Get the calendar's secret address:
   Google Calendar (web) → ⚙ Settings → click your calendar in the left list
   → **Integrate calendar** → copy **Secret address in iCal format**
   (ends in `/basic.ics`). Keep this URL private.

3. Connect it:
   - **Your own calendar (private):** IMS → Calendar page → **My calendars**
     (or `/notifications/my-calendars/`) → paste URL, pick a colour.
   - **Company calendar (shared):** Django admin → Notifications →
     Google calendar feeds → Add (leave it as company-wide).

## How it works

- Events render in the Tasks calendar view in the feed's colour with a
  legend entry. Private feeds show only for their owner.
- Sync runs automatically when the calendar page opens (throttled to every
  15 min). Force it: the sync button on My Calendars, the admin action, or
  `python manage.py sync_gcal --force`.
- Recurring events are expanded (60 days back, 180 days forward).
- Sync errors never break the page — shown on My Calendars / admin.

## Privacy notes

- Private feeds and their events are hidden from Django admin as well.
- Hard limit: anyone with direct access to the server's database file
  could technically read stored feed data — same as any server-side app.
  Keep server access restricted.

## Limits

- Read-only: changes made in IMS are not pushed back to Google.
- Google refreshes secret-address feeds on its own schedule (can lag a few
  hours for changes made in Google Calendar).
