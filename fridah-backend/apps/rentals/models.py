import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from common.validators import validate_document_extension, MaxFileSizeValidator
from common.private_files import invoice_receipt_path, maintenance_image_path, utility_photo_path


class Lease(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACTIVE = 'active', 'Active'
        TERMINATED = 'terminated', 'Terminated'
        EXPIRED = 'expired', 'Expired'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='leases')
    unit = models.ForeignKey('properties.Unit', on_delete=models.CASCADE, related_name='leases')
    landlord = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='landlord_leases')

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    rent_amount = models.DecimalField(max_digits=12, decimal_places=2)
    deposit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deposit_paid = models.BooleanField(default=False)
    rent_due_day = models.PositiveSmallIntegerField(default=5)  # day of month

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    terminated_at = models.DateTimeField(null=True, blank=True)
    termination_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'leases'
        indexes = [models.Index(fields=['status']), models.Index(fields=['tenant']), models.Index(fields=['landlord'])]

    def __str__(self):
        return f"Lease: {self.tenant} @ {self.unit}"


class RentalApplication(models.Model):
    """
    A tenant's request to rent a specific vacant unit. This is the piece that was
    entirely missing: property/unit listings were browsable and looked clickable,
    but there was no way for a tenant to actually act on one - only a landlord or
    agent could create a Lease directly, with no tenant-initiated path into it.

    Approving an application creates the actual Lease (a landlord still sets the
    final rent/deposit/dates at approval time - the application itself is a
    request to be considered, not a binding offer) and marks the unit occupied,
    automatically rejecting any other still-pending applications for that unit.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        WITHDRAWN = 'withdrawn', 'Withdrawn'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.ForeignKey('properties.Unit', on_delete=models.CASCADE, related_name='rental_applications')
    tenant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rental_applications')
    message = models.TextField(blank=True)
    preferred_move_in_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    resulting_lease = models.ForeignKey(Lease, on_delete=models.SET_NULL, null=True, blank=True, related_name='application')
    rejection_reason = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_applications',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rental_applications'
        indexes = [models.Index(fields=['status']), models.Index(fields=['unit']), models.Index(fields=['tenant'])]

    def __str__(self):
        return f"Application: {self.tenant} -> {self.unit} ({self.status})"


class Invoice(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        PARTIALLY_PAID = 'partially_paid', 'Partially Paid'
        OVERDUE = 'overdue', 'Overdue'
        CANCELLED = 'cancelled', 'Cancelled'

    class InvoiceType(models.TextChoices):
        RENT = 'rent', 'Rent'
        DEPOSIT = 'deposit', 'Deposit'
        PENALTY = 'penalty', 'Late Penalty'
        UTILITY = 'utility', 'Utility'
        AMENITY = 'amenity', 'Amenity / Service Charge'
        OTHER = 'other', 'Other'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_number = models.CharField(max_length=30, unique=True)
    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name='invoices')
    tenant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='invoices')
    invoice_type = models.CharField(max_length=20, choices=InvoiceType.choices, default=InvoiceType.RENT)

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    period_start = models.DateField()
    period_end = models.DateField()
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    pdf_receipt = models.FileField(
        upload_to=invoice_receipt_path, blank=True, null=True,
        validators=[validate_document_extension, MaxFileSizeValidator(10)],
    )

    # Itemised amenity billing + audited waivers (apps/rentals/amenities.py)
    amenity_charge = models.ForeignKey(
        'rentals.AmenityCharge', on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices',
    )
    waived_at = models.DateTimeField(null=True, blank=True)
    waived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
    )
    waiver_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'invoices'
        indexes = [models.Index(fields=['status']), models.Index(fields=['due_date'])]

    def __str__(self):
        return self.invoice_number

    @property
    def balance(self):
        return self.amount - self.amount_paid

    @property
    def is_overdue(self):
        return self.status not in (self.Status.PAID, self.Status.CANCELLED) and timezone.now().date() > self.due_date

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = f"INV-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)


class MaintenanceRequest(models.Model):
    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'

    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        ASSIGNED = 'assigned', 'Assigned'
        IN_PROGRESS = 'in_progress', 'In Progress'
        RESOLVED = 'resolved', 'Resolved'
        CLOSED = 'closed', 'Closed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='maintenance_requests')
    unit = models.ForeignKey('properties.Unit', on_delete=models.CASCADE, related_name='maintenance_requests')
    category = models.CharField(max_length=100)  # plumbing, electrical, etc
    title = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)

    assigned_provider = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_maintenance_requests'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'maintenance_requests'
        indexes = [models.Index(fields=['status']), models.Index(fields=['priority'])]


class MaintenanceImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(MaintenanceRequest, on_delete=models.CASCADE, related_name='images')
    # ImageField already validates via Pillow that this is a genuine image (unlike
    # the plain FileFields elsewhere that needed common.validators added to them) -
    # only a size cap is needed here to prevent oversized uploads.
    image = models.ImageField(upload_to=maintenance_image_path, validators=[MaxFileSizeValidator(8)])

    class Meta:
        db_table = 'maintenance_images'


class LeaseRenewal(models.Model):
    """
    Tracks the renewal offer for a lease as it approaches its end_date. A Celery Beat
    task creates/updates one of these at 60 and 30 days out and notifies the tenant;
    the tenant then accepts or declines with a single tap in the app.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending tenant response'
        ACCEPTED = 'accepted', 'Accepted'
        DECLINED = 'declined', 'Declined'
        EXPIRED = 'expired', 'Expired - lease ended with no response'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lease = models.OneToOneField(Lease, on_delete=models.CASCADE, related_name='renewal')

    # What the tenant is being offered - defaults to a like-for-like extension, but the
    # landlord can adjust (e.g. apply the annual rent escalation) before it's sent.
    proposed_start_date = models.DateField()
    proposed_end_date = models.DateField()
    proposed_rent_amount = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    notified_60_day_at = models.DateTimeField(null=True, blank=True)
    notified_30_day_at = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    decline_reason = models.TextField(blank=True)

    # Set once the tenant accepts and a fresh Lease row is created for the new term.
    renewed_lease = models.ForeignKey(
        Lease, on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'lease_renewals'
        indexes = [models.Index(fields=['status'])]

    def __str__(self):
        return f"Renewal for {self.lease} ({self.status})"


class UtilityAccount(models.Model):
    """A tracked utility (water/electricity/garbage/internet) for a specific unit."""
    class UtilityType(models.TextChoices):
        WATER = 'water', 'Water'
        ELECTRICITY = 'electricity', 'Electricity'
        GARBAGE = 'garbage', 'Garbage Collection'
        INTERNET = 'internet', 'Internet'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.ForeignKey('properties.Unit', on_delete=models.CASCADE, related_name='utility_accounts')
    utility_type = models.CharField(max_length=20, choices=UtilityType.choices)
    provider_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=100, blank=True)
    # Flat-fee utilities (garbage, often internet) skip metering entirely; metered ones
    # (water, electricity) bill usage x rate from readings instead.
    is_metered = models.BooleanField(default=True)
    rate_per_unit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    flat_monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'utility_accounts'
        unique_together = ('unit', 'utility_type')

    def __str__(self):
        return f"{self.unit} - {self.get_utility_type_display()}"


