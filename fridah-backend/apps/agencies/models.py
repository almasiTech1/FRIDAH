import builtins
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from common.validators import validate_document_extension, MaxFileSizeValidator
from common.private_files import agreement_path, statement_path, expense_receipt_path


class Agency(models.Model):
    """
    A property-management company. An agency does NOT own properties — it only ever
    receives management rights over properties belonging to one or many landlords via
    PropertyManagementAssignment. This separation of ownership from management is the
    central structural rule of FRIDAH's agency model.
    """
    class Status(models.TextChoices):
        PENDING_APPROVAL = 'pending_approval', 'Pending Approval'
        ACTIVE = 'active', 'Active'
        SUSPENDED = 'suspended', 'Suspended'
        ARCHIVED = 'archived', 'Archived'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    registration_number = models.CharField(max_length=100, blank=True)
    kra_pin = models.CharField(max_length=30, blank=True)

    # The user who created/administers the agency account. Day-to-day staff access is
    # controlled through AgencyMembership, not through this field.
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='agencies_created'
    )

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_APPROVAL)
    logo = models.ImageField(upload_to='agency_logos/', blank=True, null=True)
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=13, blank=True)
    county = models.CharField(max_length=50, blank=True)
    town = models.CharField(max_length=100, blank=True)
    address_detail = models.CharField(max_length=255, blank=True)

    # Default fee rule used when a ManagementAgreement doesn't specify its own.
    default_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=5.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'agencies'
        verbose_name_plural = 'Agencies'
        indexes = [models.Index(fields=['status'])]

    def __str__(self):
        return self.name

    @property
    def managed_properties_count(self):
        return self.management_assignments.filter(status=PropertyManagementAssignment.Status.ACTIVE).count()

    @property
    def owners_count(self):
        return (
            self.management_assignments.filter(status=PropertyManagementAssignment.Status.ACTIVE)
            .values('property__landlord').distinct().count()
        )


class AgencyRole(models.Model):
    """
    A role within an agency (Agency Admin, Property Manager, Caretaker, Finance
    Officer, Leasing Agent, or an agency-defined custom role) carrying a set of
    permission codes. Agencies get the five standard roles seeded automatically;
    additional custom roles can be created per agency.
    """
    class RoleType(models.TextChoices):
        AGENCY_ADMIN = 'agency_admin', 'Agency Admin'
        PROPERTY_MANAGER = 'property_manager', 'Property Manager'
        CARETAKER = 'caretaker', 'Caretaker'
        FINANCE_OFFICER = 'finance_officer', 'Finance Officer'
        LEASING_AGENT = 'leasing_agent', 'Leasing Agent'
        CUSTOM = 'custom', 'Custom'

    # Default permission sets for the five standard roles. Custom roles start blank.
    DEFAULT_PERMISSIONS = {
        RoleType.AGENCY_ADMIN: [
            'agency.manage_staff', 'agency.manage_assignments', 'agency.manage_settings',
            'property.view', 'property.manage', 'finance.view', 'finance.manage',
            'maintenance.view', 'maintenance.manage', 'chat.participate', 'tenants.view',
            'tenants.manage', 'statements.view', 'statements.issue', 'payouts.execute',
        ],
        RoleType.PROPERTY_MANAGER: [
            'property.view', 'property.manage', 'maintenance.view', 'maintenance.manage',
            'chat.participate', 'tenants.view', 'tenants.manage', 'finance.view',
        ],
        RoleType.CARETAKER: [
            'property.view', 'maintenance.view', 'maintenance.manage', 'chat.participate',
        ],
        RoleType.FINANCE_OFFICER: [
            'finance.view', 'finance.manage', 'statements.view', 'statements.issue',
            'payouts.execute', 'chat.participate', 'property.view',
        ],
        RoleType.LEASING_AGENT: [
            'property.view', 'tenants.view', 'chat.participate', 'listings.manage',
        ],
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='roles')
    name = models.CharField(max_length=100)
    role_type = models.CharField(max_length=20, choices=RoleType.choices, default=RoleType.CUSTOM)
    permissions = models.JSONField(default=list, blank=True)  # list of permission codes
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'agency_roles'
        unique_together = ('agency', 'name')

    def __str__(self):
        return f"{self.agency.name} - {self.name}"

    def has_permission(self, code):
        return code in (self.permissions or [])

    @classmethod
    def seed_defaults(cls, agency):
        """Create the five standard roles for a newly-created agency."""
        created = []
        for role_type in [
            cls.RoleType.AGENCY_ADMIN, cls.RoleType.PROPERTY_MANAGER, cls.RoleType.CARETAKER,
            cls.RoleType.FINANCE_OFFICER, cls.RoleType.LEASING_AGENT,
        ]:
            role, _ = cls.objects.get_or_create(
                agency=agency, name=role_type.label,
                defaults={'role_type': role_type, 'permissions': cls.DEFAULT_PERMISSIONS.get(role_type, [])},
            )
            created.append(role)
        return created


