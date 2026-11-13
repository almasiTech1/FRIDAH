# Implementation notes - Developer Enhancement Requirements Report (backend)

Run `python manage.py migrate` (properties 0005, rentals 0008, tax 0001, notifications 0006, payments 0006). No seed data is required.

## 1. Dual approval for agency-submitted properties
- `Property.review_state` (awaiting_landlord / awaiting_admin / approved / changes_requested / rejected / withdrawn),
  `submission_version`, `submitted_by`, `submitted_by_agency`, `requires_landlord_approval`.
- Agency-submitted => landlord AND admin must approve the CURRENT version (any order). Landlord/admin-created => admin only.
  Admin-created => published immediately.
- `status == active` is only reachable through `apps/properties/approvals.py`; `Property.save()` refuses otherwise.
- Material edit (`PROPERTY_MATERIAL_FIELDS` setting, default in approvals.py) bumps the version, unpublishes and re-queues.
- Endpoints: `POST /properties/<id>/review/` (landlord or admin; party derived from caller), `POST /properties/<id>/approval/`
  (admin: approve|reject|request_changes|suspend|archive|reinstate), `POST .../resubmit/`, `POST .../withdraw/`,
  `GET .../approvals/` (immutable trail), `GET /properties/review-queue/` (landlord: theirs; admin: all, with age_days).
- Security fixes: `status` no longer writable via PATCH; unapproved properties/units/reviews/cost-of-living return 404 to non-related users.
- Open product decision: which fields count as "material" - adjust the setting.

## 2. Scheduled owner statements
`apps.agencies.tasks.generate_scheduled_owner_statements` (daily beat; monthly for previous month, annual during January).
Idempotent. Self-managed => issued automatically; agency-managed => DRAFT for agency review. Owners never see drafts.

## 3. Tax (KRA) module - `apps/tax`
Configurable, effective-dated, versioned rules. NO rates are seeded: configure and have them validated by a qualified Kenyan
tax adviser. Calculations are ESTIMATES (clearly labelled) until an assessment/payment is recorded; every adjustment needs a reason
and is kept in `TaxAdjustment` + platform audit log. Endpoints under `/api/v1/tax/` (types, rules, records, estimate, adjust, summary, export).

## 4. Amenity charges
`AmenityCharge` (monthly/one-off, all units or selected units), `AmenityExemption`, itemised `Invoice(invoice_type='amenity')`
paid through the normal M-Pesa/receipt flow. Daily idempotent billing task; audited waivers (`POST /invoices/<id>/waive/`, unpaid only).

## 5. Other
- `GET /api/v1/receipts/verify/?reference=` public, throttled, non-sensitive receipt verification.
- `GET /api/v1/analytics/dashboard/admin/portfolio/` admin portfolio overview with filters (county, property_type, landlord, agency, date range).

## 6. Tenant reminders (3.10)
`apps.payments.tasks.send_payment_reminders` now runs hourly (de-duplicated per invoice+trigger via `RentReminderLog`):
states the outstanding BALANCE, names the charge type (rent/amenity/utility), carries a deep link (`/tenant/invoices?invoice=<id>`),
honours `payment_alerts` (in-app kept, SMS/push skipped) and quiet hours (default 21:00-07:00 Africa/Nairobi via
`NOTIFICATION_DEFAULT_QUIET_HOURS`; per-user `quiet_hours_start/end`). Held reminders are not logged, so the next run after the
window sends them. One failing invoice never stops the batch. `apps.notifications.tasks.retry_failed_deliveries` (every 30 min)
retries failed SMS/push up to 3 attempts, recording each attempt on `NotificationDelivery`.

## 7. Payments hardening review (3.8) - findings and fixes
| # | Finding | Fix |
|---|---|---|
| 1 | `get_client_ip` trusted the FIRST `X-Forwarded-For` entry, which the caller controls: anyone could pass the Safaricom IP allowlist and forge a "payment successful" callback. | Client IP is now the Nth entry from the RIGHT (`TRUSTED_PROXY_COUNT`, default 1; 0 = ignore the header). **Set this to match your real proxy chain.** |
| 2 | `mark_payment_completed` was not idempotent and not atomic: a retried Safaricom callback, or the callback racing the Celery poller, applied the invoice payment and credited the landlord wallet more than once. | Row-locked, atomic, returns early if already completed. |
| 3 | Callback `Amount` was never compared with the amount requested. | Mismatch => payment set to `disputed`, nothing applied, critical audit entry. |
| 4 | A late/duplicate failure notice could flip a COMPLETED payment to FAILED. | Failures only apply to pending/processing payments. |
| 5 | C2B validation endpoint had no IP check. | Same allowlist check as the other callbacks. |
| 6 | Payment statuses lacked reversed / refunded / disputed. | Added (migration payments 0006). |

