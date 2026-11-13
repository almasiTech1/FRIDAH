from django.contrib import admin
from .models import ServiceCategory, ServiceJob, Quote, ServiceProviderProfile, JobReview


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(ServiceJob)
class ServiceJobAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'posted_by', 'assigned_provider', 'status', 'created_at')
    list_filter = ('status', 'category')


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ('job', 'provider', 'amount', 'status', 'created_at')
    list_filter = ('status',)


admin.site.register(ServiceProviderProfile)
admin.site.register(JobReview)
