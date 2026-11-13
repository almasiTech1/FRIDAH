# FRIDAH — Kenya PropTech Super App

A full-stack platform for residential and hospitality rental management in Kenya:
property & lease management, hotel/BnB bookings, a maintenance service marketplace,
M-Pesa payments, and a set of Claude-powered AI tools (property search, rent
estimation, listing generation, maintenance photo triage).

**Stack:** Django REST Framework (backend) · Vue 3 + Vite (web) · React Native (mobile)

```
fridah-complete/
├── fridah-backend/    Django REST API (Python 3.14, Django 6)
├── fridah-web/        Vue 3 web app (landlord/tenant/admin/provider/hotel portals + public site)
└── fridah-mobile/     React Native app (native android/ios projects included)
```

---

## Quick Start (Docker — recommended)

```bash
cd fridah-backend
cp .env.example .env
```

Open `.env` and set at minimum:

```
SECRET_KEY=<any long random string>
```

Everything else (M-Pesa Daraja, WhatsApp Cloud API, Africa's Talking, Anthropic,
Google Maps) is optional — those integrations degrade gracefully without keys
configured; you just won't be able to exercise that specific feature.

```bash
docker compose up --build
```

In a second terminal, once the containers are healthy:

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py seed_demo_users
```

- API base: `http://localhost:8000/api/v1/`
- API docs (Swagger): `http://localhost:8000/api/docs/`
- Django admin: `http://localhost:8000/admin/`

