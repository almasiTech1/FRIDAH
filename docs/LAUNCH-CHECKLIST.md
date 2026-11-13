# FRIDAH launch checklist

Work top to bottom. Items marked **(found in review)** come from reading this repository's own config.
The deployment steps themselves are in `fridah-backend/DEPLOYMENT.md`; this list is what to verify around them.

## 1. Before you put real money through it
- [ ] **Safaricom production credentials** (Daraja): live shortcode, passkey, consumer key/secret; callback URLs registered and reachable over HTTPS (`ufw status` shows 443 open).
- [ ] Test on the sandbox first, then one real small payment in production. Test **failed**, **cancelled by user**, **timeout** and **duplicate callback** cases; confirm an invoice is never marked paid twice and a failed payment never marks it paid.
- [ ] Daily **reconciliation** between Safaricom statements and the Payments table (admin has a Reconciliation page).
- [ ] Refund and payout flows tried end to end with real (small) amounts.

## 2. Security
- [x] `SECRET_KEY`: the app now **refuses to start** with `DEBUG=False` and a missing, placeholder or short (under 50 characters) key. Still set a fresh random value yourself.
- [ ] `DEBUG=False`; `DB_PASSWORD` strong and not the default.
- [x] `TRUSTED_PROXY_COUNT` (1 = nginx only, 2 = Cloudflare in front of nginx) is now the single setting for both the API rate limits and the M-Pesa IP check. **Set it correctly on the server.**
- [x] Anonymous limit raised to 600/hour (login stays 10/min). Watch for `429` in the logs after launch and adjust `THROTTLE_ANON`.
- [x] Login and OTP limits keep working in-process if Redis goes down (ordinary traffic stays available). Still monitor Redis.
- [x] Private uploads (ID scans, agreements, statements, receipts, property documents, maintenance photos) are no longer served by nginx. They use random file names and short-lived signed links (`PRIVATE_FILE_URL_TTL`, default 5 minutes). Deploy the new `nginx.conf`, run `python manage.py migrate`, and check that `https://<api>/media/kyc_documents/anything.jpg` returns 404. Django admin file links to these folders no longer open; use the app's signed links.
- [ ] Set `ADMIN_URL` to a random address (not `/admin/`) and, if you have a fixed office or VPN address, `ADMIN_ALLOWED_IPS`.
- [x] Libraries upgraded (Pillow 13.0.0, PyJWT 2.15.0, cryptography 50.0.0, DRF 3.18.2, vue-i18n 11.4.18, plus npm fixes): pip-audit reports no known vulnerabilities and `npm audit --omit=dev` reports 0. Eight advisories remain in test tooling only (vitest, tinypool and similar), which is not shipped to users; fixing them needs a major test-tool upgrade.
- [x] The web build now writes `dist/_headers` and `dist/security-headers.nginx.conf` (Content-Security-Policy and other headers, using your `VITE_API_BASE_URL`). Make sure your web host applies them.
- [ ] CORS: `CORS_ALLOWED_ORIGINS` lists only your real web domains.
- [ ] Two-factor or a strong password rule for admin accounts. Remove demo accounts (`seed_demo_users`) from production.
- [ ] Keep dependencies updated (`pip list --outdated`, `npm audit`) on a schedule.

## 3. Data safety
- [ ] `scripts/backup.sh` is on a daily cron. **(found in review)** It writes only to the same server (`/var/backups/fridah`). Copy backups **off the server** (object storage or another provider); a lost server would otherwise lose the backups too.
- [ ] **Restore a backup into a scratch database and check it.** An untested backup is not a backup.
- [ ] Uploaded files (`media/`) are backed up too, not just the database.
- [ ] Data-protection: register with the Office of the Data Protection Commissioner if required, publish privacy and terms pages reviewed by a lawyer, and decide how long KYC documents are kept.

## 4. Monitoring (know before your users tell you)
- [ ] `sentry-sdk` is already in requirements: create a Sentry project and set its DSN so errors reach you.
- [ ] External uptime check on `https://api.fridah.co.ke/healthz` (UptimeRobot, Better Stack) alerting your phone.
- [ ] Alerts for: disk above 80%, memory pressure, Celery queue growing, database connections near the limit, certificate expiry.
- [ ] Check that Celery Beat jobs (rent invoice generation, reminders) actually run, by looking at one cycle in the logs.

## 5. Performance
- [ ] Run `fridah-backend/loadtest/` against staging (see its README): `smoke`, then `load`, then `stress`. Record the numbers.
- [ ] Rough guide (an estimate, not a measurement): one 4-worker server on 2 vCPU / 4 GB suits a small launch, a few hundred active users. The load test replaces this guess with your real figure.
- [ ] If the test shows limits: add CPU/RAM first, move Postgres to a managed database, put Redis on its own instance, and run Celery workers on a separate machine. The web app is static files, so serve it from a CDN.
- [ ] Database indexes on the columns your slowest list pages filter by (check slow-query logs after a week of real data).

## 6. The web app
- [ ] `fridah-web/.env`: `VITE_API_BASE_URL`, Google Maps key, and the `VITE_COMPANY_*` invoice details (name, KRA PIN, paybill, logo).
- [ ] Build with `npx vite build` and host on Cloudflare Pages (or similar) with HTTPS and the SPA redirect so deep links like `/tenant/invoices` work on refresh.
- [x] Monthly trend charts now plot real month-by-month figures from the API (landlord, hotel, admin). If the API returns no history they fall back to a chart labelled "Estimated trend". The agency dashboard has one too; the service-provider dashboard shows monthly earnings (wallet credits after commission). The landlord "Collected this month" tile and its chart now use the same definition (completed payments, part-payments included).

## 7. People and process
- [ ] Support contact visible in the app, and someone on call for payment problems in the first two weeks.
- [ ] A short written rollback plan: how to redeploy the previous version (`scripts/deploy.sh` with the last good commit) and restore the last backup.
- [ ] Pilot with 1 to 3 real landlords before opening to everyone, and watch their first rent cycle closely.
