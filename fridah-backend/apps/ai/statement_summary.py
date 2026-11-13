"""
Owner statement AI summary - turns an OwnerStatement's already-computed figures
into a 2-3 sentence plain-English recap for the landlord, in the same spirit as
the rent estimator's `demand_notes`.

Flagged as a missing capability in the AI/Analytics architecture review: statements
were numbers-only, with no narrative layer, despite the platform already having 3
other text-generation AI features following this exact grounded-summary pattern.

Deliberately does NOT compute any numbers itself - every figure it's given is
already-real, already-verified statement data (see apps.agencies.services.
generate_owner_statement). The model's only job is to phrase what already happened
in the DB, not to calculate or estimate anything, so there's no risk of it
inventing a number that doesn't match the actual statement.
"""
import logging

from .client import call_claude, AIUnavailableError

logger = logging.getLogger('apps.ai')

SUMMARY_SYSTEM_PROMPT = """You are writing a short, plain-English summary of a property owner's monthly \
statement for a Kenyan property management platform. You are given the exact already-computed figures for \
this statement - do not recalculate or second-guess them, just explain what they mean in 2-3 sentences a \
busy landlord can read in five seconds. Mention anything that stands out (high vacancy loss, arrears, or a \
larger-than-usual commission/expense deduction) in plain terms. Do not repeat every number verbatim - the \
full breakdown is already shown elsewhere on the statement; your job is the one-glance takeaway.

Respond with ONLY the summary text, no preamble, no markdown, no JSON."""


def summarize_statement(statement, user=None) -> str:
    """
    Returns a short plain-English summary string. Falls back to a simple templated
    sentence (not an error) if AI is unavailable, since a statement should never be
    blocked on the AI layer - matches the rent estimator's graceful-degradation approach.
    """
    from django.conf import settings

    prop = statement.property
    listing = statement.listing
    if prop:
        label = f"Property: {prop.name}, {prop.town}, {prop.county}\n"
    else:
        label = f"Listing: {listing.name}, {listing.town}, {listing.county} ({listing.get_listing_type_display()})\n"
    prompt = (
        label +
        f"Period: {statement.period_start} to {statement.period_end}\n"
        f"Gross rent collected: KES {statement.gross_rent_collected:,.2f}\n"
        f"Vacancy loss: KES {statement.vacancy_loss:,.2f}\n"
        f"Arrears outstanding: KES {statement.arrears:,.2f}\n"
        f"Agency commission: KES {statement.agency_commission:,.2f}\n"
        f"Approved expenses deducted: KES {statement.approved_expenses:,.2f}\n"
        f"Other deductions: KES {statement.other_deductions:,.2f}\n"
        f"Net payable to owner: KES {statement.net_payable:,.2f}\n"
    )

    try:
        text = call_claude(
            feature='statement_summary',
            model=settings.AI_MODEL_FAST,
            system=SUMMARY_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            user=user,
        )
        return text.strip()
    except (AIUnavailableError, Exception) as e:
        logger.warning("Statement summary: AI unavailable, falling back to templated summary: %s", e)
        return (
            f"For {statement.period_start.strftime('%B %Y')}, {prop.name} collected "
            f"KES {statement.gross_rent_collected:,.0f} in rent"
            + (f" with KES {statement.arrears:,.0f} still outstanding in arrears" if statement.arrears else "")
            + f". After commission and deductions, KES {statement.net_payable:,.0f} is payable to the owner."
        )