Still open (needs product/finance decisions, not code alone): refund and reversal workflows with approval limits, a settlement
ledger/fees table, automatic reconciliation reports against the Daraja statement, and Daraja transaction-status verification
before crediting. A `disputed` payment is resolved by an administrator: `POST /payments/<id>/resolve-dispute/` with `confirm` (applies it once) or `void` (credits nothing), reason required and audited; the admin Payments page has the controls.

## 8. Web and mobile UI
Web (`fridah-web`): landlord Approvals / Tax / Amenities pages, waive action on Invoices, admin Review Queue / Portfolio /
Tax Settings pages, approval-state badges on both Properties pages. Mobile (`fridah-mobile`): landlord Approvals / Tax /
Amenities screens (reached from the dashboard quick actions), admin Review Queue (from Properties). Motion: staggered list entry,
animated skeletons, and a global `prefers-reduced-motion` override on web; `AccessibilityInfo` reduce-motion hook on mobile.
Tax *creation of estimates*, rule configuration and amenity creation are web-only; mobile is view/act.

## 9. Agencies are never self-registered
- `POST /api/v1/agencies/` is administrator-only (403 for every other role, including existing agency admins). There is no public
  path to an agency: self-registration only allows tenant, landlord, service provider and hotel owner.
- The administrator registers the agency **and creates its first Agency Admin's login** in one step (`admin_first_name`,
  `admin_last_name`, `admin_email`, `admin_phone_number` - email and phone must be unused). The person never signs up themselves.
  The agency is `active` immediately; standard roles are seeded; the registration is audited with the admin as actor; the admin is not
  added as a member. The account carries the ordinary base role `landlord` (the platform has no separate agency role - agency
  access comes from the `AgencyMembership`, as for the demo agency account).
- The account gets a random 12-character temporary password, returned **once** in the response (`credentials`) for the admin to hand
  over and never stored in clear or retrievable. `User.must_change_password` is set; `FridahJWTAuthentication` then refuses every API
  call except change-password / profile / logout until the password is replaced (and the new password must differ). Web and mobile
  show a forced "Set your own password" screen.
- There is no self-service password reset, so `POST /agencies/<id>/reset-admin-password/` (admin) issues a new temporary password
  (audited). `POST /agencies/<id>/status/` (admin) activates / suspends / archives; suspended agencies leave the directory.
- Removed: web sidebar "Manage properties as an Agency" link, the "Create an Agency" form on the agency dashboard and the router
  bootstrap exception; mobile `AgencyOnboardingLink`, `AgencyOnboardingScreen`, the profile links (tenant, landlord, service
  provider, hotel owner) and the create form on the agency dashboard.
- Added: web Admin -> Agencies page (register, one-time credentials panel, reset login, activate/suspend); mobile Admin ->
  Properties -> Agencies screen with the same.
- Existing agencies are untouched. Self-registered agencies left in `pending_approval` can be activated from the Agencies page.
- Staff are not self-registered either: `POST /agencies/<id>/members/invite/` now creates the login when the email has no account
  (`first_name`, `last_name`, `phone_number` required; temporary password returned once; active membership; must change password at
  first login). An email that already has an account is invited as before. `POST /agencies/memberships/<id>/reset-password/` issues a
  new temporary password (staff, by anyone with manage-staff; an Agency Admin's login only by a platform administrator). Web and
  mobile Staff screens updated.

## 10. Refunds, reversals, reconciliation and settlement
Backend `apps/payments/refunds.py`, `reconciliation.py` (migration payments 0007). **The policy values below are defaults I chose; confirm
them with finance** (all in settings / `.env`).
- **Refund** (customer wants money back) or **reversal** (mistaken/duplicate payment; always the full remaining amount, admin-approved).
  Requested by the payer, the recipient (landlord/host) or an administrator, against a COMPLETED payment within `REFUND_WINDOW_DAYS` (180).
  Total refunded can never exceed the payment; open requests count against the remainder.
- **Approval limits + maker-checker:** up to `REFUND_ADMIN_APPROVAL_ABOVE` (KES 5,000) the recipient or an admin may approve; above it, and for
  every reversal, only an admin. Nobody approves their own request. (With a single admin who files a request, a second approver is
  needed - or set `REFUND_ALLOW_SELF_APPROVAL=True`, not recommended.)
- **Approval reverses the books atomically:** invoice allocations newest-first and invoice status, booking paid amount, and the
  recipient's wallet by the same share of the net they were credited (platform commission is returned to the customer, i.e. absorbed
  by the platform). If the recipient has already withdrawn the money, approval is refused unless an administrator approves with
  "allow negative balance" (recovered from future earnings). Fully refunded payments become `refunded`.
