"""
Shared command logic for the WhatsApp bot and USSD menu. Both channels ultimately let
a tenant check their balance or log a maintenance request without installing the app,
so the actual lookups live here once.
"""
import logging

logger = logging.getLogger('apps.notifications')


def normalize_phone(raw_phone):
    """
    WhatsApp/Africa's Talking send numbers as '2547XXXXXXXX' or '07XXXXXXXX' (no '+'),
    while FRIDAH stores them as '+2547XXXXXXXX'. Normalize to FRIDAH's stored format.
    """
    digits = ''.join(c for c in raw_phone if c.isdigit() or c == '+')
    if digits.startswith('+254'):
        return digits
    if digits.startswith('254'):
        return '+' + digits
    if digits.startswith('0'):
        return '+254' + digits[1:]
    return '+254' + digits


def get_tenant_by_phone(raw_phone):
    from apps.users.models import User
    return User.objects.filter(phone_number=normalize_phone(raw_phone), role='tenant').first()


def balance_summary_text(tenant):
    """Human-readable outstanding balance summary, used for both WhatsApp replies and USSD screens."""
    from apps.rentals.models import Invoice

    outstanding = Invoice.objects.filter(
        tenant=tenant,
        status__in=[Invoice.Status.PENDING, Invoice.Status.OVERDUE, Invoice.Status.PARTIALLY_PAID],
    ).order_by('due_date')

    if not outstanding.exists():
        return "You have no outstanding balance. You're all caught up!"

    total = sum(inv.balance for inv in outstanding)
    lines = [f"Outstanding balance: KES {total:,.2f}", ""]
    for inv in outstanding[:5]:
        lines.append(f"- {inv.invoice_number}: KES {inv.balance:,.2f} due {inv.due_date}")
    if outstanding.count() > 5:
        lines.append(f"...and {outstanding.count() - 5} more. Open the app for full details.")
    return "\n".join(lines)


def lease_summary_text(tenant):
    from apps.rentals.models import Lease

    lease = Lease.objects.filter(tenant=tenant, status=Lease.Status.ACTIVE).first()
    if not lease:
        return "You don't have an active lease on FRIDAH."
    return (
        f"Unit: {lease.unit}\n"
        f"Rent: KES {lease.rent_amount:,.2f}/month\n"
        f"Lease ends: {lease.end_date}"
    )


def log_maintenance_request(tenant, description):
    from apps.rentals.models import Lease, MaintenanceRequest

    lease = Lease.objects.filter(tenant=tenant, status=Lease.Status.ACTIVE).first()
    if not lease:
        return None, "You don't have an active lease on file, so we can't log a maintenance request."

    req = MaintenanceRequest.objects.create(
        tenant=tenant,
        unit=lease.unit,
        title=description[:100] or "Maintenance request via bot",
        description=description or "(no details provided)",
        category="other",
        priority=MaintenanceRequest.Priority.MEDIUM,
    )
    return req, f"Maintenance request logged (ref: {str(req.id)[:8].upper()}). Your landlord has been notified."
