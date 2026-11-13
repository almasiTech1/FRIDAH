from django.contrib import admin
from .models import Property, PropertyImage, Unit, UnitImage, SavedProperty, PropertyReview, PropertyDocument


class UnitInline(admin.TabularInline):
    model = Unit
    extra = 0


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('name', 'landlord', 'property_type', 'status', 'town', 'county', 'total_units', 'created_at')
    list_filter = ('status', 'property_type', 'county')
    search_fields = ('name', 'town', 'county', 'estate')
    inlines = [UnitInline]


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ('property', 'unit_number', 'bedrooms', 'rent_amount', 'status')
    list_filter = ('status', 'bedrooms')


admin.site.register(PropertyImage)
admin.site.register(UnitImage)
admin.site.register(SavedProperty)
admin.site.register(PropertyReview)


@admin.register(PropertyDocument)
class PropertyDocumentAdmin(admin.ModelAdmin):
    list_display = ('property', 'document_type', 'version', 'is_current', 'expiry_date', 'created_at')
    list_filter = ('document_type', 'is_current')
