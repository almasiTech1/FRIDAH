def log_action(*, actor=None, action, target=None, property=None, changes=None, severity='info', request=None):
    """
    Central entry point every app should call for auditable financial/permission
    events, e.g.:
        log_action(actor=request.user, action='payment.completed', target=payment,
                    property=payment.invoice.lease.unit.property, changes={'amount': str(payment.amount)})
    """
    from .models import AuditLog

    ip_address = None
    if request is not None:
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR')

    return AuditLog.objects.create(
        actor=actor,
        action=action,
        severity=severity,
        target_type=target.__class__.__name__ if target is not None else '',
        target_id=str(getattr(target, 'id', '')) if target is not None else '',
        property=property,
        changes=changes or {},
        ip_address=ip_address,
    )
