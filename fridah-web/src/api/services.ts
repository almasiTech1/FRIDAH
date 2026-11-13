import api, { createCrudService } from './client'
import type { MaintenanceRequest,
  User, Property, Unit, Lease,
  Listing, RoomType, Booking, ServiceJob, Quote,
  TenantDashboard, LandlordDashboard, AdminDashboard,
  ServiceProviderDashboard, HotelDashboard, PayoutRule
} from '@/types'

// ---------- Auth ----------
export const authApi = {
  register: (data: Record<string, unknown>) => api.post('/auth/register/', data),
  login: (email: string, password: string) => api.post('/auth/login/', { email, password }),
  logout: (refresh: string) => api.post('/auth/logout/', { refresh }),
  me: () => api.get<{ success: boolean; data: User }>('/me/'),
  updateProfile: (data: Partial<User>) => api.patch('/me/', data),
  changePassword: (old_password: string, new_password: string) =>
    api.post('/auth/change-password/', { old_password, new_password }),
  requestOtp: (purpose: string) => api.post('/otp/request/', { purpose }),
  verifyOtp: (code: string, purpose: string) => api.post('/otp/verify/', { code, purpose }),
  submitKyc: (formData: FormData) => api.post('/kyc/submit/', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  registerDevice: (device_id: string, fcm_token: string, platform: string) =>
    api.post('/me/device/', { device_id, fcm_token, platform }),
}

// ---------- Properties ----------
export const propertiesApi = {
  ...createCrudService<Property>('/properties/'),
  approve: (id: string, action: string) => api.post(`/properties/${id}/approval/`, { action }),
  units: (propertyId: string) => api.get<any>(`/properties/${propertyId}/units/`),
  createUnit: (propertyId: string, data: Partial<Unit>) => api.post(`/properties/${propertyId}/units/`, data),
  updateUnit: (id: string, data: Partial<Unit>) => api.patch(`/units/${id}/`, data),
  deleteUnit: (id: string) => api.delete(`/units/${id}/`),
  savedList: () => api.get('/saved-properties/'),
  save: (propertyId: string) => api.post('/saved-properties/', { property: propertyId }),
  areas: () => api.get('/properties/areas/'),
  unsave: (propertyId: string) => api.delete(`/saved-properties/${propertyId}/`),
  reviews: (propertyId: string) => api.get(`/properties/${propertyId}/reviews/`),
  addReview: (propertyId: string, data: { rating: number; comment: string }) =>
    api.post(`/properties/${propertyId}/reviews/`, data),
  costOfLiving: (unitId: string) => api.get(`/units/${unitId}/cost-of-living/`),
  recommendations: (limit?: number) => api.get('/properties/recommendations/', { params: { limit } }),
}

// ---------- Rentals ----------
export const rentalsApi = {
  leases: (params?: Record<string, unknown>) => api.get('/leases/', { params }),
  getLease: (id: string) => api.get(`/leases/${id}/`),
  createLease: (data: Partial<Lease>) => api.post('/leases/', data),
  activateLease: (id: string) => api.post(`/leases/${id}/activate/`),
  terminateLease: (id: string, reason: string) => api.post(`/leases/${id}/terminate/`, { reason }),

  invoices: (params?: Record<string, unknown>) => api.get('/invoices/', { params }),
  getInvoice: (id: string) => api.get(`/invoices/${id}/`),

  maintenanceList: (params?: Record<string, unknown>) => api.get('/maintenance/', { params }),
  getMaintenance: (id: string) => api.get(`/maintenance/${id}/`),
  createMaintenance: (data: Partial<MaintenanceRequest>) => api.post('/maintenance/', data),
  assignMaintenance: (id: string, provider_id: string) => api.post(`/maintenance/${id}/assign/`, { provider_id }),
  resolveMaintenance: (id: string, notes: string) => api.post(`/maintenance/${id}/resolve/`, { notes }),

  applyToUnit: (unitId: string, data: { message?: string; preferred_move_in_date?: string }) =>
    api.post(`/units/${unitId}/apply/`, data),
  applications: (params?: Record<string, unknown>) => api.get('/rental-applications/', { params }),
  approveApplication: (id: string, data: Record<string, unknown>) => api.post(`/rental-applications/${id}/approve/`, data),
  rejectApplication: (id: string, reason?: string) => api.post(`/rental-applications/${id}/reject/`, { reason }),
  withdrawApplication: (id: string) => api.post(`/rental-applications/${id}/withdraw/`),
}

// ---------- Bookings ----------
export const bookingsApi = {
  listings: (params?: Record<string, unknown>) => api.get('/listings/', { params }),
  getListing: (id: string) => api.get(`/listings/${id}/`),
  createListing: (data: Partial<Listing>) => api.post('/listings/', data),
  updateListing: (id: string, data: Partial<Listing>) => api.patch(`/listings/${id}/`, data),
  approveListing: (id: string, action: string) => api.post(`/listings/${id}/approval/`, { action }),

  roomTypes: (listingId: string) => api.get(`/listings/${listingId}/room-types/`),
  createRoomType: (listingId: string, data: Partial<RoomType>) => api.post(`/listings/${listingId}/room-types/`, data),
  checkAvailability: (roomTypeId: string, check_in: string, check_out: string) =>
    api.get(`/room-types/${roomTypeId}/availability/`, { params: { check_in, check_out } }),
  availabilityCalendar: (listingId: string, start: string, end: string) =>
    api.get(`/listings/${listingId}/calendar/`, { params: { start, end } }),

  bookings: (params?: Record<string, unknown>) => api.get('/bookings/', { params }),
  getBooking: (id: string) => api.get(`/bookings/${id}/`),
  createBooking: (data: Partial<Booking>) => api.post('/bookings/', data),
  cancelBooking: (id: string, reason: string) => api.post(`/bookings/${id}/cancel/`, { reason }),
  checkIn: (id: string) => api.post(`/bookings/${id}/check-in/`),
  checkOut: (id: string) => api.post(`/bookings/${id}/check-out/`),
}

// ---------- Services ----------
export const servicesApi = {
  categories: () => api.get('/service-categories/'),
  jobs: (params?: Record<string, unknown>) => api.get('/jobs/', { params }),
  getJob: (id: string) => api.get(`/jobs/${id}/`),
  createJob: (data: Partial<ServiceJob>) => api.post('/jobs/', data),
  startJob: (id: string) => api.post(`/jobs/${id}/start/`),
  completeJob: (id: string) => api.post(`/jobs/${id}/complete/`),
  submitQuote: (data: Partial<Quote>) => api.post('/quotes/', data),
  acceptQuote: (id: string) => api.post(`/quotes/${id}/accept/`),
  providerProfile: () => api.get('/provider-profile/'),
  updateProviderProfile: (data: Record<string, unknown>) => api.patch('/provider-profile/', data),
  publicProviders: (params?: Record<string, unknown>) => api.get('/public/providers/', { params }),
  providers: () => api.get('/providers/'),
}

// ---------- Payments ----------
export const paymentsApi = {
  resolveDispute: (id: string, action: 'confirm' | 'void', reason: string) =>
    api.post(`/payments/${id}/resolve-dispute/`, { action, reason }),
  list: (params?: Record<string, unknown>) => api.get('/payments/', { params }),
  stkPush: (data: { phone_number: string; amount: number; invoice_id?: string; booking_id?: string; description?: string }) =>
    api.post('/payments/mpesa/stk-push/', data),
  stkStatus: (paymentId: string) => api.get(`/payments/mpesa/status/${paymentId}/`),
  wallet: () => api.get('/wallet/'),
  requestPayout: (amount: number, phone_number: string) => api.post('/payouts/request/', { amount, phone_number }),
  payouts: () => api.get('/payouts/'),

  paybillTransactions: (params?: Record<string, unknown>) => api.get('/paybill-transactions/', { params }),
  reconcilePaybillTransaction: (transactionId: string, invoiceId: string) =>
    api.post(`/paybill-transactions/${transactionId}/reconcile/`, { invoice_id: invoiceId }),
}

// ---------- Lease Renewals ----------
export const renewalsApi = {
  list: (params?: Record<string, unknown>) => api.get('/lease-renewals/', { params }),
  get: (id: string) => api.get(`/lease-renewals/${id}/`),
  updateOffer: (id: string, data: { proposed_start_date?: string; proposed_end_date?: string; proposed_rent_amount?: number }) =>
    api.patch(`/lease-renewals/${id}/`, data),
  respond: (id: string, accept: boolean, decline_reason?: string) =>
    api.post(`/lease-renewals/${id}/respond/`, { accept, decline_reason }),
}

// ---------- Tenant Blacklist ----------
export const blacklistApi = {
  list: (params?: Record<string, unknown>) => api.get('/blacklist/', { params }),
  flag: (data: { tenant: string; lease?: string; reason: string; details: string; amount_owed?: number }) =>
    api.post('/blacklist/flag/', data),
  check: (tenantId: string) => api.get(`/blacklist/check/${tenantId}/`),
  respond: (id: string, response: string) => api.post(`/blacklist/${id}/respond/`, { response }),
  review: (id: string, status: 'active' | 'removed', review_notes?: string) =>
    api.post(`/blacklist/${id}/review/`, { status, review_notes }),
}

// ---------- Tenant Risk Score ----------
export const riskScoreApi = {
  get: (tenantId: string) => api.get(`/analytics/risk-score/${tenantId}/`),
  recalculate: (tenantId: string) => api.post(`/analytics/risk-score/${tenantId}/`),
}

// ---------- Property Documents (vault) ----------
export const documentsApi = {
  list: (propertyId: string, params?: Record<string, unknown>) =>
    api.get(`/properties/${propertyId}/documents/`, { params }),
  upload: (propertyId: string, formData: FormData) =>
    api.post(`/properties/${propertyId}/documents/`, formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  delete: (id: string) => api.delete(`/documents/${id}/`),
}

// ---------- Notifications ----------
export const notificationsApi = {
  list: (params?: Record<string, unknown>) => api.get('/notifications/', { params }),
  markRead: (id: string) => api.post(`/notifications/${id}/read/`),
  markAllRead: () => api.post('/notifications/read-all/'),
  unreadCount: () => api.get('/notifications/unread-count/'),
  preferences: () => api.get('/notification-preferences/'),
  updatePreferences: (data: Record<string, unknown>) => api.patch('/notification-preferences/', data),
}

// ---------- Analytics ----------
export const analyticsApi = {
  tenantDashboard: () => api.get<{ success: boolean; data: TenantDashboard }>('/analytics/dashboard/tenant/'),
  landlordDashboard: () => api.get<{ success: boolean; data: LandlordDashboard }>('/analytics/dashboard/landlord/'),
  adminDashboard: () => api.get<{ success: boolean; data: AdminDashboard }>('/analytics/dashboard/admin/'),
  serviceProviderDashboard: () => api.get<{ success: boolean; data: ServiceProviderDashboard }>('/analytics/dashboard/service-provider/'),
  hotelDashboard: () => api.get<{ success: boolean; data: HotelDashboard }>('/analytics/dashboard/hotel-owner/'),

  // Advanced analytics (chart data sources)
  vacancyAnalytics: () => api.get('/analytics/analytics/vacancy/'),
  maintenanceAnalytics: () => api.get('/analytics/analytics/maintenance/'),
  revenueForecast: (params?: { forecast_months?: number; lookback_months?: number }) =>
    api.get('/analytics/analytics/revenue-forecast/', { params }),
  leasingFunnel: (params?: { days?: number }) => api.get('/analytics/analytics/leasing-funnel/', { params }),
  aiUsageDashboard: (params?: { days?: number }) => api.get('/ai/usage-dashboard/', { params }),

  // Admin user management
  users: (params?: Record<string, unknown>) => api.get('/users/', { params }),
  getUser: (id: string) => api.get(`/users/${id}/`),
  updateUser: (id: string, data: Partial<User>) => api.patch(`/users/${id}/`, data),
  kycPending: () => api.get('/kyc/pending/'),
  reviewKyc: (userId: string, action: string, rejection_reason?: string) =>
    api.post(`/kyc/${userId}/review/`, { action, rejection_reason }),
}

// ---------- AI Features ----------
export const aiApi = {
  propertySearch: (query: string) => api.post('/ai/property-search/', { query }),
  rentEstimate: (data: { county: string; town?: string; bedrooms: number; amenities?: string[]; size_sqm?: number }) =>
    api.post('/ai/rent-estimate/', data),
  generateListing: (images: File[], facts: Record<string, unknown>) => {
    const formData = new FormData()
    images.forEach((img) => formData.append('images', img))
    formData.append('facts', JSON.stringify(facts))
    return api.post('/ai/generate-listing/', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  maintenanceTriage: (image: File, description?: string) => {
    const formData = new FormData()
    formData.append('image', image)
    if (description) formData.append('description', description)
    return api.post('/ai/maintenance-triage/', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
}

// ---------- Agency Management ----------
export const agencyApi = {
  list: (params?: Record<string, unknown>) => api.get('/agencies/', { params }),
  searchDirectory: (search: string) => api.get('/agencies/directory/', { params: { search } }),
  get: (id: string) => api.get(`/agencies/${id}/`),
  dashboard: (id: string) => api.get(`/agencies/${id}/dashboard/`),
  // Admin only: registers an agency company and creates its first Agency Admin's login (nobody self-registers).
  create: (data: Record<string, unknown>) => api.post('/agencies/', data),
  setStatus: (id: string, status: 'active' | 'suspended' | 'archived') => api.post(`/agencies/${id}/status/`, { status }),
  // Admin only: issue a new temporary password to an agency's Agency Admin (shown once).
  resetAdminPassword: (id: string) => api.post(`/agencies/${id}/reset-admin-password/`),
  update: (id: string, data: Record<string, unknown>) => api.patch(`/agencies/${id}/`, data),

  roles: (agencyId: string) => api.get(`/agencies/${agencyId}/roles/`),
  createRole: (agencyId: string, data: Record<string, unknown>) => api.post(`/agencies/${agencyId}/roles/`, data),

  members: (agencyId: string, params?: Record<string, unknown>) => api.get(`/agencies/${agencyId}/members/`, { params }),
  // Existing account => invitation. Unknown email => the agency creates the login (first_name, last_name, phone_number needed).
  inviteMember: (agencyId: string, email: string, role_id: string, extra: { first_name?: string; last_name?: string; phone_number?: string } = {}) =>
    api.post(`/agencies/${agencyId}/members/invite/`, { email, role_id, ...extra }),
  resetStaffPassword: (membershipId: string) => api.post(`/agencies/memberships/${membershipId}/reset-password/`),
  acceptInvite: (membershipId: string) => api.post(`/agency/members/${membershipId}/accept/`),
  suspendMember: (membershipId: string) => api.post(`/agency/members/${membershipId}/suspend/`),
  removeMember: (membershipId: string) => api.post(`/agency/members/${membershipId}/remove/`),

  propertyStaff: (propertyId?: string) => api.get('/agency/property-staff/', { params: propertyId ? { property: propertyId } : {} }),
  assignStaffToProperty: (property: string, membership: string) =>
    api.post('/agency/property-staff/', { property, membership }),
  removeStaffFromProperty: (id: string) => api.post(`/agency/property-staff/${id}/remove/`),

  feeRules: (agencyId: string) => api.get(`/agencies/${agencyId}/fee-rules/`),
  createFeeRule: (agencyId: string, data: Record<string, unknown>) => api.post(`/agencies/${agencyId}/fee-rules/`, data),

  agreements: (params?: Record<string, unknown>) => api.get('/agency/agreements/', { params }),
  getAgreement: (id: string) => api.get(`/agency/agreements/${id}/`),
  createAgreement: (data: Record<string, unknown>) => api.post('/agency/agreements/', data),
  signAgreement: (id: string, as: 'owner' | 'agency') => api.post(`/agency/agreements/${id}/sign/`, { as }),

  assignments: (params?: Record<string, unknown>) => api.get('/agency/assignments/', { params }),
  assignProperty: (data: {
    property_id: string; agency_id: string; start_date: string
    management_fee_percent?: number; payout_rule?: PayoutRule; fee_rule_id?: string
  }) => api.post('/agency/assignments/assign/', data),
  assignListing: (data: {
    listing_id: string; agency_id: string; start_date: string
    management_fee_percent?: number; payout_rule?: PayoutRule; fee_rule_id?: string
  }) => api.post('/agency/assignments/assign-listing/', data),
  endAssignment: (id: string, reason?: string) => api.post(`/agency/assignments/${id}/end/`, { reason }),

  ownerProperties: () => api.get('/owner/properties/'),
  ownerListings: () => api.get('/owner/listings/'),
  ownerPortfolio: (params?: { period_start: string; period_end: string }) => api.get('/owner/portfolio/', { params }),
  myProperties: () => api.get('/my-properties/'),

  statements: (params?: Record<string, unknown>) => api.get('/agency/statements/', { params }),
  getStatement: (id: string) => api.get(`/agency/statements/${id}/`),
  generateStatement: (property_id: string, period_start: string, period_end: string) =>
    api.post('/agency/statements/generate/', { property_id, period_start, period_end }),
  generateListingStatement: (listing_id: string, period_start: string, period_end: string) =>
    api.post('/agency/statements/generate-listing/', { listing_id, period_start, period_end }),
  issueStatement: (id: string) => api.post(`/agency/statements/${id}/issue/`),

  payouts: () => api.get('/agency/payouts/'),
  executePayout: (statementId: string, phone_number?: string) =>
    api.post(`/agency/statements/${statementId}/payout/`, { phone_number }),

  commissions: (params?: Record<string, unknown>) => api.get('/agency/commissions/', { params }),

  expenses: (agencyId: string, params?: Record<string, unknown>) => api.get(`/agencies/${agencyId}/expenses/`, { params }),
  createExpense: (agencyId: string, data: FormData | Record<string, unknown>) =>
    api.post(`/agencies/${agencyId}/expenses/`, data, data instanceof FormData ? { headers: { 'Content-Type': 'multipart/form-data' } } : undefined),

  auditLogs: (agencyId: string, params?: Record<string, unknown>) => api.get(`/agencies/${agencyId}/audit-logs/`, { params }),
}

// ---------- FRIDAH Chat ----------
export const chatApi = {
  threads: () => api.get('/chat/threads/'),
  startThread: (participant_id: string, body?: string, lease_id?: string) =>
    api.post('/chat/threads/', { participant_id, body, lease_id }),
  createGroup: (property_id: string, participant_ids: string[], subject?: string) =>
    api.post('/chat/threads/group/', { property_id, participant_ids, subject }),

  messages: (threadId: string) => api.get(`/chat/threads/${threadId}/messages/`),
  sendMessage: (threadId: string, body: string, message_type = 'text', reply_to_id?: string) =>
    api.post(`/chat/threads/${threadId}/messages/`, { body, message_type, reply_to_id }),
  uploadAttachment: (threadId: string, files: File[], file_type: string, caption?: string, duration_seconds?: number) => {
    const formData = new FormData()
    files.forEach((f) => formData.append('files', f))
    formData.append('file_type', file_type)
    if (caption) formData.append('caption', caption)
    if (duration_seconds) formData.append('duration_seconds', String(duration_seconds))
    return api.post(`/chat/threads/${threadId}/attachments/`, formData, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  shareObject: (threadId: string, object_type: string, object_id: string, card_data?: Record<string, unknown>) =>
    api.post(`/chat/threads/${threadId}/share/`, { object_type, object_id, card_data }),

  react: (messageId: string, emoji: string) => api.post(`/chat/messages/${messageId}/react/`, { emoji }),
  unreact: (messageId: string, emoji: string) => api.delete(`/chat/messages/${messageId}/react/`, { params: { emoji } }),

  startCall: (callee_id: string, call_type: 'voice' | 'video' = 'voice', thread_id?: string) =>
    api.post('/chat/calls/', { callee_id, call_type, thread_id }),
  updateCallStatus: (id: string, status: string) => api.post(`/chat/calls/${id}/status/`, { status }),

  relationships: () => api.get('/chat/relationships/'),
  postAnnouncement: (property_id: string, title: string, body: string, send_sms = false) =>
    api.post('/announcements/', { property_id, title, body, send_sms }),
}

// ---------- Payment Engine Extensions ----------
export const paymentExtrasApi = {
  paymentMethods: () => api.get('/payment-methods/'),
  addPaymentMethod: (data: Record<string, unknown>) => api.post('/payment-methods/', data),
  removePaymentMethod: (id: string) => api.delete(`/payment-methods/${id}/`),
  paymentAllocations: (paymentId: string) => api.get(`/payments/${paymentId}/allocations/`),

  tenantAdvances: (params?: Record<string, unknown>) => api.get('/tenant-advances/', { params }),
  requestAdvance: (data: { lease_id: string; amount: number; reason?: string; invoice_id?: string }) =>
    api.post('/tenant-advances/', data),
  approveAdvance: (id: string) => api.post(`/tenant-advances/${id}/approve/`),
  rejectAdvance: (id: string, reason?: string) => api.post(`/tenant-advances/${id}/reject/`, { reason }),

  serviceInvoices: (params?: Record<string, unknown>) => api.get('/service-invoices/', { params }),
  submitServiceInvoice: (data: FormData) =>
    api.post('/service-invoices/', data, { headers: { 'Content-Type': 'multipart/form-data' } }),
  approveServiceInvoice: (id: string, notes?: string) => api.post(`/service-invoices/${id}/approve/`, { notes }),
  rejectServiceInvoice: (id: string, notes?: string) => api.post(`/service-invoices/${id}/reject/`, { notes }),
  payServiceInvoice: (id: string) => api.post(`/service-invoices/${id}/pay/`),
}


// ---------- Property approval workflow (landlord + admin dual approval) ----------
export const approvalApi = {
  queue: () => api.get('/properties/review-queue/'),
  history: (propertyId: string) => api.get(`/properties/${propertyId}/approvals/`),
  // Landlord decision on an agency-submitted property
  landlordDecision: (propertyId: string, action: 'approve' | 'reject' | 'request_changes', comment = '') =>
    api.post(`/properties/${propertyId}/review/`, { action, comment }),
  // Administrator decision / listing actions
  adminDecision: (propertyId: string, action: 'approve' | 'reject' | 'request_changes' | 'suspend' | 'archive' | 'reinstate', comment = '') =>
    api.post(`/properties/${propertyId}/approval/`, { action, comment }),
  resubmit: (propertyId: string, comment = '') => api.post(`/properties/${propertyId}/resubmit/`, { comment }),
  withdraw: (propertyId: string, comment = '') => api.post(`/properties/${propertyId}/withdraw/`, { comment }),
}

// ---------- Tax (KRA) records ----------
export const taxApi = {
  types: () => api.get('/tax/types/'),
  createType: (data: Record<string, unknown>) => api.post('/tax/types/', data),
  rules: (params?: Record<string, unknown>) => api.get('/tax/rules/', { params }),
  createRule: (data: Record<string, unknown>) => api.post('/tax/rules/', data),
  records: (params?: Record<string, unknown>) => api.get('/tax/records/', { params }),
  estimate: (data: { statement: string; tax_type: string; taxpayer_type?: string; withholding?: string }) =>
    api.post('/tax/records/estimate/', data),
  adjust: (id: string, data: Record<string, unknown>) => api.post(`/tax/records/${id}/adjust/`, data),
  adjustments: (id: string) => api.get(`/tax/records/${id}/adjustments/`),
  summary: (params?: Record<string, unknown>) => api.get('/tax/summary/', { params }),
  exportCsvUrl: (year?: string) => `${api.defaults.baseURL}/tax/export/${year ? `?year=${year}` : ''}`,
  exportCsv: (year?: string) => api.get('/tax/export/', { params: { year }, responseType: 'blob' }),
}

// ---------- Amenity charges ----------
export const amenityApi = {
  list: (params?: Record<string, unknown>) => api.get('/amenity-charges/', { params }),
  create: (data: Record<string, unknown>) => api.post('/amenity-charges/', data),
  update: (id: string, data: Record<string, unknown>) => api.patch(`/amenity-charges/${id}/`, data),
  billNow: (id: string) => api.post(`/amenity-charges/${id}/bill-now/`),
  exempt: (data: { charge: string; lease: string; reason: string }) => api.post('/amenity-exemptions/', data),
  waiveInvoice: (invoiceId: string, reason: string) => api.post(`/invoices/${invoiceId}/waive/`, { reason }),
}

// ---------- Admin portfolio overview ----------
export const portfolioApi = {
  overview: (params?: Record<string, unknown>) => api.get('/analytics/dashboard/admin/portfolio/', { params }),
}


// ---------- Refunds, reversals, reconciliation, settlement ----------
export const refundApi = {
  list: (params?: Record<string, unknown>) => api.get('/refunds/', { params }),
  request: (paymentId: string, data: { amount: string | number; reason: string; kind?: 'refund' | 'reversal' }) =>
    api.post(`/payments/${paymentId}/refunds/`, data),
  approve: (id: string, comment = '', allowNegativeBalance = false) =>
    api.post(`/refunds/${id}/approve/`, { comment, allow_negative_balance: allowNegativeBalance }),
  reject: (id: string, comment: string) => api.post(`/refunds/${id}/reject/`, { comment }),
  cancel: (id: string) => api.post(`/refunds/${id}/cancel/`),
  markPaid: (id: string, reference: string) => api.post(`/refunds/${id}/mark-paid/`, { reference }),
  payOut: (id: string) => api.post(`/refunds/${id}/pay-out/`),
  policy: () => api.get('/refunds/policy/'),
  updatePolicy: (admin_approval_above: number | string, window_days: number | string) =>
    api.put('/refunds/policy/', { admin_approval_above, window_days }),
}

export const reconciliationApi = {
  runs: () => api.get('/reconciliation/runs/'),
  run: (id: string, openOnly = false) => api.get(`/reconciliation/runs/${id}/`, { params: openOnly ? { open: 1 } : {} }),
  runInternal: (period_start: string, period_end: string) => api.post('/reconciliation/runs/internal/', { period_start, period_end }),
  uploadStatement: (file: File, period_start: string, period_end: string) => {
    const form = new FormData()
    form.append('file', file); form.append('period_start', period_start); form.append('period_end', period_end)
    return api.post('/reconciliation/runs/statement/', form, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  resolveItem: (id: string, note: string) => api.post(`/reconciliation/items/${id}/resolve/`, { note }),
  settlement: (params?: Record<string, unknown>) => api.get('/settlement/summary/', { params }),
}
