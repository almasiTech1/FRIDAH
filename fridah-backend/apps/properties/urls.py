from django.urls import path
from . import views

urlpatterns = [
    path('properties/', views.PropertyListCreateView.as_view(), name='property_list'),
    path('properties/areas/', views.PropertyAreaSummaryView.as_view(), name='property_areas'),
    path('properties/<uuid:id>/', views.PropertyDetailView.as_view(), name='property_detail'),
    path('properties/<uuid:id>/approval/', views.PropertyApprovalView.as_view(), name='property_approval'),
    path('properties/review-queue/', views.PropertyReviewQueueView.as_view(), name='property_review_queue'),
    path('properties/<uuid:id>/review/', views.PropertyReviewDecisionView.as_view(), name='property_review_decision'),
    path('properties/<uuid:id>/resubmit/', views.PropertyResubmitView.as_view(), name='property_resubmit'),
    path('properties/<uuid:id>/withdraw/', views.PropertyWithdrawView.as_view(), name='property_withdraw'),
    path('properties/<uuid:id>/approvals/', views.PropertyApprovalHistoryView.as_view(), name='property_approval_history'),
    path('properties/<uuid:property_id>/units/', views.UnitListCreateView.as_view(), name='unit_list'),
    path('properties/<uuid:property_id>/reviews/', views.PropertyReviewListCreateView.as_view(), name='property_reviews'),
    path('properties/<uuid:property_id>/documents/', views.PropertyDocumentListCreateView.as_view(), name='property_documents'),
    path('documents/<uuid:id>/', views.PropertyDocumentDetailView.as_view(), name='property_document_detail'),
    path('units/<uuid:id>/', views.UnitDetailView.as_view(), name='unit_detail'),
    path('units/<uuid:id>/cost-of-living/', views.UnitCostOfLivingView.as_view(), name='unit_cost_of_living'),
    path('properties/recommendations/', views.PropertyRecommendationsView.as_view(), name='property_recommendations'),
    path('saved-properties/', views.SavedPropertyListView.as_view(), name='saved_properties'),
    path('saved-properties/<uuid:property_id>/', views.SavedPropertyDeleteView.as_view(), name='saved_property_delete'),
]