class UtilityMeterReading(models.Model):
    """A single meter reading for a metered utility account. Usage is derived from the previous reading."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utility_account = models.ForeignKey(UtilityAccount, on_delete=models.CASCADE, related_name='readings')
    reading_value = models.DecimalField(max_digits=12, decimal_places=2)
    reading_date = models.DateField()
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    photo = models.ImageField(upload_to=utility_photo_path, blank=True, null=True)
    generated_invoice = models.ForeignKey(
        Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='utility_reading'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'utility_meter_readings'
        ordering = ['-reading_date']
        indexes = [models.Index(fields=['utility_account', 'reading_date'])]

    def __str__(self):
        return f"{self.utility_account} - {self.reading_value} on {self.reading_date}"


class AmenityCharge(models.Model):
    """
    A recurring (monthly) or one-off charge for a shared amenity/service on a property -
    e.g. borehole water, security, garbage, parking, gym. Billed to tenants with an active
    lease as itemised invoices that flow through the normal M-Pesa payment and receipt path.
    """
    class Frequency(models.TextChoices):
        MONTHLY = 'monthly', 'Monthly'
        ONE_OFF = 'one_off', 'One-off'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey('properties.Property', on_delete=models.CASCADE, related_name='amenity_charges')
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    frequency = models.CharField(max_length=10, choices=Frequency.choices, default=Frequency.MONTHLY)
    applies_to_all_units = models.BooleanField(default=True)
    units = models.ManyToManyField('properties.Unit', blank=True, related_name='amenity_charges')
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'amenity_charges'
        ordering = ['property', 'name']

    def __str__(self):
        return f'{self.name} @ {self.property_id}'


class AmenityExemption(models.Model):
    """A lease exempt from an amenity charge, with the reason and who granted it."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    charge = models.ForeignKey(AmenityCharge, on_delete=models.CASCADE, related_name='exemptions')
    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name='amenity_exemptions')
    reason = models.TextField()
    granted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'amenity_exemptions'
        unique_together = ('charge', 'lease')
