# Architecture Note: Property Management, Rentals & Hospitality Spec vs. Current Fridah

**Purpose of this note:** per the spec's own §12 build instructions ("inspect existing
models... produce a short architecture note before changing schema"), this identifies what
already exists, what's genuinely missing, and the two or three decisions that need an answer
before writing any migration. No schema has been touched yet.

---

## 1. Existing stack (confirmed by inspection, not assumption)

Django 6 + DRF, PostgreSQL (SQLite for local dev), Celery/Celery Beat for scheduled jobs,
M-Pesa STK/C2B/B2C integration. Relevant apps: `agencies`, `properties`, `rentals`,
`payments`, `bookings`, `services` (maintenance marketplace). 145 backend tests currently
pass; `agencies` alone has 13 tests covering multi-owner isolation and cross-agency access
control.

## 2. The one modeling decision that changes everything downstream

**The spec assumes an agency-first ownership model** ("do not attach an owner directly to a
property without an effective agreement," §3.1). **Fridah's actual model is landlord-first**:
`Property.landlord` is a required direct foreign key to a `User`. An `Agency` attaches to an
*already-existing* property afterward, via `PropertyManagementAssignment` + `ManagementAgreement`
— both optional overlays, not the property's origin.

This isn't a bug — it's because Fridah also serves independent landlords with no agency at
all (see the landlord portal, which predates the agency system). But it means:

- The spec's rule "block payment collection for properties with no active agreement" **cannot
  apply globally** — most properties in this system legitimately have no agency at all, and
  that has to keep working.
- Any new ledger/fund-bucket logic needs to handle both cases cleanly: self-managed
  (payment → landlord, no fee split) and agency-managed (payment → clearing → split by fee
  rule → owner payable + agency fee).

**This needs a decision before Phase 0 starts**, not during it: does agency management stay an
optional overlay (current architecture, less disruptive) or does the spec's agency-first model
become the new baseline (larger migration, forces every existing property/landlord through an
agreement)? The gap analysis below assumes the overlay approach, since rewriting property
ownership is a far bigger, riskier change than anything else in this document.

## 3. What already exists and genuinely matches the spec

| Spec concept | Existing equivalent |
|---|---|
| `Agency`, multi-owner isolation | `Agency` model + 13 passing tests proving one agency can manage two owners without cross-access |
| `ManagementAgreement` (fee, payout rule, signatures, document) | `ManagementAgreement` — has `fee_rule`, `payout_rule`, `signed_by_owner_at`/`signed_by_agency_at`, uploaded document, `terms` JSON |
| `PropertyManagementAssignment` history | Exists, append-only by design, exactly-one-active-per-property enforced |
| `FeePlan` | `AgencyFeeRule` — percentage or flat, reusable across agreements |
| `OwnerStatement` (period, income, expenses, fees, net payable) | Exists with `recompute_net()`; PDF export field present |
| `OwnerPayout` | Exists, M-Pesa B2C by default, idempotent reference generation |
| `AgencyCommission` (separate from owner payout) | Exists, correctly modeled as a distinct record |
| Idempotent monthly rent-charge generation (acceptance criterion #2) | `generate_monthly_rent_invoices` — checks `Invoice.objects.filter(...).exists()` before creating |
| Role-scoped staff access to specific properties | `PropertyStaffAssignment` |
| Audit log for agency actions | `AgencyAuditLog` |
| Vendor invoicing | `ServiceProviderInvoice` (payments app) |
| Deposit *concept* | `Lease.deposit_amount` / `deposit_paid` (boolean only — see gap below) |

This is a real foundation — Phase 0 in the spec's sense (agency tenancy, roles, agreements,
audit log) is largely done already.

## 4. Real gaps (the substantive missing pieces)

### 4.1 No fund-bucket separation — the spec's most important accounting rule

`Payment` has no `fund_bucket` field at all. Rent, deposits, and any future agency fee all
flow through the same `Payment` model with no structural guarantee that deposit money can't
be spent as revenue. This is exactly the rule the spec calls "non-negotiable" (§2.2) and it's
currently unenforced anywhere in the code — it's convention, not a constraint.

### 4.2 No ledger / journal at all

There is no `JournalEntry`, `JournalLine`, `PaymentIntent`, `BankTransaction`, or
`ReconciliationMatch`. Money movement today is a flat sequence of `Payment` rows plus
denormalized totals on `OwnerStatement` (`gross_rent_collected`, `agency_commission`, etc. are
plain decimal fields, recomputed by a method, not derived from a drillable ledger). This fails
acceptance criterion #7 directly: *"each line is drillable to a receipt, payout, invoice, fee
rule or adjustment."* Right now a statement line is a number, not a link.

### 4.3 No reversal model

Acceptance criterion #8 requires a reversal to preserve the original record and create balanced
reversing entries. Nothing in `payments` or `agencies` currently supports this — a bad payment
today would presumably just be edited or deleted, which the spec explicitly forbids (§2.3).

### 4.4 No separation-of-duties enforcement

Confirmed by grep: no code path checks that the user releasing an `OwnerPayout` isn't the same
user who prepared the `OwnerStatement`. Acceptance criterion #9 requires this above a threshold.
`Agency` doesn't even have an `approval_threshold` field yet.

### 4.5 Deposits have no lifecycle

`Lease.deposit_paid` is a boolean. There's no deposit *liability* ledger entry, no move-out
settlement record (itemized deductions, evidence, sign-off), and no `Inspection` model at all.
§4.3's whole deposit lifecycle is unbuilt.

### 4.6 Short-stay/channel reconciliation doesn't exist

`bookings.Listing` and `bookings.Booking` exist for direct/in-app bookings, but there's no
`channel` field, no external reservation ID, no expected-vs-actual payout reconciliation, and
no distinction between "confirmed booking" (forecast) and "cleared payout" (cash) — which is
the specific rule acceptance criterion #5 tests for. Airbnb-style channel import (§4.4) is
entirely new work.

### 4.7 Vendor payment controls are looser than the spec requires

`ServiceProviderInvoice` exists, but there's no `WorkOrder`/`VendorQuote` split, no explicit
"approved invoice + completion evidence required before payment" gate (acceptance criterion #6),
and no `MaintenanceRequest → WorkOrder` structure — maintenance requests go more or less
straight to a service job today.

### 4.8 No co-owner splits, no multi-currency, no hotel folios

All Phase 4 territory (§10) — none of it exists, and the spec itself says not to build it until
folios/night-audit/rate plans are ready, so this is correctly out of scope for now.

## 5. Mapping onto the spec's own phased plan

| Spec phase | Status in this codebase |
|---|---|
| **Phase 0** — agency tenancy, roles, agreements, audit log | **~80% done.** Missing: `fund_bucket` enum, `approval_threshold` on `Agency`, and the agency-first-vs-overlay decision above |
| **Phase 1** — leases, rent charges, deposits, statements | **Partially done.** Leases/invoices/statements exist and are tested; idempotent generation exists. Missing: `PaymentIntent`/`fund_bucket`/journal, real deposit ledger, drillable statement lines |
| **Phase 2** — maintenance, vendor payments, disbursements | **Foundations exist** (`ServiceProviderInvoice`, `AgencyExpense`), but the approval-gate and work-order structure the spec requires are not built |
| **Phase 3** — short stays, channels | **Mostly new.** `Listing`/`Booking` exist for direct bookings only; no channel/reconciliation layer |
| **Phase 4** — hotels, co-owner splits, multi-currency | **Not started**, correctly deferred |

## 6. Open questions before any migration is written

1. **Agency-first vs. overlay** (§2 above) — confirm before Phase 0 work starts, since it
   changes whether `Property.landlord` stays mandatory-and-direct or becomes
   agreement-mediated.
2. **Ledger granularity** — does every existing `Payment`/`Invoice`/`OwnerPayout` need a
   backfilled `JournalEntry`, or only new records going forward? Backfilling is safer for
   auditability but is itself a data migration with real risk on production data.
3. **Payment provider adapters for channel reconciliation** — the spec assumes CSV import
   first, certified API later (§4.4). Confirm CSV-first is acceptable for the initial cut, since
   Airbnb/Booking.com API access requires partner approval that takes time to obtain.
4. **Scope for this pass** — given the size of the gap, do you want the full Phase 0 + Phase 1
   vertical slice per the spec's §12.3 instruction (fund buckets + journal + deposit lifecycle +
   drillable statements, with tests), or a narrower first cut (e.g. fund buckets + journal only,
   without touching deposits/statements yet)?

## 7. What I'd recommend as a starting point

Given the size of this spec, I'd suggest treating **Phase 0 + Phase 1 as the spec itself
prescribes** — a single cohesive vertical slice — rather than picking off individual pieces,
since fund buckets, the journal, and drillable statements are all interdependent (a statement
line can't be drillable without a journal to point at). That's a substantial multi-day build
even scoped tightly, so it's worth confirming direction on the open questions above before I
start writing migrations.
