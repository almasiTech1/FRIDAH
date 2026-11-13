"""
Lease/agreement drafting assistant - flagged as a missing AI capability in the
architecture review: FRIDAH had 4 AI agents but none touched lease terms.

Grounds the draft entirely in the Lease row's real data (parties, property,
rent, deposit, dates) plus whatever special terms the landlord/agency types in -
the model's job is turning verified facts into properly-structured legal prose,
not inventing terms. Unlike the rent estimator, there's no safe numeric fallback
if AI is unavailable (a template lease with the wrong clauses is worse than a
clear "try again later"), so this lets AIUnavailableError propagate to the view,
same as the listing generator and maintenance triage.
"""
from .client import call_claude

DRAFTING_SYSTEM_PROMPT = """You are drafting a residential tenancy agreement for a property rental in Kenya. \
You are given the exact, already-verified lease terms from the platform's database - use them exactly as \
given, do not alter the rent, deposit, or dates. Structure the agreement with standard numbered clauses: \
Parties, Premises, Term, Rent and Payment, Security Deposit, Tenant Obligations, Landlord Obligations, \
Utilities, Maintenance and Repairs, Termination, Special Conditions (if any were provided), Governing Law. \
Use clear, professional plain-English legal language appropriate for a Kenyan residential tenancy - not \
overly archaic legalese. If special terms were provided, incorporate them into the Special Conditions clause \
without contradicting the fixed terms above.

Respond with ONLY the drafted agreement text (markdown headings for each clause), no preamble or closing commentary."""

DRAFT_DISCLAIMER = (
    "This is an AI-generated draft based on the lease details on file. It is not legal advice and has not "
    "been reviewed by a lawyer. Review it carefully - and consider having a qualified advocate check it - "
    "before using it for signature."
)


def draft_lease_agreement(lease, special_terms: str = "", user=None) -> dict:
    unit = lease.unit
    prop = unit.property

    prompt = (
        f"Landlord: {lease.landlord.get_full_name() or lease.landlord.username}\n"
        f"Tenant: {lease.tenant.get_full_name() or lease.tenant.username}\n"
        f"Property: {prop.name}, Unit {unit.unit_number}, {prop.address_detail or prop.estate}, "
        f"{prop.town}, {prop.county}\n"
        f"Lease term: {lease.start_date} to {lease.end_date or 'ongoing/month-to-month'}\n"
        f"Monthly rent: KES {lease.rent_amount:,.2f}, due on day {lease.rent_due_day} of each month\n"
        f"Security deposit: KES {lease.deposit_amount:,.2f}\n"
        + (f"\nSpecial terms requested by the landlord: {special_terms}\n" if special_terms else "")
    )

    from django.conf import settings
    text = call_claude(
        feature='lease_drafting',
        model=settings.AI_MODEL_QUALITY,
        system=DRAFTING_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        user=user,
    )
    return {'draft': text.strip(), 'disclaimer': DRAFT_DISCLAIMER}