class AgencyMembership(models.Model):
    """A staff member's membership of an agency, carrying their role/permissions."""
    class Status(models.TextChoices):
        INVITED = 'invited', 'Invited'
        ACTIVE = 'active', 'Active'
        SUSPENDED = 'suspended', 'Suspended'
        REMOVED = 'removed', 'Removed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='agency_memberships')
    role = models.ForeignKey(AgencyRole, on_delete=models.PROTECT, related_name='memberships')

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INVITED)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='agency_invites_sent'
    )
    joined_at = models.DateTimeField(null=True, blank=True)
    removed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'agency_memberships'
        unique_together = ('agency', 'user')
        indexes = [models.Index(fields=['agency', 'status'])]

    def __str__(self):
        return f"{self.user} @ {self.agency} ({self.role.role_type})"

    def has_permission(self, code):
        return self.status == self.Status.ACTIVE and self.role.has_permission(code)


class PropertyManagementAssignment(models.Model):
    """
    The historical record of which agency managed a given property, for what period,
    under what fee/payout terms. This is deliberately a time-stamped, append-only-style
    history rather than a single `property.agency` field, so the system can answer who
    managed a property during any previous period. Exactly one assignment per property
    may be ACTIVE at a time.
    """
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        ENDED = 'ended', 'Ended'
        TERMINATED = 'terminated', 'Terminated Early'

    class PayoutRule(models.TextChoices):
        OWNER_DIRECT = 'owner_direct', 'Owner Direct'
        AGENCY_COLLECTS = 'agency_collects', 'Agency Collects, Then Remits'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(
        'properties.Property', on_delete=models.CASCADE, null=True, blank=True, related_name='management_assignments'
    )
    listing = models.ForeignKey(
        'bookings.Listing', on_delete=models.CASCADE, null=True, blank=True, related_name='management_assignments'
    )
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='management_assignments')
    agreement = models.ForeignKey(
        'ManagementAgreement', on_delete=models.SET_NULL, null=True, blank=True, related_name='assignments'
    )
    fee_rule = models.ForeignKey(
        'AgencyFeeRule', on_delete=models.SET_NULL, null=True, blank=True, related_name='assignments'
    )

    management_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=5.0)
    payout_rule = models.CharField(max_length=20, choices=PayoutRule.choices, default=PayoutRule.OWNER_DIRECT)

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='management_assignments_approved'
    )
    ended_reason = models.TextField(blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'property_management_assignments'
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['property', 'status']),
            models.Index(fields=['listing', 'status']),
            models.Index(fields=['agency', 'status']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(property__isnull=False, listing__isnull=True) |
                    models.Q(property__isnull=True, listing__isnull=False)
                ),
                name='assignment_exactly_one_of_property_or_listing',
            ),
        ]

    def __str__(self):
        return f"{self.property or self.listing} managed by {self.agency} ({self.status})"

    def end(self, reason='', by_user=None):
        self.status = self.Status.ENDED
        self.end_date = self.end_date or timezone.now().date()
        self.ended_reason = reason
        self.ended_at = timezone.now()
        self.save(update_fields=['status', 'end_date', 'ended_reason', 'ended_at'])

    @classmethod
    def active_for_property(cls, property):
        return cls.objects.filter(property=property, status=cls.Status.ACTIVE).first()

    @classmethod
    def active_for_listing(cls, listing):
        return cls.objects.filter(listing=listing, status=cls.Status.ACTIVE).first()


