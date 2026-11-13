# FRIDAH Backend — Django REST API

Django REST Framework API powering FRIDAH: property/lease management, M-Pesa
payments, maintenance & bookings marketplace, agency staff/permissions,
Claude-powered AI tools, and rule-based fraud detection.

**Requires:** Python 3.12+ (Docker image uses 3.14), PostgreSQL 16, Redis 7.

> This file covers backend setup only. See the [root README](../README.md) for
> the full-stack Docker quick start, demo login credentials, and what's built.
> Deploying this to a live server? See [`DEPLOYMENT.md`](DEPLOYMENT.md) for the
> full VPS setup (SSL, nginx, backups, deploy script) — the steps below are for
> local development only.

---

## Option A — Docker (recommended, matches production)

```bash
cp .env.example .env
```

Open `.env` and set at minimum `SECRET_KEY` to any long random string — everything
else (M-Pesa, WhatsApp, Africa's Talking, Anthropic) is optional and degrades
gracefully without it.

```bash
docker compose up --build
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py seed_demo_users
```

- API base: `http://localhost:8000/api/v1/`
- Swagger docs: `http://localhost:8000/api/docs/` (requires login)
- Django admin: `http://localhost:8000/admin/`

This starts Postgres, Redis, the API (gunicorn), a Celery worker, Celery Beat, and
nginx as reverse proxy — the same topology as production, minus TLS certs.

---

## Option B — Manual setup (no Docker)

Needs PostgreSQL 16 and Redis 7 running locally, **or** set `USE_SQLITE=True` in
`.env` to skip both and use a local sqlite file instead (good for a quick look or
running the test suite, not for anything resembling production).

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt --break-system-packages

cp .env.example .env
# edit .env: either point DB_HOST/DB_NAME/DB_USER/DB_PASSWORD/REDIS_URL at your
# local Postgres/Redis, or set USE_SQLITE=True to skip both

python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo_users
python manage.py runserver
```

### Background jobs (optional, needed for scheduled features)

Lease renewal notices, nightly tenant risk-score recompute, fraud-detection
sweeps, and flat-fee utility billing run on Celery Beat. To have them fire, run
these in separate terminals (same venv):

```bash
celery -A config worker -l info
celery -A config beat -l info
```

### Demo logins

`seed_demo_users` creates one account per role, all sharing the password
`Fridah@2026` — including `agency@fridah.co.ke`, which already owns an active
demo agency ("Fridah Demo Property Managers") with its standard staff roles
seeded, so it lands straight on a populated agency dashboard. Full table and
notes in the [root README](../README.md#demo-logins).

---

## Running the test suite

```bash
pip install -r requirements-dev.txt --break-system-packages
USE_SQLITE=True SECRET_KEY=any-value DEBUG=True python manage.py migrate
USE_SQLITE=True SECRET_KEY=any-value DEBUG=True pytest apps/ tests/ -q
```

72 tests as of this writing (auth/role-escalation, file upload validators,
WhatsApp/USSD webhook signature verification, payments/advances, agencies,
fraud detection, AI graceful degradation, KYC review, property approval). CI
runs this automatically on every push via `.github/workflows/backend-ci.yml`.

For a coverage report: add `--cov=apps --cov=common --cov-report=term-missing`.

---

## Environment variables

Full list with inline explanations is in `.env.example`. The ones that actually
gate a feature (rather than just having a sensible default):

| Variable | Gates | Required in prod? |
|---|---|---|
| `SECRET_KEY` | Django | **Yes** |
| `DB_*` | PostgreSQL connection | Yes (unless `USE_SQLITE=True`) |
| `REDIS_URL` | Celery broker / cache / rate limiting | Yes (unless `USE_SQLITE=True` for local dev — Celery still needs Redis regardless) |
| `MPESA_*` | Daraja API (STK push, paybill, B2C payouts) | No — payments log/no-op in dev without it |
| `WHATSAPP_APP_SECRET` | Verifies WhatsApp webhook signatures (`X-Hub-Signature-256`) | **Yes if you enable the WhatsApp bot** — without it, incoming webhook POSTs are accepted with no proof they came from Meta |
| `USSD_SHARED_SECRET` | Verifies USSD callback requests | **Yes if you enable the USSD menu** — Africa's Talking doesn't sign callbacks, so this is the only thing stopping anyone who finds the callback URL from submitting requests as any tenant |
| `ANTHROPIC_API_KEY` | AI features (search, rent estimator, listing generator, maintenance triage) | No — AI endpoints return a clean 503 without it |
| `USE_SQLITE` | Swap Postgres for a local sqlite file | No — local/CI convenience only, never use in production |

---

## Project layout

```
fridah-backend/
├── apps/            One Django app per domain (users, properties, rentals,
│                     payments, agencies, ai, analytics, fraud, notifications,
│                     bookings, services, ussd, visitors, audit)
├── common/           Cross-app shared code (e.g. common/validators.py — file
│                     upload extension/size validation)
├── config/           settings.py, urls.py, celery.py
├── tests/            Cross-app pytest suite (fixtures in tests/conftest.py)
├── nginx/            nginx.conf used by docker-compose
├── docker-compose.yml, Dockerfile
└── smoke_test*.py    Standalone smoke tests (predate the pytest suite; still
                       useful as a quick end-to-end sanity check)
```