- **Paying the customer back.** Two ways, both admin-only. (1) Manual: the admin sends the money and records the M-Pesa reference
  (`POST /refunds/<id>/mark-paid/`; references are unique). (2) Automatic, **off by default** (`MPESA_B2C_REFUNDS_ENABLED=True`, needs the
  `MPESA_INITIATOR_*` settings and Safaricom certificate): `POST /refunds/<id>/pay-out/` sends a B2C payment from the business float; the
  existing B2C result callback then marks the refund paid out with the M-Pesa receipt, or leaves it approved (admins notified) for a retry or a
  manual payout. Refund payouts credit/debit no wallet. B2C pays whole shillings only, so a refund with cents must be paid manually. The payout
  row is committed before the network call (a double click cannot send twice) and failed attempts are kept. **This code is tested against a
  mocked Daraja client, never against live or sandbox Safaricom** - run a sandbox payout before enabling it. Refunds approved but unpaid for 3+
  days are flagged by reconciliation.
- **Editable policy:** the approval limit and refund window are edited by an administrator on the Admin -> Refunds page (`GET/PUT /refunds/policy/`,
  audited before/after; the `.env` values are only the initial defaults). Allowing people to approve their own requests and turning automatic
  payouts on are deliberately configuration-only, not editable in the UI.
- Endpoints: `POST /payments/<id>/refunds/`, `GET /refunds/`, `POST /refunds/<id>/approve|reject|cancel|mark-paid/`.
- **Reconciliation** (admin): `POST /reconciliation/runs/internal/` (also a daily task for yesterday) checks that every completed payment
  has exactly one wallet credit of the right size after refunds, and lists stuck, disputed and unpaid-refund items.
  `POST /reconciliation/runs/statement/` uploads the Safaricom statement CSV and matches lines by receipt number (amount mismatches,
  money on the paybill/statement but not on the platform, platform payments missing from the statement). Items stay open until resolved
  with a note (audited). This works from the official statement rather than calling the Daraja API.
- **Settlement summary:** `GET /settlement/summary/?start=&end=` - collected, commission, credited to recipients, refunds (approved / paid /
  awaiting payout), amounts recovered from wallets, payouts sent, and what the platform currently owes in wallets.
- UI: web (tenant "My Refunds" + request button on Payments, landlord Refunds, admin Refunds + policy card + payouts + Payments buttons +
  Reconciliation page + My Account). Mobile: tenant/landlord/admin Refunds screens (request from your completed payments, approve, reject,
  cancel), admin payouts (send via M-Pesa when enabled, record reference), admin Reconciliation (settlement, run check, resolve items) and
  admin My Account (notification preferences). On mobile only these are web-only: reversals (full-amount, admin/recipient) and uploading a
  Safaricom statement CSV.
- **Statement "pulls":** Daraja has no statement-download API. Its Transaction Status API checks one receipt at a time, asynchronously; it is not
  implemented. Reconciliation therefore uses the statement CSV the finance team downloads from the M-Pesa portal.

### Bugs found and fixed in existing payment code while doing this
- **Callback URLs were wrong.** The client asked Safaricom to call `/api/payments/mpesa/...` but the routes are `/api/v1/payments/mpesa/...`,
  so STK, B2C and C2B callbacks would 404 unless a proxy rewrote them. Fixed and covered by a test that resolves every path the client sends.
  (Re-register your C2B URLs after deploying.)
- **B2C failure callbacks were not idempotent.** A repeated failure notice credited the landlord's wallet again each time (and a failure for a
  payout that never debited a wallet still credited it). Now applied once, only when a wallet debit exists.

## 11. Tests
- Backend: `pytest` in `fridah-backend`.
- Web unit/component/integration: `npm test` in `fridah-web` (Vitest; includes router-guard integration tests with only the network mocked).
- Mobile: `npm test` in `fridah-mobile` (Jest + React Native Testing Library; rendered screens and components).
- **Real-browser end-to-end (Playwright): `fridah-web/e2e`, 9 scenarios x 2 viewports. WRITTEN BUT NEVER EXECUTED** - the environment they were
  written in has no browser. They parse and list (`npx playwright test --list`) but expect some selector adjustments on first run. Run:
  `npm run e2e:install && npm run e2e` (the API is stubbed at the network layer; no backend needed).
- No on-device (Detox/Maestro/emulator) tests exist for the mobile app.

## Not yet done
- First successful run of the Playwright specs; on-device mobile e2e.
- A Daraja sandbox run of the automatic refund payout, and of STK/B2C/C2B callbacks at the corrected URLs.
- Daraja Transaction Status verification of individual receipts (optional).
- Mobile: reversals and statement CSV upload (web-only).
- The mobile admin dashboard shows hard-coded demo numbers if the stats request fails (existing behaviour in `screens/admin/DashboardScreen.tsx`);
  it should show an error instead.
