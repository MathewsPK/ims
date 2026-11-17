# Tender Radar in IMS

IMS → **Tender Radar** (sidebar, Admins and Managers only):

- **Search now & email**: searches all portals in the background (a few minutes), emails new matching tenders.
- **Re-send current list**: emails every open matching tender again, no searching (seconds).
- Table of open matching tenders, filterable by match strength and portal. **NEW** = not emailed yet.
- **Recent runs**: who ran it, when, the result, and the exact email that went out.

IMS doesn't contain the search logic. It runs the separate `tender_radar` project (its own folder and
virtual environment) and records what happened. The email itself is sent by tender_radar using its own
`tender_radar.env`, not IMS's email settings.

## Where it can run

The tender search must run on a machine with an **Indian IP address**, because many government portals
block foreign and some cloud IPs. The button runs the search on the same machine IMS runs on.

On the droplet, check first:
```
curl -s https://ipinfo.io/country          # must print IN
```
DigitalOcean's Bangalore region (BLR1) gives an Indian IP. Any other region: use the office PC instead
(see the end of this file).

## Setup on the DigitalOcean droplet

All commands over SSH on the droplet.

### 1. Install tender_radar next to IMS
```
cd /var/www
# copy the tender_radar folder here (scp from the office PC, or git clone if you put it in a repo)
cd /var/www/tender_radar
python3 -m venv .venv
.venv/bin/pip install -e .
```

### 2. Bring over the database from the office PC (avoids re-seeding for hours)
Copy `C:\tender_radar\data\tenders.db` from the office PC to `/var/www/tender_radar/data/tenders.db`.
Also copy `C:\tender_radar\tender_radar.env` (Gmail settings) to `/var/www/tender_radar/tender_radar.env`.

### 3. Check the portals answer from the droplet
```
cd /var/www/tender_radar
.venv/bin/tender-radar probe cppp
.venv/bin/tender-radar probe odisha
```
Both should end with `PASS`. If they fail with connection errors, the droplet's IP is blocked:
stop here and use the office-PC option below.

### 4. Tell IMS where tender_radar is
Add to `/var/www/ims/.env`:
```
TENDER_RADAR_DIR=/var/www/tender_radar
```

### 5. Update IMS
```
cd /var/www/ims
git pull                     # or copy the updated files
source .venv/bin/activate
python manage.py migrate
python manage.py collectstatic --no-input
sudo systemctl restart ims
```

### 6. Move the daily 7 AM run onto the droplet
```
sudo crontab -e
```
Add (runs 07:00 IST if the droplet's clock is IST; for a UTC clock use `30 1 * * *`):
```
0 7 * * * cd /var/www/ims && /var/www/ims/.venv/bin/python manage.py run_tender_radar --scheduled >> /var/log/ims-tenders.log 2>&1
```
Scheduled runs show up in IMS under Recent runs as "Daily schedule".

**Then disable the Windows Task Scheduler job on the office PC.** Two machines running it means two
emails a day and two databases that drift apart.

## Office-PC option (if the droplet isn't in India)

The office PC already runs tender_radar. Run IMS on the office PC too (`run.bat`, LAN access) with
`TENDER_RADAR_DIR=C:\tender_radar` in `C:\Users\...\ims_project\.env`. The button works for anyone on
the office network. The online IMS shows no Tender Radar data in this setup.

## Troubleshooting

| On the page | Fix |
|---|---|
| "Tender Radar isn't connected on this server yet" | `TENDER_RADAR_DIR` missing or wrong in IMS `.env`, or tender_radar's `.venv` not created |
| Run says "not emailed (no email set up…)" | fill in `tender_radar.env` in the tender_radar folder (Gmail app password) |
| Run stuck on Running | it gives up after 3 hours automatically; check `/var/log/ims-tenders.log` |
| "tender-radar returned unreadable data" | update tender_radar to v0.4.0 or newer (`pip install -e .` again in its folder) |

Manual runs from the shell (same as the buttons, also recorded in IMS):
```
python manage.py run_tender_radar --scheduled            # search & email
python manage.py run_tender_radar --scheduled --resend   # re-send current list
```
