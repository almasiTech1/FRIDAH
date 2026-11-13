import uuid
from django.db import models
from django.conf import settings


class ServiceCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'service_categories'
        verbose_name_plural = 'Service Categories'

    def __str__(self):
        return self.name


class ServiceJob(models.Model):
    """A job posted (often auto-created from a MaintenanceRequest, or posted directly by a landlord/tenant)."""
    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        QUOTED = 'quoted', 'Quoted'
        ASSIGNED = 'assigned', 'Assigned'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posted_jobs')
    category = models.ForeignKey(ServiceCategory, on_delete=models.PROTECT, related_name='jobs')
    maintenance_request = models.ForeignKey(
        'rentals.MaintenanceRequest', on_delete=models.SET_NULL, null=True, blank=True, related_name='service_jobs'
    )

    title = models.CharField(max_length=200)
    description = models.TextField()
    county = models.CharField(max_length=50)
    town = models.CharField(max_length=100)
    budget_estimate = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)

    assigned_provider = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_jobs'
    )
    scheduled_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'service_jobs'
        indexes = [models.Index(fields=['status']), models.Index(fields=['county', 'town'])]

    def __str__(self):
        return self.title


class Quote(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        REJECTED = 'rejected', 'Rejected'
        WITHDRAWN = 'withdrawn', 'Withdrawn'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(ServiceJob, on_delete=models.CASCADE, related_name='quotes')
    provider = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quotes')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    message = models.TextField(blank=True)
    estimated_days = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'quotes'
        unique_together = ('job', 'provider')


class ServiceProviderProfile(models.Model):
    """Extended profile for service providers: ratings, categories, portfolio."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='provider_profile')
    categories = models.ManyToManyField(ServiceCategory, related_name='providers', blank=True)
    bio = models.TextField(blank=True)
    years_experience = models.PositiveSmallIntegerField(default=0)
    is_available = models.BooleanField(default=True)
    service_counties = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'service_provider_profiles'

    @property
    def average_rating(self):
        reviews = JobReview.objects.filter(job__assigned_provider=self.user)
        if not reviews:
            return None
        return round(sum(r.rating for r in reviews) / reviews.count(), 1)


class JobReview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.OneToOneField(ServiceJob, on_delete=models.CASCADE, related_name='review')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='job_reviews')
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'job_reviews'
