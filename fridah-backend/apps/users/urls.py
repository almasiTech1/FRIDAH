from django.urls import path
from . import views

urlpatterns = [
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/refresh/', views.TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    path('auth/change-password/', views.ChangePasswordView.as_view(), name='change_password'),

    path('me/', views.MeView.as_view(), name='me'),
    path('me/device/', views.RegisterDeviceView.as_view(), name='register_device'),

    path('otp/request/', views.OTPRequestView.as_view(), name='otp_request'),
    path('otp/verify/', views.OTPVerifyView.as_view(), name='otp_verify'),

    path('kyc/submit/', views.KYCSubmitView.as_view(), name='kyc_submit'),
    path('kyc/pending/', views.KYCPendingListView.as_view(), name='kyc_pending'),
    path('kyc/<uuid:user_id>/review/', views.KYCReviewView.as_view(), name='kyc_review'),

    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/<uuid:id>/', views.UserDetailView.as_view(), name='user_detail'),

    path('blacklist/', views.TenantBlacklistListView.as_view(), name='blacklist_list'),
    path('blacklist/flag/', views.TenantBlacklistCreateView.as_view(), name='blacklist_flag'),
    path('blacklist/check/<uuid:tenant_id>/', views.TenantBlacklistCheckView.as_view(), name='blacklist_check'),
    path('blacklist/<uuid:id>/respond/', views.TenantBlacklistRespondView.as_view(), name='blacklist_respond'),
    path('blacklist/<uuid:id>/review/', views.TenantBlacklistReviewView.as_view(), name='blacklist_review'),
]
