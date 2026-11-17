# IMS

Internal management system I built for the studio I work at. We used to track projects,
AMC visits, expenses and software renewals across Excel sheets and WhatsApp. This replaced
all of that. It's been in daily use since 2026, running on a DigitalOcean droplet.

Django 5, DRF with JWT, SQLite locally / Postgres in production, Bootstrap 5 for the UI.
I used AI tools while building it; the requirements, data model, deployment and maintenance are mine.

## What's in it

- Projects and tasks: assignment, priorities, time logs, out-of-office
- AMC contracts and an equipment register (serial numbers, warranty, service dates), with CSV import
- Field engineers submit AMC visit reports with photos, managers review them
- Expenses with receipts: pending, approved/rejected, then paid
- Software subscriptions (Claude, Adobe, hosting etc.) with renewal reminders. Marking one as
  paid moves the renewal date to the next cycle
- In-app and email notifications, Google Calendar sync through private iCal links
- Four roles (admin, manager, engineer, staff), each sees a different dashboard
- REST API for most modules

## Some things worth explaining

Renewal dates: adding a month to Jan 31 should give Feb 28, not crash or skip to March.
`add_months()` in `billing/models.py` handles that.

Reminders run once a day from cron. Each subscription stores the date it was last reminded,
so running the command twice doesn't send duplicate emails.

The billing list sorts by platform or price through a `?sort=` param. Only a fixed set of
sort keys is accepted, so user input never goes straight into `order_by`.

Permissions live in `users/permissions.py` and a few methods on the `User` model, so views and
templates check roles the same way.

## Running it

```
git clone https://github.com/MathewsPK/ims.git
cd ims
python -m venv .venv
.venv\Scripts\activate        (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env        (set SECRET_KEY)
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

`seed_data` creates demo data. Login: admin@ims.local / admin123

## Deployment

Gunicorn under systemd, Nginx in front, Certbot for SSL, and a cron job for renewal reminders.
Steps are in [docs/deployment.md](docs/deployment.md).
