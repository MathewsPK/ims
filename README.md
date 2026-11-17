# IMS: Internal Management System

An operations platform for a small project-based engineering/installation studio. It replaces
spreadsheets and chat threads for projects, field work, maintenance contracts, expenses and
recurring software bills. **In daily production use** at a museum-interactives studio, deployed
on a DigitalOcean droplet.

**Stack:** Django 5 · Django REST Framework + JWT · SQLite / PostgreSQL · Bootstrap 5 ·
Gunicorn + Nginx + systemd · cron

> Built with AI-assisted development. Requirements, data model, architecture decisions,
> deployment and ongoing operation are mine.

## Features

| Module | What it does |
|---|---|
| **Projects** | Clients, sites, status, assigned team, media |
| **Tasks** | Assignment, priority, status, time logs, out-of-office tracking |
| **AMC** | Annual maintenance contracts and equipment registry (serials, warranty, AMC dates), CSV import with de-duplication |
| **Reports** | Engineer AMC visit reports with photos → manager review/approval; installation reports with documents |
| **Expenses** | Submission with receipts → **Pending → Approved / Rejected → Paid** workflow, filters, notifications |
| **Billing** | Software subscriptions (AI tools, hosting, design suites), renewal tracking, monthly-spend estimate, sortable list, daily reminder job, one-click "mark paid" that rolls the renewal date forward |
| **Notifications** | In-app + email, Google Calendar sync via private iCal feeds (per-user and company-wide) |
| **Tender Radar** | Triggers an external tender-search tool and logs each run (optional integration) |
| **Dashboard** | Per-role overview: tasks by status, overdue items, pending approvals, due renewals |
| **Users & roles** | Admin / Manager / Engineer / Staff with role-based permissions, activity + audit log |
| **REST API** | JWT-authenticated endpoints for users, projects, tasks, AMC, expenses, reports, notifications |

## Design decisions

- **Role-based access in one place.** Permission mixins (`users/permissions.py`) and helper methods
  on `User` gate both views and templates, so a role check never gets duplicated inconsistently.
- **Renewal date arithmetic.** `billing.models.add_months` clamps to the last valid day
  (Jan 31 + 1 month → Feb 28/29) so monthly bills don't drift or crash on short months.
- **Idempotent reminders.** `check_subscription_renewals` stores `last_reminder_sent` so a re-run on
  the same day never double-notifies. It runs from system cron, with an HTTP-token fallback endpoint
  for hosts without cron.
- **Server-side sorting/filtering via query params.** Sort keys are whitelisted in the view, so
  arbitrary `order_by` input is never passed to the ORM, and filters + sort compose in the URL.
- **Config through environment only.** No secrets in code; SQLite locally, PostgreSQL via
  `DATABASE_URL` in production.

## Run locally

```bash
git clone https://github.com/<you>/ims.git && cd ims
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # then set SECRET_KEY
python manage.py migrate
python manage.py seed_data                           # demo users, projects, expenses…
python manage.py runserver
```

Or run the one-command scripts: `./setup.sh` (Linux/macOS) or `setup.bat` (Windows).
Demo login: `admin@ims.local` / `admin123` (all seeded users share that password).

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for Ubuntu + Gunicorn + Nginx + systemd + Certbot, and the cron
entry for renewal reminders. Google Calendar sync: [GCAL_SYNC_SETUP.md](GCAL_SYNC_SETUP.md).
Tender Radar: [TENDER_RADAR.md](TENDER_RADAR.md).

## Screenshots

_Add screenshots taken with seed data only._
