from django.urls import path
from . import views

urlpatterns = [
    path('audit/', views.AuditLogListView.as_view(), name='audit_log_list'),
    path('audit/property/<uuid:property_id>/', views.PropertyAuditLogListView.as_view(), name='property_audit_log_list'),
]
