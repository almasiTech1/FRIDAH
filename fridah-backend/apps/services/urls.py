from django.urls import path
from . import views

urlpatterns = [
    path('service-categories/', views.ServiceCategoryListView.as_view(), name='service_category_list'),

    path('jobs/', views.ServiceJobListCreateView.as_view(), name='job_list'),
    path('jobs/<uuid:id>/', views.ServiceJobDetailView.as_view(), name='job_detail'),
    path('jobs/<uuid:id>/start/', views.JobStartView.as_view(), name='job_start'),
    path('jobs/<uuid:id>/complete/', views.JobCompleteView.as_view(), name='job_complete'),

    path('quotes/', views.QuoteCreateView.as_view(), name='quote_create'),
    path('quotes/<uuid:id>/accept/', views.QuoteAcceptView.as_view(), name='quote_accept'),

    path('job-reviews/', views.JobReviewCreateView.as_view(), name='job_review_create'),

    path('provider-profile/', views.ServiceProviderProfileView.as_view(), name='provider_profile'),
    path('providers/', views.ServiceProviderListView.as_view(), name='provider_list'),
    path('public/providers/', views.PublicServiceProviderListView.as_view(), name='public_provider_list'),
]
