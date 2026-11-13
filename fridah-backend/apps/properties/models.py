import uuid
from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings
from common.validators import validate_document_extension, MaxFileSizeValidator
from common.private_files import property_document_path
from django.core.validators import MinValueValidator, MaxValueValidator


class Property(models.Model):
    class PropertyType(models.TextChoices):
        APARTMENT = 'apartment', 'Apartment'
        BUNGALOW = 'bungalow', 'Bungalow'
        MAISONETTE = 'maisonette', 'Maisonette'
        TOWNHOUSE = 'townhouse', 'Townhouse'
        COMMERCIAL = 'commercial', 'Commercial'
        HOSTEL = 'hostel', 'Hostel'
        BEDSITTER = 'bedsitter', 'Bedsitter'
        SINGLE_ROOM = 'single_room', 'Single Room'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        PENDING_APPROVAL = 'pending_approval', 'Pending Approval'
        SUSPENDED = 'suspended', 'Suspended'
        ARCHIVED = 'archived', 'Archived'

    class ReviewState(models.TextChoices):
        """Where the property sits in the approval workflow (separate from listing `status`)."""
        AWAITING_LANDLORD = 'awaiting_landlord', 'Awaiting Landlord Approval'
        AWAITING_ADMIN = 'awaiting_admin', 'Awaiting Admin Approval'
        APPROVED = 'approved', 'Approved'
        CHANGES_REQUESTED = 'changes_requested', 'Changes Requested'
        REJECTED = 'rejected', 'Rejected'
        WITHDRAWN = 'withdrawn', 'Withdrawn'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    landlord = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='properties')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    property_type = models.CharField(max_length=20, choices=PropertyType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_APPROVAL)

    county = models.CharField(max_length=50)
    town = models.CharField(max_length=100)
    estate = models.CharField(max_length=150, blank=True)
    address_detail = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, validators=[MinValueValidator(-180), MaxValueValidator(180)])

    total_units = models.PositiveIntegerField(default=1)
    amenities = models.JSONField(default=list, blank=True)  # ["water", "parking", "gym", ...]

    caretaker_name = models.CharField(max_length=150, blank=True)
    caretaker_phone = models.CharField(max_length=13, blank=True)

    # --- Approval workflow (see apps/properties/approvals.py) -------------------------
    # `status == ACTIVE` is the one and only publication flag every tenant-facing query
    # filters on. It may only be reached when review_state == APPROVED; save() enforces it.
    review_state = models.CharField(max_length=20, choices=ReviewState.choices, default=ReviewState.AWAITING_ADMIN)
    submission_version = models.PositiveIntegerField(default=1)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='submitted_properties',
    )
    submitted_by_agency = models.ForeignKey(
        'agencies.Agency', on_delete=models.SET_NULL, null=True, blank=True, related_name='submitted_properties',
    )
    # True when someone other than the owner (an agency) submitted it: the landlord must
    # then approve as well as an administrator before the listing can be published.
    requires_landlord_approval = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'properties'
        verbose_name_plural = 'Properties'
        indexes = [
            models.Index(fields=['county', 'town']),
            models.Index(fields=['status']),
            models.Index(fields=['landlord']),
            models.Index(fields=['review_state']),
        ]

    def __str__(self):
        return f"{self.name} ({self.town}, {self.county})"

    def save(self, *args, **kwargs):
        """
        Last line of defence for the dual-approval rule: no code path (view, task, admin,
        shell) may publish a property that has not completed its approvals.
        """
        if self.status == self.Status.ACTIVE and self.review_state != self.ReviewState.APPROVED:
            trusted_new_row = (
                self._state.adding
                and self.review_state == self.ReviewState.AWAITING_ADMIN
                and not self.requires_landlord_approval
            )
            if trusted_new_row:
                # Rows created straight through the ORM as active (seed data, fixtures,
                # admin onboarding) are trusted; API submissions never take this path
                # because they are created as pending and go through approvals.submit().
                self.review_state = self.ReviewState.APPROVED
            else:
                raise ValidationError(
                    "A property cannot be published until all required approvals are complete."
                )
        super().save(*args, **kwargs)

    @property
    def vacant_units_count(self):
        return self.units.filter(status=Unit.Status.VACANT).count()


class PropertyImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='property_images/')
    caption = models.CharField(max_length=150, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'property_images'
        ordering = ['order']


class Unit(models.Model):
    class Status(models.TextChoices):
        VACANT = 'vacant', 'Vacant'
        OCCUPIED = 'occupied', 'Occupied'
        MAINTENANCE = 'maintenance', 'Under Maintenance'
        RESERVED = 'reserved', 'Reserved'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='units')
    unit_number = models.CharField(max_length=20)
    bedrooms = models.PositiveSmallIntegerField(default=1)
    bathrooms = models.PositiveSmallIntegerField(default=1)
    size_sqm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    rent_amount = models.DecimalField(max_digits=12, decimal_places=2)
    deposit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.VACANT)
    floor = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'units'
        unique_together = ('property', 'unit_number')
        indexes = [models.Index(fields=['status'])]

    def __str__(self):
        return f"{self.property.name} - Unit {self.unit_number}"


class UnitImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='unit_images/')
    is_primary = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'unit_images'
        ordering = ['order']


class SavedProperty(models.Model):
    """Tenant favorites/wishlist."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_properties')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='saved_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'saved_properties'
        unique_together = ('user', 'property')


class PropertyReview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='property_reviews')
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'property_reviews'
        unique_together = ('property', 'reviewer')


class PropertyDocument(models.Model):
    """
    Secure vault for a property's legal documents (title deed, occupation certificate,
    compliance certificates, etc). Only the owning landlord and platform admins can
    access these. Re-uploading a document of the same document_type creates a new
    version rather than overwriting, so the history is preserved.
    """
    class DocumentType(models.TextChoices):
        TITLE_DEED = 'title_deed', 'Title Deed'
        OCCUPATION_CERTIFICATE = 'occupation_certificate', 'Occupation Certificate'
        COMPLIANCE_CERTIFICATE = 'compliance_certificate', 'Compliance Certificate'
        FIRE_SAFETY_CERTIFICATE = 'fire_safety_certificate', 'Fire Safety Certificate'
        LAND_RATES_RECEIPT = 'land_rates_receipt', 'Land Rates Receipt'
        INSURANCE_POLICY = 'insurance_policy', 'Insurance Policy'
        OTHER = 'other', 'Other'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='documents')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_documents')

    document_type = models.CharField(max_length=30, choices=DocumentType.choices)
    title = models.CharField(max_length=200)
    file = models.FileField(
        upload_to=property_document_path,
        validators=[validate_document_extension, MaxFileSizeValidator(10)],
    )
    version = models.PositiveIntegerField(default=1)
    is_current = models.BooleanField(default=True)
    expiry_date = models.DateField(null=True, blank=True)  # e.g. compliance certs that need renewal
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'property_documents'
        ordering = ['-version']
        indexes = [models.Index(fields=['property', 'document_type'])]

    def __str__(self):
        return f"{self.property} - {self.get_document_type_display()} v{self.version}"


class PropertyApproval(models.Model):
    """
    Immutable audit trail for the property approval workflow. One row per event:
    submission, each landlord/admin decision, resubmission, withdrawal, and approval
    invalidation caused by a material edit. Rows are never updated or deleted.
    """
    class Party(models.TextChoices):
        LANDLORD = 'landlord', 'Landlord'
        ADMIN = 'admin', 'Administrator'
        AGENCY = 'agency', 'Agency / Submitter'
        SYSTEM = 'system', 'System'

    class Decision(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        CHANGES_REQUESTED = 'changes_requested', 'Changes Requested'
        RESUBMITTED = 'resubmitted', 'Resubmitted'
        WITHDRAWN = 'withdrawn', 'Withdrawn'
        INVALIDATED = 'invalidated', 'Invalidated by edit'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='approvals')
    party = models.CharField(max_length=10, choices=Party.choices)
    decision = models.CharField(max_length=20, choices=Decision.choices)
    submission_version = models.PositiveIntegerField()
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='property_approval_events',
    )
    comment = models.TextField(blank=True)
    from_state = models.CharField(max_length=20, blank=True)
    to_state = models.CharField(max_length=20, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'property_approvals'
        ordering = ['created_at']
        indexes = [models.Index(fields=['property', 'party', 'submission_version'])]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Approval records are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Approval records are immutable.")

    def __str__(self):
        return f"{self.property_id} {self.party} {self.decision} v{self.submission_version}"
