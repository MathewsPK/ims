# Deploying IMS on Your DigitalOcean Droplet

This deploys IMS to an Ubuntu droplet at **`ims.example.com`** (replace with your domain)
as its own systemd service behind Nginx, so it can share the server with other sites.

Assumptions:
- Nginx owns ports 80/443.
- Port **8001** is free for the IMS Gunicorn service.

All commands below are run over SSH on the droplet.

## 1. DNS

Wherever you manage DNS for `example.com`, add an **A record**:
```
ims.example.com  →  <your droplet's IP>
```
This can take a few minutes to propagate. Check with `dig ims.example.com`
once done.

## 2. Install prerequisites (skip anything already installed)

```
sudo apt update
sudo apt install -y python3-venv python3-pip postgresql postgresql-contrib nginx certbot python3-certbot-nginx
```

## 3. Create the Postgres database

```
sudo -u postgres psql
```
```sql
CREATE DATABASE ims;
CREATE USER ims_user WITH PASSWORD 'choose-a-strong-password';
ALTER ROLE ims_user SET client_encoding TO 'utf8';
ALTER ROLE ims_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE ims_user SET timezone TO 'Asia/Kolkata';
GRANT ALL PRIVILEGES ON DATABASE ims TO ims_user;
\q
```

## 4. Get the code onto the droplet

From your machine (or set up a git repo and `git clone` on the droplet — recommended
so future updates are just `git pull`):
```
scp -r ims_project root@your-droplet-ip:/var/www/ims
```

Then on the droplet:
```
cd /var/www/ims
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 5. Configure `.env`

Edit `/var/www/ims/.env`:
```
SECRET_KEY=<generate a long random string>
DEBUG=False
USE_POSTGRES=True
DB_NAME=ims
DB_USER=ims_user
DB_PASSWORD=<the password you set in step 3>
DB_HOST=localhost
DB_PORT=5432
CSRF_TRUSTED_ORIGINS=https://ims.example.com

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your-office-gmail@gmail.com
EMAIL_HOST_PASSWORD=<Gmail App Password, not your normal password>
DEFAULT_FROM_EMAIL=IMS <your-office-gmail@gmail.com>
```
(Generate a Gmail App Password at myaccount.google.com/apppasswords.)

## 6. Migrate data and collect static files

If you want to bring across what's already in your local `db.sqlite3`:
```
# on your local machine, with the OLD sqlite settings active:
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.permission > data.json
# copy data.json to the droplet, then on the droplet:
```
```
python manage.py migrate
python manage.py loaddata data.json   # skip this line for a fresh start instead
python manage.py collectstatic --no-input
python manage.py createsuperuser      # only needed if you didn't load existing data
```

## 7. Run Gunicorn as a systemd service

Create `/etc/systemd/system/ims.service`:
```ini
[Unit]
Description=IMS Gunicorn daemon
After=network.target postgresql.service

[Service]
User=root
Group=www-data
WorkingDirectory=/var/www/ims
ExecStart=/var/www/ims/.venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8001 config.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

```
sudo systemctl daemon-reload
sudo systemctl enable --now ims
sudo systemctl status ims
```

## 8. Nginx server block

Create `/etc/nginx/sites-available/ims`:
```nginx
server {
    listen 80;
    server_name ims.example.com;

    client_max_body_size 20M;

    location /static/ {
        alias /var/www/ims/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, max-age=2592000, immutable";
        access_log off;
    }
    location /media/ {
        alias /var/www/ims/media/;
        expires 30d;
        add_header Cache-Control "public, max-age=2592000";
        access_log off;
    }
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
```
sudo ln -s /etc/nginx/sites-available/ims /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 9. HTTPS

```
sudo certbot --nginx -d ims.example.com
```
Certbot edits the Nginx block to redirect HTTP → HTTPS and auto-renews the
certificate. Visit
`https://ims.example.com` to confirm it works.

## 10. Schedule the daily subscription-renewal check

Since you have real shell access, a plain cron job is simplest — no external
pinger needed:
```
sudo crontab -e
```
Add:
```
0 8 * * * cd /var/www/ims && /var/www/ims/.venv/bin/python manage.py check_subscription_renewals >> /var/log/ims-billing.log 2>&1
```
Runs daily at 8am, sends in-app + email reminders for subscriptions due/overdue.

## Updating the app later

```
cd /var/www/ims
git pull                       # or scp updated files over
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --no-input
sudo systemctl restart ims
```
