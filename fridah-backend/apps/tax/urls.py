from django.urls import path
from . import views

urlpatterns = [
    path('tax/types/', views.TaxTypeListCreateView.as_view(), name='tax_types'),
    path('tax/rules/', views.TaxRuleListCreateView.as_view(), name='tax_rules'),
    path('tax/records/', views.TaxRecordListView.as_view(), name='tax_records'),
    path('tax/records/estimate/', views.TaxEstimateView.as_view(), name='tax_estimate'),
    path('tax/records/<uuid:id>/', views.TaxRecordDetailView.as_view(), name='tax_record_detail'),
    path('tax/records/<uuid:id>/adjust/', views.TaxRecordAdjustView.as_view(), name='tax_record_adjust'),
    path('tax/records/<uuid:id>/adjustments/', views.TaxRecordAdjustmentsView.as_view(), name='tax_record_adjustments'),
    path('tax/summary/', views.TaxSummaryView.as_view(), name='tax_summary'),
    path('tax/export/', views.TaxExportView.as_view(), name='tax_export'),
]