class PropertyStaffAssignment(models.Model):
    """Restricts a specific agency staff member's operational access to specific properties."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey('properties.Property', on_delete=models.CASCADE, related_name='staff_assignments')
    membership = models.ForeignKey(AgencyMembership, on_delete=models.CASCADE, related_name='property_assignments')
    is_active = models.BooleanField(default=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    removed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'property_staff_assignments'
        unique_together = ('property', 'membership')
        indexes = [models.Index(fields=['property', 'is_active'])]

    def __str__(self):
        return f"{self.membership.user} -> {self.property}"


class AgencyFeeRule(models.Model):
    """A reusable fee schedule an agency can attach to management agreements/assignments."""
    class FeeType(models.TextChoices):
        PERCENTAGE = 'percentage', 'Percentage of Collections'
        FLAT = 'flat', 'Flat Fee per Period'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='fee_rules')
    name = models.CharField(max_length=100)
    fee_type = models.CharField(max_length=20, choices=FeeType.choices, default=FeeType.PERCENTAGE)
    fee_value = models.DecimalField(max_digits=10, decimal_places=2)  # percent (0-100) or flat KES amount
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'agency_fee_rules'
        unique_together = ('agency', 'name')

    def __str__(self):
        return f"{self.agency.name} - {self.name}"

    def compute_fee(self, gross_amount):
        if self.fee_type == self.FeeType.PERCENTAGE:
            return (gross_amount * self.fee_value / 100).quantize(gross_amount)
        return min(self.fee_value, gross_amount)


class ManagementAgreement(models.Model):
    """
    The formal agreement authorizing an agency to manage a property on behalf of its
    owner. A PropertyManagementAssignment is the operational/historical record; this
    is the underlying signed contract that assignment is derived from/tied to.
    """
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PENDING_SIGNATURES = 'pending_signatures', 'Pending Signatures'
        ACTIVE = 'active', 'Active'
        ENDED = 'ended', 'Ended'
        TERMINATED = 'terminated', 'Terminated'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey('properties.Property', on_delete=models.CASCADE, related_name='management_agreements')
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='management_agreements')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='management_agreements')

    fee_rule = models.ForeignKey(AgencyFeeRule, on_delete=models.SET_NULL, null=True, blank=True, related_name='agreements')
    management_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=5.0)
    payout_rule = models.CharField(
        max_length=20, choices=PropertyManagementAssignment.PayoutRule.choices,
        default=PropertyManagementAssignment.PayoutRule.OWNER_DIRECT
    )

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    document = models.FileField(
        upload_to=agreement_path, blank=True, null=True,
        validators=[validate_document_extension, MaxFileSizeValidator(15)],
    )
    terms = models.JSONField(default=dict, blank=True)

    signed_by_owner_at = models.DateTimeField(null=True, blank=True)
    signed_by_agency_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'management_agreements'
        indexes = [models.Index(fields=['status'])]

    def __str__(self):
        return f"Agreement: {self.property} - {self.agency}"

    def _is_fully_signed(self):
        return bool(self.signed_by_owner_at and self.signed_by_agency_at)

    # NOTE: can't use the `@property` decorator here — this model has a field
    # literally named `property` (the managed Property FK), which shadows the
    # builtin `property` name within the class body. Build the property object
    # explicitly using the builtin captured at module import time instead.
    is_fully_signed = builtins.property(_is_fully_signed)


class OwnerStatement(models.Model):
    """
    A periodic (typically monthly) financial statement for a property owner, showing
    gross rent collected, vacancy/arrears, agency commission, approved expenses, other
    deductions and the resulting net payable amount. Generated per property per period.
    """
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        ISSUED = 'issued', 'Issued'
        PAID = 'paid', 'Paid'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(
        'properties.Property', on_delete=models.CASCADE, null=True, blank=True, related_name='owner_statements'
    )
    listing = models.ForeignKey(
        'bookings.Listing', on_delete=models.CASCADE, null=True, blank=True, related_name='owner_statements'
    )
    agency = models.ForeignKey(Agency, on_delete=models.SET_NULL, null=True, blank=True, related_name='owner_statements')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owner_statements')

    period_start = models.DateField()
    period_end = models.DateField()

    gross_rent_collected = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    vacancy_loss = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    arrears = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    agency_commission = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    approved_expenses = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    net_payable = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    pdf_statement = models.FileField(
        upload_to=statement_path, blank=True, null=True,
        validators=[validate_document_extension, MaxFileSizeValidator(10)],
    )

    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='statements_generated'
    )
    issued_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'owner_statements'
        ordering = ['-period_start']
        indexes = [models.Index(fields=['owner', 'status'])]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(property__isnull=False, listing__isnull=True) |
                    models.Q(property__isnull=True, listing__isnull=False)
                ),
                name='statement_exactly_one_of_property_or_listing',
            ),
            models.UniqueConstraint(
                fields=['property', 'period_start', 'period_end'], name='unique_property_statement_period',
            ),
            models.UniqueConstraint(
                fields=['listing', 'period_start', 'period_end'], name='unique_listing_statement_period',
            ),
        ]

    def __str__(self):
        return f"Statement {self.property or self.listing} {self.period_start}–{self.period_end}"

    def recompute_net(self):
        self.net_payable = (
            self.gross_rent_collected - self.agency_commission - self.approved_expenses - self.other_deductions
        )
        return self.net_payable


class OwnerPayout(models.Model):
    """The actual disbursement of an OwnerStatement's net payable amount to the owner."""
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    statement = models.ForeignKey(OwnerStatement, on_delete=models.CASCADE, related_name='payouts')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owner_payouts')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(max_length=20, default='mpesa_b2c')
    phone_number = models.CharField(max_length=13, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    reference = models.CharField(max_length=50, unique=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    raw_callback = models.JSONField(default=dict, blank=True)

    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='payouts_initiated'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'owner_payouts'
        indexes = [models.Index(fields=['status'])]

    def __str__(self):
        return f"{self.reference} - KES {self.amount} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"OPO-{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)


class AgencyCommission(models.Model):
    """The agency's earned commission record for a property/period, distinct from the owner payout."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='commissions')
    property = models.ForeignKey(
        'properties.Property', on_delete=models.CASCADE, null=True, blank=True, related_name='agency_commissions'
    )
    listing = models.ForeignKey(
        'bookings.Listing', on_delete=models.CASCADE, null=True, blank=True, related_name='agency_commissions'
    )
    assignment = models.ForeignKey(
        PropertyManagementAssignment, on_delete=models.SET_NULL, null=True, blank=True, related_name='commissions'
    )
    statement = models.ForeignKey(
        OwnerStatement, on_delete=models.SET_NULL, null=True, blank=True, related_name='commission_records'
    )

    period_start = models.DateField()
    period_end = models.DateField()
    gross_amount = models.DecimalField(max_digits=14, decimal_places=2)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=14, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'agency_commissions'
        indexes = [models.Index(fields=['agency', 'period_start'])]

    def __str__(self):
        return f"{self.agency} commission {self.property or self.listing} {self.period_start}"


class AgencyExpense(models.Model):
    """
    A property expense (maintenance, compliance, utilities, etc.) incurred and recorded
    by an agency, optionally deductible from the owner's net payable on their statement.
    """
    class Category(models.TextChoices):
        MAINTENANCE = 'maintenance', 'Maintenance'
        UTILITIES = 'utilities', 'Utilities'
        COMPLIANCE = 'compliance', 'Compliance / Certification'
        SECURITY = 'security', 'Security'
        CLEANING = 'cleaning', 'Cleaning'
        OTHER = 'other', 'Other'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='expenses')
    property = models.ForeignKey('properties.Property', on_delete=models.CASCADE, related_name='agency_expenses')
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    receipt = models.FileField(
        upload_to=expense_receipt_path, blank=True, null=True,
        validators=[validate_document_extension, MaxFileSizeValidator(5)],
    )
    is_deductible_from_owner = models.BooleanField(default=True)

    incurred_on = models.DateField()
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses_recorded'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='expenses_approved'
    )
    statement = models.ForeignKey(
        OwnerStatement, on_delete=models.SET_NULL, null=True, blank=True, related_name='expense_records'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'agency_expenses'
        indexes = [models.Index(fields=['property', 'incurred_on'])]

    def __str__(self):
        return f"{self.property} - {self.description} (KES {self.amount})"


class AgencyAuditLog(models.Model):
    """Append-only log of agency-scoped financial and permission changes (staff, assignments, fees, payouts)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='audit_logs')
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='agency_audit_actions'
    )
    action = models.CharField(max_length=100)  # e.g. 'staff.invited', 'assignment.created', 'payout.executed'
    target_type = models.CharField(max_length=100, blank=True)  # model name
    target_id = models.CharField(max_length=64, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'agency_audit_logs'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['agency', 'created_at'])]

    def __str__(self):
        return f"[{self.agency}] {self.action} by {self.actor}"
