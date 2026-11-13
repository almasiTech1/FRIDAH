from django.urls import path
from . import views

urlpatterns = [
    path('fraud-flags/', views.FraudFlagListView.as_view(), name='fraud_flag_list'),
    path('fraud-flags/<uuid:id>/review/', views.FraudFlagReviewView.as_view(), name='fraud_flag_review'),
    path('fraud-flags/run-detection/', views.RunFraudDetectionView.as_view(), name='fraud_run_detection'),
]
