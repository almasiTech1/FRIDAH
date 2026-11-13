from django.urls import path
from . import views

urlpatterns = [
    path('ussd/webhook/', views.UssdWebhookView.as_view(), name='ussd_webhook'),
]
