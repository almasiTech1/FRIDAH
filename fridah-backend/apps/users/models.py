import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from common.validators import validate_document_extension, MaxFileSizeValidator
from common.private_files import kyc_document_path

phone_validator = RegexValidator(
    regex=r'^\+254[17]\d{8}$',
    message="Phone number must be in the format +2547XXXXXXXX or +2541XXXXXXXX"
)


class User(AbstractUser):
    class Role(models.TextChoices):
        TENANT = 'tenant', 'Tenant'
        LANDLORD = 'landlord', 'Landlord'
        ADMIN = 'admin', 'Admin'
        SERVICE_PROVIDER = 'service_provider', 'Service Provider'
        HOTEL_OWNER = 'hotel_owner', 'Hotel/BnB Owner'

    class KYCStatus(models.TextChoices):
        NOT_SUBMITTED = 'not_submitted', 'Not Submitted'
        PENDING = 'pending', 'Pending Review'
        VERIFIED = 'verified', 'Verified'
        REJECTED = 'rejected', 'Rejected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=13, unique=True, validators=[phone_validator])
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.TENANT)

    national_id = models.CharField(max_length=20, blank=True, null=True)
    kyc_status = models.CharField(max_length=20, choices=KYCStatus.choices, default=KYCStatus.NOT_SUBMITTED)
    kyc_document = models.FileField(
        upload_to=kyc_document_path, blank=True, null=True,
        validators=[validate_document_extension, MaxFileSizeValidator(5)],
    )
    kyc_rejection_reason = models.TextField(blank=True, null=True)
    kyc_reviewed_at = models.DateTimeField(blank=True, null=True)
    kyc_reviewed_by = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='kyc_reviews'
    )

    is_phone_verified = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    # Set on accounts an administrator creates (e.g. an agency's first admin) so the temporary
    # password handed over out-of-band must be replaced at first login.
    must_change_password = models.BooleanField(default=False)

    county = models.CharField(max_length=50, blank=True, null=True)
    town = models.CharField(max_length=100, blank=True, null=True)
    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)

    # Service-provider-specific
    business_name = models.CharField(max_length=150, blank=True, null=True)
    service_category = models.CharField(max_length=100, blank=True, null=True)

    is_active_account = models.BooleanField(default=True)
    fcm_token = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'phone_number', 'role']

    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['phone_number']),
            models.Index(fields=['kyc_status']),
        ]

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"

    @property
    def is_kyc_verified(self):
        return self.kyc_status == self.KYCStatus.VERIFIED


class OTP(models.Model):
    class Purpose(models.TextChoices):
        REGISTRATION = 'registration', 'Registration'
        LOGIN = 'login', 'Login'
        PASSWORD_RESET = 'password_reset', 'Password Reset'
        PHONE_VERIFY = 'phone_verify', 'Phone Verification'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'otps'
        indexes = [models.Index(fields=['user', 'purpose', 'is_used'])]

    def is_expired(self):
        return timezone.now() > self.expires_at

    def is_valid(self, code):
        return not self.is_used and not self.is_expired() and self.code == code


class UserDevice(models.Model):
    """Track devices for push notifications / session security."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='devices')
    device_id = models.CharField(max_length=255)
    fcm_token = models.CharField(max_length=255, blank=True, null=True)
    platform = models.CharField(max_length=20, choices=[('ios', 'iOS'), ('android', 'Android'), ('web', 'Web')])
    last_active = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_devices'
        unique_together = ('user', 'device_id')


class TenantBlacklistEntry(models.Model):
    """
    A landlord's flag against a tenant for non-payment or property damage. Visible to
    other landlords platform-wide when that tenant applies for a unit (shared trust
    network) - the flagging landlord's identity is shown so it can be disputed/verified,
    and a tenant can respond to give their side.
    """
    class Reason(models.TextChoices):
        NON_PAYMENT = 'non_payment', 'Non-payment of rent'
        PROPERTY_DAMAGE = 'property_damage', 'Property damage'
        LEASE_VIOLATION = 'lease_violation', 'Lease violation'
        ABANDONMENT = 'abandonment', 'Abandoned unit without notice'
        OTHER = 'other', 'Other'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        DISPUTED = 'disputed', 'Disputed by tenant'
        REMOVED = 'removed', 'Removed by admin'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blacklist_entries')
    flagged_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blacklist_flags_raised')
    lease = models.ForeignKey(
        'rentals.Lease', on_delete=models.SET_NULL, null=True, blank=True, related_name='blacklist_entries'
    )

    reason = models.CharField(max_length=30, choices=Reason.choices)
    details = models.TextField()
    amount_owed = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    tenant_response = models.TextField(blank=True)
    tenant_responded_at = models.DateTimeField(null=True, blank=True)

    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='blacklist_reviews'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tenant_blacklist_entries'
        indexes = [models.Index(fields=['tenant', 'status'])]

    def __str__(self):
        return f"{self.tenant} flagged by {self.flagged_by} ({self.reason})"
