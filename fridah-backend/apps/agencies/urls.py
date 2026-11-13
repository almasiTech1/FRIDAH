from django.urls import path
from . import views

urlpatterns = [
    path('agencies/', views.AgencyListCreateView.as_view(), name='agency_list'),
    path('agencies/directory/', views.AgencyDirectorySearchView.as_view(), name='agency_directory_search'),
    path('agencies/<uuid:id>/', views.AgencyDetailView.as_view(), name='agency_detail'),
    path('agencies/<uuid:id>/reset-admin-password/', views.AgencyResetAdminPasswordView.as_view(), name='agency_reset_admin_password'),
    path('agencies/memberships/<uuid:membership_id>/reset-password/', views.StaffResetPasswordView.as_view(), name='staff_reset_password'),
    path('agencies/<uuid:id>/status/', views.AgencyStatusView.as_view(), name='agency_status'),
    path('agencies/<uuid:agency_id>/dashboard/', views.AgencyRollupDashboardView.as_view(), name='agency_rollup_dashboard'),
    path('agencies/<uuid:agency_id>/roles/', views.AgencyRoleListCreateView.as_view(), name='agency_role_list'),
    path('agencies/<uuid:agency_id>/members/', views.AgencyMembershipListView.as_view(), name='agency_member_list'),
    path('agencies/<uuid:agency_id>/members/invite/', views.InviteStaffView.as_view(), name='agency_member_invite'),
    path('agencies/<uuid:agency_id>/fee-rules/', views.AgencyFeeRuleListCreateView.as_view(), name='agency_fee_rule_list'),
    path('agencies/<uuid:agency_id>/expenses/', views.AgencyExpenseListCreateView.as_view(), name='agency_expense_list'),
    path('agencies/<uuid:agency_id>/audit-logs/', views.AgencyAuditLogListView.as_view(), name='agency_audit_log_list'),

    path('agency/members/<uuid:membership_id>/accept/', views.AcceptInviteView.as_view(), name='agency_member_accept'),
    path('agency/members/<uuid:membership_id>/suspend/', views.MembershipSuspendView.as_view(), name='agency_member_suspend'),
    path('agency/members/<uuid:membership_id>/remove/', views.MembershipRemoveView.as_view(), name='agency_member_remove'),

    path('agency/property-staff/', views.PropertyStaffAssignmentListCreateView.as_view(), name='property_staff_list'),
    path('agency/property-staff/<uuid:id>/remove/', views.PropertyStaffAssignmentRemoveView.as_view(), name='property_staff_remove'),

    path('agency/agreements/', views.ManagementAgreementListCreateView.as_view(), name='management_agreement_list'),
    path('agency/agreements/<uuid:id>/', views.ManagementAgreementDetailView.as_view(), name='management_agreement_detail'),
    path('agency/agreements/<uuid:id>/sign/', views.SignAgreementView.as_view(), name='management_agreement_sign'),

    path('agency/assignments/', views.PropertyManagementAssignmentListView.as_view(), name='assignment_list'),
    path('agency/assignments/assign/', views.AssignPropertyView.as_view(), name='assignment_assign'),
    path('agency/assignments/assign-listing/', views.AssignListingView.as_view(), name='assignment_assign_listing'),
    path('agency/assignments/<uuid:id>/end/', views.EndAssignmentView.as_view(), name='assignment_end'),

    path('agency/statements/', views.OwnerStatementListView.as_view(), name='statement_list'),
    path('agency/statements/<uuid:id>/', views.OwnerStatementDetailView.as_view(), name='statement_detail'),
    path('agency/statements/generate/', views.GenerateStatementView.as_view(), name='statement_generate'),
    path('agency/statements/generate-listing/', views.GenerateListingStatementView.as_view(), name='statement_generate_listing'),
    path('agency/statements/<uuid:id>/issue/', views.IssueStatementView.as_view(), name='statement_issue'),
    path('agency/statements/<uuid:id>/ai-summary/', views.OwnerStatementAISummaryView.as_view(), name='statement_ai_summary'),

    path('agency/payouts/', views.OwnerPayoutListView.as_view(), name='owner_payout_list'),
    path('agency/statements/<uuid:statement_id>/payout/', views.ExecuteOwnerPayoutView.as_view(), name='owner_payout_execute'),

    path('agency/commissions/', views.AgencyCommissionListView.as_view(), name='agency_commission_list'),

    path('owner/properties/', views.OwnerPropertiesView.as_view(), name='owner_properties'),
    path('owner/listings/', views.OwnerListingsView.as_view(), name='owner_listings'),
    path('owner/portfolio/', views.OwnerPortfolioView.as_view(), name='owner_portfolio'),
    path('my-properties/', views.MyPropertiesView.as_view(), name='my_properties'),
]
