from django.urls import path
from . import views

urlpatterns = [
    path('visitors/', views.VisitorListCreateView.as_view(), name='visitor_list'),
    path('visitors/<uuid:id>/cancel/', views.VisitorCancelView.as_view(), name='visitor_cancel'),
    path('visitors/check-in/', views.VisitorQRCheckInView.as_view(), name='visitor_check_in'),
    path('visitors/check-out/', views.VisitorQRCheckOutView.as_view(), name='visitor_check_out'),
]
