import uuid
import hashlib
from django.db import models
from django.conf import settings
from django.utils import timezone


class LeaseSignature(models.Model):
    """Tracks digital e-signature status for a lease."""
    class Status(models.TextChoices):
        PENDING_TENANT = 'pending_tenant', 'Pending Tenant Signature'
        PENDING_LANDLORD = 'pending_landlord', 'Pending Landlord Signature'
        FULLY_SIGNED = 'fully_signed', 'Fully Signed'
        REJECTED = 'rejected', 'Rejected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lease = models.OneToOneField('rentals.Lease', on_delete=models.CASCADE, related_name='signature')
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING_TENANT)

    tenant_signed_at = models.DateTimeField(null=True, blank=True)
    tenant_ip = models.GenericIPAddressField(null=True, blank=True)
    tenant_signature_hash = models.CharField(max_length=64, blank=True)

    landlord_signed_at = models.DateTimeField(null=True, blank=True)
    landlord_ip = models.GenericIPAddressField(null=True, blank=True)
    landlord_signature_hash = models.CharField(max_length=64, blank=True)

    document_hash = models.CharField(max_length=64, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'lease_signatures'

    def generate_signature_hash(self, user_id, timestamp):
        raw = f"{self.lease_id}-{user_id}-{timestamp}-{settings.SECRET_KEY}"
        return hashlib.sha256(raw.encode()).hexdigest()


class LeaseSignatureView:
    """Service layer for lease signing workflow."""

    @staticmethod
    def initiate(lease):
        sig, _ = LeaseSignature.objects.get_or_create(lease=lease)
        sig.status = LeaseSignature.Status.PENDING_TENANT
        sig.save()
        from apps.notifications.services import notify_user
        notify_user(
            lease.tenant,
            title="Lease Ready to Sign",
            message=f"Your lease for {lease.unit.property.name} Unit {lease.unit.unit_number} is ready for your digital signature.",
            notification_type="lease",
            send_sms_too=True,
        )
        return sig

    @staticmethod
    def sign(lease, user, ip_address):
        sig = LeaseSignature.objects.get(lease=lease)
        now = timezone.now()
        hash_val = sig.generate_signature_hash(user.id, now.isoformat())

        if user.id == lease.tenant_id:
            if sig.status != LeaseSignature.Status.PENDING_TENANT:
                raise ValueError("Not awaiting tenant signature.")
            sig.tenant_signed_at = now
            sig.tenant_ip = ip_address
            sig.tenant_signature_hash = hash_val
            sig.status = LeaseSignature.Status.PENDING_LANDLORD
            from apps.notifications.services import notify_user
            notify_user(lease.landlord, title="Tenant Signed Lease", message=f"{lease.tenant.get_full_name()} has signed the lease. Your signature is needed.", notification_type="lease", send_sms_too=True)

        elif user.id == lease.landlord_id:
            if sig.status != LeaseSignature.Status.PENDING_LANDLORD:
                raise ValueError("Not awaiting landlord signature.")
            sig.landlord_signed_at = now
            sig.landlord_ip = ip_address
            sig.landlord_signature_hash = hash_val
            sig.status = LeaseSignature.Status.FULLY_SIGNED
            from apps.notifications.services import notify_user
            notify_user(lease.tenant, title="Lease Fully Signed 🎉", message="Your lease agreement has been signed by both parties. Welcome home!", notification_type="lease", send_sms_too=True)
        else:
            raise PermissionError("Not a party to this lease.")

        sig.save()
        return sig