Then start the web app (see [Web](#web-vue) below) and log in with the credentials
in the [Demo Logins](#demo-logins) section.

---

## Backend (Django) — manual setup, without Docker

See [`fridah-backend/README.md`](fridah-backend/README.md) for the full backend
guide (Docker vs. manual setup, running the 72-test pytest suite, background
jobs, and every environment variable explained). Quick version:

Requires Python 3.14, PostgreSQL 16, and Redis 7 running locally.

```bash
cd fridah-backend
python3.14 -m venv venv && source venv/bin/activate
pip install -r requirements.txt --break-system-packages

cp .env.example .env
# edit .env: point DB_HOST / DB_NAME / DB_USER / DB_PASSWORD / REDIS_URL at your local instances

python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo_users
python manage.py runserver
```

### Background jobs (optional but needed for scheduled features)

Lease renewal notices, nightly tenant risk-score recompute, fraud-detection sweeps,
and flat-fee utility billing all run on a Celery Beat schedule. To have them actually
fire, run these in separate terminals (same venv):

```bash
celery -A config worker -l info
celery -A config beat -l info
```

### Environment variables of note

| Variable | Purpose | Required? |
|---|---|---|
| `SECRET_KEY` | Django secret key | **Yes** |
| `DB_*` | PostgreSQL connection | Yes (Docker sets these for you) |
| `REDIS_URL` | Celery broker / cache | Yes (Docker sets this for you) |
| `MPESA_*` | Daraja API (STK push, paybill, B2C payouts) | No — payments no-op/log in dev without it |
| `WHATSAPP_*` | WhatsApp Cloud API (bot) | No |
| `AT_*` / `USSD_SERVICE_CODE` | Africa's Talking (SMS, USSD) | No |
| `ANTHROPIC_API_KEY` | AI features (search, rent estimator, listing generator, maintenance triage) | No — AI endpoints return a clean 503 without it |
| `AI_MODEL_FAST` / `AI_MODEL_QUALITY` | Which Claude models the AI features use | No — sensible defaults set |

Full list with defaults is in `fridah-backend/.env.example`.

---

## Web (Vue)

```bash
cd fridah-web
npm install
npm run dev
```

Opens at `http://localhost:5173`. Talks to the backend at `http://localhost:8000/api/v1`
by default (see `src/api/client.ts` / `VITE_API_BASE_URL` if you need to point it
elsewhere).

Optional, for interactive maps (property/hotel search, address autocomplete on
listing forms, office location on the Contact page):

```bash
# fridah-web/.env
VITE_GOOGLE_MAPS_API_KEY=your-key-here
```

Get a key from the [Google Cloud Console](https://console.cloud.google.com/google/maps-apis)
with "Maps JavaScript API" enabled. Without it, map components show a clean
"Map unavailable" placeholder instead of breaking.

Production build: `npm run build` (output in `dist/`).

---

## Mobile (React Native)

See [`fridah-mobile/README.md`](fridah-mobile/README.md) for full setup — the
native `android/` and `ios/` project folders **are included** in this repo and
already correctly configured, so it's a normal `npm install` +
`react-native run-android` / `run-ios` (plus `pod install` for iOS), not a
from-scratch native scaffold.

---

## Demo Logins

Created by running `python manage.py seed_demo_users` (safe to re-run — it won't
duplicate accounts). **All accounts use the same password:**

```
Fridah@2026
```

| Role | Email |
|---|---|
| Admin | `admin@fridah.co.ke` |
| Tenant | `tenant@fridah.co.ke` |
| Landlord | `landlord@fridah.co.ke` |
| Service Provider | `provider@fridah.co.ke` |
| Hotel / BnB Owner | `hotel@fridah.co.ke` |
| Agency (property manager) | `agency@fridah.co.ke` |

Notes:
- The **Admin** account is also a Django superuser — it works for both the in-app
  admin dashboard and `/admin/` (Django's built-in admin panel).
- The **Tenant** account is pre-verified (KYC), so it lands straight on the
  dashboard instead of the verification prompt.
- The **Agency** account already owns an active agency ("Fridah Demo Property
  Managers") with its standard staff roles seeded, so it lands straight on the
  agency dashboard. Agencies can only be registered by an **administrator**
  (Admin portal → Agencies, or `POST /api/v1/agencies/`); tenants, landlords,
  service providers and hotel owners have no way to create one. The admin creates
  the agency and its first Agency Admin's login together; that person gets a
  temporary password and must change it at first login.
- These accounts start with **no data attached** — no properties, leases, or
  invoices — so dashboards will look empty at first. That's expected; create a
  property as the landlord account (or add data via `/admin/`) to populate things.

---

## What's built

**Core:** property & unit management, leases with digital e-signatures, invoicing,
M-Pesa (STK push, paybill auto-reconciliation, B2C payouts), maintenance requests
& a service-provider marketplace, hotel/BnB bookings with an availability calendar,
tenant risk scoring, tenant blacklist, secure per-property document vault, lease
renewal workflow, dark mode, Swahili i18n, WhatsApp bot, USSD menu, a 15-page public
marketing site with Google Maps (search, address autocomplete, "near me",
directions), utility billing (metered + flat-fee), visitor QR management, and
rule-based fraud detection (duplicate listings, suspicious payment patterns,
abnormal pricing, duplicate national IDs).

**Agency management:** an agency can manage properties on behalf of one or more
landlords, or listings on behalf of one or more hotel/BnB owners — agreements,
staff roles, fee rules, periodic owner statements (revenue, agency commission,
net payable), M-Pesa B2C owner payouts, and an audit log. The owner (landlord or
hotel owner) always keeps full visibility into anything an agency manages for
them: management terms (fee %, payout rule, since when), tenants/leases or
guests/bookings, and revenue collected per period via a read-only Statements
page — without needing any agency role themselves. A dedicated **Managed & Revenue** page
(landlord and hotel-owner portals) shows each property or listing, which agency manages it, who is
living or staying there, and the revenue collected for any chosen period. Agencies, in turn, see the
registered owner (name, phone, email) on every property they manage.

**AI features** (via the Claude API, gracefully disabled without `ANTHROPIC_API_KEY`):
- **Property Assistant** — natural-language search ("2-bedroom under KSh 30,000 near
  Kilimani with parking") parsed into real filters, with a short AI explanation per result
- **Rent Estimator** — recommendation grounded in real comparable units already on
  the platform, not a generic guess
- **Listing Generator** — upload photos + facts, get back title/description/amenities/SEO keywords
- **Maintenance Assistant** — tenant uploads a photo, gets instant category/priority/safety triage

**Known gaps** (not built): referral program, loyalty points, property valuation,
predictive vacancy analytics, revenue forecasting, admin BI dashboard, mobile
screens for the AI features (web-only right now), a dedicated agency-side UI for
managing hotel/BnB listings (the API supports it fully; the agency web portal's
own screens are still rental-property-only), and per-listing staff access
restriction (agency staff permissions are currently agency-wide for listings,
whereas properties support restricting a staff member to specific ones).

---

## Support

- API documentation: `http://localhost:8000/api/docs/` once the backend is running
- Something not working? Check `fridah-backend/.env` has `DEBUG=True` for full
  error pages while developing locally.


## Glass dashboards
The web portals use a skinnable glass design system (6 looks, command palette, interactive charts). See `fridah-web/docs/DESIGN-SYSTEM.md`.
