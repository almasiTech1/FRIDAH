# Deploying the Fridah Backend to a VPS

This covers a from-scratch deployment of `fridah-backend` (Django + Postgres + Redis +
Celery + nginx) to a plain Linux VPS, using the Docker Compose setup already in this
repo. Written for Ubuntu 24.04, but any recent Debian/Ubuntu works the same way.

This guide is for the **backend only**. The web app (`fridah-web`) is a separate static
build deployed elsewhere (e.g. Cloudflare Pages) — see `fridah-web/README.md`. The two
are connected only by `VITE_API_BASE_URL` (web) and `CORS_ALLOWED_ORIGINS` (backend)
pointing at each other.

## 1. Provision the server

Any provider works — DigitalOcean, Hetzner, Linode, etc. Minimum realistic spec for a
small-to-medium deployment: **2 vCPU / 4 GB RAM / 40 GB disk**. Ubuntu 24.04 LTS image.

Once it's up, SSH in as root (or a sudo user) and do basic hardening:

```bash
adduser fridah && usermod -aG sudo fridah   # don't operate as root day-to-day
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

## 2. Point DNS at the server

Create an **A record** for `api.fridah.co.ke` pointing at the server's public IP.
Give it a few minutes to propagate before continuing — step 5 depends on it.
Check with:

```bash
dig +short api.fridah.co.ke
```

## 3. Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker   # or log out and back in
docker compose version   # confirm the plugin is present
```

## 4. Get the code onto the server and configure it

```bash
git clone <your-repo-url> fridah && cd fridah/fridah-backend
# or: scp/rsync the fridah-backend folder up if you're not using git

cp .env.production.example .env
nano .env   # fill in every CHANGE-ME value - see the comments in that file
```

At minimum before going further: **`SECRET_KEY`** (the app now **refuses to start** when `DEBUG=False` and the key is missing, a placeholder, or shorter than 50 characters) (generate with
`python3 -c "import secrets; print(secrets.token_urlsafe(50))"`) and **`DB_PASSWORD`**.
Everything else (M-Pesa, Africa's Talking, WhatsApp, Anthropic) can stay blank — those
features degrade gracefully without credentials, per the root README.

## 5. First boot (no SSL yet)

```bash
docker compose up -d --build db redis backend celery_worker celery_beat
```

This brings up everything except nginx (nginx needs the SSL bootstrap step below
first, or it'll fail to start — see nginx/nginx.conf's comments). Confirm the backend
itself is healthy:

```bash
docker compose logs -f backend   # watch migrations run, then Ctrl+C
curl http://localhost:8000/healthz   # should return {"status": "ok"}
```

## 6. Get an SSL certificate

```bash
chmod +x scripts/init-ssl.sh
./scripts/init-ssl.sh api.fridah.co.ke you@yourdomain.com
```

This script handles the chicken-and-egg problem of nginx needing a cert to start,
and Let's Encrypt needing nginx running to verify domain ownership — see the comments
at the top of `scripts/init-ssl.sh` for exactly what it does. Takes under a minute if
DNS is already pointing at the server.

Once it finishes:

```bash
curl https://api.fridah.co.ke/healthz   # should return {"status": "ok"} over HTTPS
```

The `certbot` service (brought up automatically as part of `docker-compose.prod.yml`,
which `init-ssl.sh` already uses) checks twice a day and renews automatically when the
cert is within 30 days of expiry — nothing further to do for renewal.

## 7. Create an admin account and (optionally) demo data

```bash
docker compose run --rm backend python manage.py createsuperuser
# Only if you want the demo accounts for testing - skip in a real production deploy:
docker compose run --rm backend python manage.py seed_demo_users
```

## 8. Point the frontend at this backend

In `fridah-web`, set `VITE_API_BASE_URL=https://api.fridah.co.ke/api/v1` before
building (see `fridah-web/README.md`), and make sure `CORS_ALLOWED_ORIGINS` in this
server's `.env` includes wherever the built frontend actually ends up hosted.

## Day-to-day operations

**Deploying a new version** (after `git pull` or copying up new code):
```bash
./scripts/deploy.sh
```
Pulls/builds images, runs migrations, collects static files, restarts services, and
waits for `/healthz` to confirm the new containers are actually up before exiting.

**Database backups** (run manually, or add to cron — see below):
```bash
./scripts/backup.sh
```
Dumps to `/var/backups/fridah/`, gzipped, auto-deletes anything older than 14 days.
Put it on a daily cron job:
```bash
crontab -e
# add: 0 3 * * * cd /home/fridah/fridah/fridah-backend && ./scripts/backup.sh >> /var/log/fridah-backup.log 2>&1
```

**Logs:**
```bash
docker compose logs -f backend         # API request/error logs
docker compose logs -f celery_worker   # background task logs (payments, notifications, etc.)
docker compose logs -f celery_beat     # scheduled task logs (rent invoice generation, etc.)
```

**Restarting a single service** (e.g. after an env var change):
```bash
docker compose restart backend
```

**Checking everything is up:**
```bash
docker compose ps   # all services should show "Up" / "healthy"
```

## Troubleshooting

- **nginx won't start / `docker compose up nginx` fails immediately**: almost always
  means the SSL cert doesn't exist yet — run `./scripts/init-ssl.sh` first (step 6).
- **502 Bad Gateway from nginx**: the `backend` container isn't up yet or crashed -
  check `docker compose logs backend`.
- **M-Pesa/WhatsApp/Africa's Talking callbacks aren't arriving**: those providers need
  to reach `https://api.fridah.co.ke/...` directly - confirm the relevant `*_CALLBACK*`
  or webhook URL is registered with the provider's dashboard pointing at this exact
  domain, and that `ufw status` shows 443 open.
- **Certificate renewal seems stuck**: `docker compose logs certbot` - the most common
  cause is DNS having changed since the cert was issued.
