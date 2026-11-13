import api from './client'
import type {
  User, Lease, Invoice, MaintenanceRequest,
  Listing, RoomType, Booking, ServiceJob, Quote,
  TenantDashboard, LandlordDashboard, AdminDashboard,
  ServiceProviderDashboard, HotelDashboard,
} from '@/types'

// ─── Auth ────────────────────────────────────────────────────────────────────
export const authApi = {
  register: (data: Record<string, unknown>) =>
    api.post('/auth/register/', data),
  login: (email: string, password: string) =>
    api.post('/auth/login/', { email, password }),
  logout: (refresh: string) =>
    api.post('/auth/logout/', { refresh }),
  me: () =>
    api.get<{ success: boolean; data: User }>('/me/'),
  updateProfile: (data: Partial<User>) =>
    api.patch('/me/', data),
  changePassword: (old_password: string, new_password: string) =>
    api.post('/auth/change-password/', { old_password, new_password }),
  requestOtp: (purpose: string) =>
    api.post('/otp/request/', { purpose }),
  verifyOtp: (code: string, purpose: string) =>
    api.post('/otp/verify/', { code, purpose }),
  registerDevice: (device_id: string, fcm_token: string, platform: string) =>
    api.post('/me/device/', { device_id, fcm_token, platform }),
}

// ─── Properties ──────────────────────────────────────────────────────────────
export const propertiesApi = {
  list: (params?: Record<string, unknown>) =>
    api.get('/properties/', { params }),
  get: (id: string) =>
    api.get(`/properties/${id}/`),
  create: (data: Record<string, unknown>) =>
    api.post('/properties/', data),
  update: (id: string, data: Record<string, unknown>) =>
    api.patch(`/properties/${id}/`, data),
  approve: (id: string, action: string) =>
    api.post(`/properties/${id}/approval/`, { action }),
  units: (propertyId: string) =>
    api.get(`/properties/${propertyId}/units/`),
  createUnit: (propertyId: string, data: Record<string, unknown>) =>
    api.post(`/properties/${propertyId}/units/`, data),
  costOfLiving: (unitId: string) =>
    api.get(`/units/${unitId}/cost-of-living/`),
  recommendations: (limit?: number) =>
    api.get('/properties/recommendations/', { params: { limit } }),
}

// ─── Rentals ─────────────────────────────────────────────────────────────────
export const rentalsApi = {
  leases: (params?: Record<string, unknown>) =>
    api.get<{ success: boolean; data: { results: Lease[] } }>('/leases/', { params }),
  getLease: (id: string) =>
    api.get(`/leases/${id}/`),
  createLease: (data: Record<string, unknown>) =>
    api.post('/leases/', data),
  activateLease: (id: string) =>
    api.post(`/leases/${id}/activate/`),
  terminateLease: (id: string, reason: string) =>
    api.post(`/leases/${id}/terminate/`, { reason }),
  invoices: (params?: Record<string, unknown>) =>
    api.get<{ success: boolean; data: { results: Invoice[] } }>('/invoices/', { params }),
  getInvoice: (id: string) =>
    api.get(`/invoices/${id}/`),
  maintenanceList: (params?: Record<string, unknown>) =>
    api.get<{ success: boolean; data: { results: MaintenanceRequest[] } }>('/maintenance/', { params }),
  createMaintenance: (data: Record<string, unknown>) =>
    api.post('/maintenance/', data),
  resolveMaintenance: (id: string, notes: string) =>
    api.post(`/maintenance/${id}/resolve/`, { notes }),
  attachMaintenanceImage: (id: string, photo: { uri: string; name: string; type: string }) => {
    const formData = new FormData()
    formData.append('image', { uri: photo.uri, name: photo.name, type: photo.type } as any)
    return api.post(`/maintenance/${id}/images/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  assignMaintenance: (id: string, provider_id: string) =>
    api.post(`/maintenance/${id}/assign/`, { provider_id }),
  applyToUnit: (unitId: string, data: { message?: string; preferred_move_in_date?: string }) =>
    api.post(`/units/${unitId}/apply/`, data),
  applications: (params?: Record<string, unknown>) =>
    api.get('/rental-applications/', { params }),
  approveApplication: (id: string, data: Record<string, unknown>) =>
    api.post(`/rental-applications/${id}/approve/`, data),
  rejectApplication: (id: string, reason?: string) =>
    api.post(`/rental-applications/${id}/reject/`, { reason }),
  withdrawApplication: (id: string) =>
    api.post(`/rental-applications/${id}/withdraw/`),
}

// ─── Lease Renewals ───────────────────────────────────────────────────────────
export const renewalsApi = {
  list: (params?: Record<string, unknown>) =>
    api.get('/lease-renewals/', { params }),
  get: (id: string) =>
    api.get(`/lease-renewals/${id}/`),
  updateOffer: (id: string, data: Record<string, unknown>) =>
    api.patch(`/lease-renewals/${id}/`, data),
  respond: (id: string, accept: boolean, decline_reason?: string) =>
    api.post(`/lease-renewals/${id}/respond/`, { accept, decline_reason }),
}

// ─── Tenant Blacklist ─────────────────────────────────────────────────────────
export const blacklistApi = {
  list: (params?: Record<string, unknown>) =>
    api.get('/blacklist/', { params }),
  flag: (data: Record<string, unknown>) =>
    api.post('/blacklist/flag/', data),
  check: (tenantId: string) =>
    api.get(`/blacklist/check/${tenantId}/`),
  respond: (id: string, response: string) =>
    api.post(`/blacklist/${id}/respond/`, { response }),
  review: (id: string, status: 'active' | 'removed', review_notes?: string) =>
    api.post(`/blacklist/${id}/review/`, { status, review_notes }),
}

// ─── Tenant Risk Score ────────────────────────────────────────────────────────
export const riskScoreApi = {
  get: (tenantId: string) =>
    api.get(`/analytics/risk-score/${tenantId}/`),
  recalculate: (tenantId: string) =>
    api.post(`/analytics/risk-score/${tenantId}/`),
}

// ─── Property Documents (vault) ───────────────────────────────────────────────
export const documentsApi = {
  list: (propertyId: string, params?: Record<string, unknown>) =>
    api.get(`/properties/${propertyId}/documents/`, { params }),
  upload: (propertyId: string, formData: FormData) =>
    api.post(`/properties/${propertyId}/documents/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  delete: (id: string) =>
    api.delete(`/documents/${id}/`),
}

// ─── Bookings ─────────────────────────────────────────────────────────────────
export const bookingsApi = {
  listings: (params?: Record<string, unknown>) =>
    api.get<{ success: boolean; data: { results: Listing[] } }>('/listings/', { params }),
  getListing: (id: string) =>
    api.get(`/listings/${id}/`),
  createListing: (data: Record<string, unknown>) =>
    api.post('/listings/', data),
  approveListing: (id: string, action: string) =>
    api.post(`/listings/${id}/approval/`, { action }),
  roomTypes: (listingId: string) =>
    api.get<{ success: boolean; data: { results: RoomType[] } }>(`/listings/${listingId}/room-types/`),
  createRoomType: (listingId: string, data: Record<string, unknown>) =>
    api.post(`/listings/${listingId}/room-types/`, data),
  checkAvailability: (roomTypeId: string, check_in: string, check_out: string) =>
    api.get(`/room-types/${roomTypeId}/availability/`, { params: { check_in, check_out } }),
  bookings: (params?: Record<string, unknown>) =>
    api.get<{ success: boolean; data: { results: Booking[] } }>('/bookings/', { params }),
  getBooking: (id: string) =>
    api.get(`/bookings/${id}/`),
  createBooking: (data: Record<string, unknown>) =>
    api.post('/bookings/', data),
  cancelBooking: (id: string, reason: string) =>
    api.post(`/bookings/${id}/cancel/`, { reason }),
  checkIn: (id: string) =>
    api.post(`/bookings/${id}/check-in/`),
  checkOut: (id: string) =>
    api.post(`/bookings/${id}/check-out/`),
  availabilityCalendar: (listingId: string, start: string, end: string) =>
    api.get(`/listings/${listingId}/calendar/`, { params: { start, end } }),
}

// ─── Services ────────────────────────────────────────────────────────────────
export const servicesApi = {
  categories: () =>
    api.get('/service-categories/'),
  jobs: (params?: Record<string, unknown>) =>
    api.get<{ success: boolean; data: { results: ServiceJob[] } }>('/jobs/', { params }),
  getJob: (id: string) =>
    api.get(`/jobs/${id}/`),
  submitQuote: (data: Partial<Quote>) =>
    api.post('/quotes/', data),
  acceptQuote: (id: string) =>
    api.post(`/quotes/${id}/accept/`),
  startJob: (id: string) =>
    api.post(`/jobs/${id}/start/`),
  completeJob: (id: string) =>
    api.post(`/jobs/${id}/complete/`),
  providerProfile: () =>
    api.get('/provider-profile/'),
  updateProviderProfile: (data: Record<string, unknown>) =>
    api.patch('/provider-profile/', data),
}

// ─── Payments ────────────────────────────────────────────────────────────────
export const paymentsApi = {
  list: (params?: Record<string, unknown>) =>
    api.get('/payments/', { params }),
  stkPush: (data: {
    phone_number: string
    amount: number
    invoice_id?: string
    booking_id?: string
    description?: string
  }) => api.post('/payments/mpesa/stk-push/', data),
  stkStatus: (paymentId: string) =>
    api.get(`/payments/mpesa/status/${paymentId}/`),
  wallet: () =>
    api.get('/wallet/'),
  requestPayout: (amount: number, phone_number: string) =>
    api.post('/payouts/request/', { amount, phone_number }),
  payouts: () =>
    api.get('/payouts/'),
  paybillTransactions: (params?: Record<string, unknown>) =>
    api.get('/paybill-transactions/', { params }),
  reconcilePaybillTransaction: (transactionId: string, invoiceId: string) =>
    api.post(`/paybill-transactions/${transactionId}/reconcile/`, { invoice_id: invoiceId }),
}

// ─── Notifications ───────────────────────────────────────────────────────────
export const notificationsApi = {
  preferences: () => api.get('/notification-preferences/'),
  updatePreferences: (data: Record<string, unknown>) => api.patch('/notification-preferences/', data),
  list: () =>
    api.get('/notifications/'),
  markRead: (id: string) =>
    api.post(`/notifications/${id}/read/`),
  markAllRead: () =>
    api.post('/notifications/read-all/'),
  unreadCount: () =>
    api.get('/notifications/unread-count/'),
}

// ─── Agency Management ───────────────────────────────────────────────────────
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

  members: (agencyId: string, params?: Record<string, unknown>) => api.get(`/agencies/${agencyId}/members/`, { params }),
  // Existing account => invitation. Unknown email => the agency creates the login (first_name, last_name, phone_number needed).
  inviteMember: (agencyId: string, email: string, role_id: string, extra: { first_name?: string; last_name?: string; phone_number?: string } = {}) =>
    api.post(`/agencies/${agencyId}/members/invite/`, { email, role_id, ...extra }),
  resetStaffPassword: (membershipId: string) => api.post(`/agencies/memberships/${membershipId}/reset-password/`),
  suspendMember: (membershipId: string) => api.post(`/agency/members/${membershipId}/suspend/`),
  removeMember: (membershipId: string) => api.post(`/agency/members/${membershipId}/remove/`),

  assignments: (params?: Record<string, unknown>) => api.get('/agency/assignments/', { params }),
  assignProperty: (data: {
    property_id: string; agency_id: string; start_date: string
    management_fee_percent?: number; payout_rule?: string
  }) => api.post('/agency/assignments/assign/', data),
  endAssignment: (id: string, reason?: string) => api.post(`/agency/assignments/${id}/end/`, { reason }),

  ownerProperties: () => api.get('/owner/properties/'),

  statements: (params?: Record<string, unknown>) => api.get('/agency/statements/', { params }),
  generateStatement: (property_id: string, period_start: string, period_end: string) =>
    api.post('/agency/statements/generate/', { property_id, period_start, period_end }),
  issueStatement: (id: string) => api.post(`/agency/statements/${id}/issue/`),

  payouts: () => api.get('/agency/payouts/'),
  executePayout: (statementId: string, phone_number?: string) =>
    api.post(`/agency/statements/${statementId}/payout/`, { phone_number }),

  expenses: (agencyId: string, params?: Record<string, unknown>) => api.get(`/agencies/${agencyId}/expenses/`, { params }),
  createExpense: (agencyId: string, data: Record<string, unknown>) => api.post(`/agencies/${agencyId}/expenses/`, data),

  auditLogs: (agencyId: string) => api.get(`/agencies/${agencyId}/audit-logs/`),
}

// ─── FRIDAH Chat ─────────────────────────────────────────────────────────────
export const chatApi = {
  threads: () => api.get('/chat/threads/'),
  startThread: (participant_id: string, body?: string) =>
    api.post('/chat/threads/', { participant_id, body }),
  createGroup: (property_id: string, participant_ids: string[], subject?: string) =>
    api.post('/chat/threads/group/', { property_id, participant_ids, subject }),

  messages: (threadId: string) => api.get(`/chat/threads/${threadId}/messages/`),
  sendMessage: (threadId: string, body: string, message_type = 'text') =>
    api.post(`/chat/threads/${threadId}/messages/`, { body, message_type }),

  uploadAttachment: (
    threadId: string,
    files: { uri: string; name: string; type: string }[],
    file_type: 'image' | 'video' | 'document' | 'voice_note',
    caption?: string,
    duration_seconds?: number,
  ) => {
    const formData = new FormData()
    files.forEach((f) => {
      // React Native's fetch/FormData polyfill expects this exact shape for file
      // parts (not a real Blob/File instance, unlike web).
      formData.append('files', { uri: f.uri, name: f.name, type: f.type } as any)
    })
    formData.append('file_type', file_type)
    if (caption) formData.append('caption', caption)
    if (duration_seconds) formData.append('duration_seconds', String(duration_seconds))
    return api.post(`/chat/threads/${threadId}/attachments/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  react: (messageId: string, emoji: string) => api.post(`/chat/messages/${messageId}/react/`, { emoji }),
  unreact: (messageId: string, emoji: string) => api.delete(`/chat/messages/${messageId}/react/`, { params: { emoji } }),

  relationships: () => api.get('/chat/relationships/'),
  postAnnouncement: (property_id: string, title: string, body: string, send_sms = false) =>
    api.post('/announcements/', { property_id, title, body, send_sms }),
}

// ─── Payment Engine Extensions ───────────────────────────────────────────────
export const paymentExtrasApi = {
  tenantAdvances: (params?: Record<string, unknown>) => api.get('/tenant-advances/', { params }),
  requestAdvance: (data: { lease_id: string; amount: number; reason?: string; invoice_id?: string }) =>
    api.post('/tenant-advances/', data),
  approveAdvance: (id: string) => api.post(`/tenant-advances/${id}/approve/`),
  rejectAdvance: (id: string, reason?: string) => api.post(`/tenant-advances/${id}/reject/`, { reason }),

  serviceInvoices: (params?: Record<string, unknown>) => api.get('/service-invoices/', { params }),
  approveServiceInvoice: (id: string, notes?: string) => api.post(`/service-invoices/${id}/approve/`, { notes }),
  rejectServiceInvoice: (id: string, notes?: string) => api.post(`/service-invoices/${id}/reject/`, { notes }),
  payServiceInvoice: (id: string) => api.post(`/service-invoices/${id}/pay/`),
}
// ─── Analytics ───────────────────────────────────────────────────────────────
export const analyticsApi = {
  tenantDashboard: () =>
    api.get<{ success: boolean; data: TenantDashboard }>('/analytics/dashboard/tenant/'),
  landlordDashboard: () =>
    api.get<{ success: boolean; data: LandlordDashboard }>('/analytics/dashboard/landlord/'),
  adminDashboard: () =>
    api.get<{ success: boolean; data: AdminDashboard }>('/analytics/dashboard/admin/'),
  serviceProviderDashboard: () =>
    api.get<{ success: boolean; data: ServiceProviderDashboard }>('/analytics/dashboard/service-provider/'),
  hotelDashboard: () =>
    api.get<{ success: boolean; data: HotelDashboard }>('/analytics/dashboard/hotel-owner/'),
  users: (params?: Record<string, unknown>) =>
    api.get('/users/', { params }),
  kycPending: () =>
    api.get('/kyc/pending/'),
  reviewKyc: (userId: string, action: string, rejection_reason?: string) =>
    api.post(`/kyc/${userId}/review/`, { action, rejection_reason }),
  submitKyc: (national_id: string, document: { uri: string; name: string; type: string }) => {
    const formData = new FormData()
    formData.append('national_id', national_id)
    // React Native's fetch/FormData polyfill expects this exact shape for file
    // parts (not a real Blob/File instance, unlike web) - same pattern as chat attachments.
    formData.append('kyc_document', { uri: document.uri, name: document.name, type: document.type } as any)
    return api.post('/kyc/submit/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}

export const aiApi = {
  propertySearch: (query: string) =>
    api.post('/ai/property-search/', { query }),
  maintenanceTriage: (photo: { uri: string; name: string; type: string }, description?: string) => {
    const formData = new FormData()
    formData.append('image', { uri: photo.uri, name: photo.name, type: photo.type } as any)
    if (description) formData.append('description', description)
    return api.post('/ai/maintenance-triage/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}


// ─── Property approvals (landlord + admin dual approval) ──────────────────────
export const approvalApi = {
  queue: () => api.get('/properties/review-queue/'),
  landlordDecision: (id: string, action: 'approve' | 'reject' | 'request_changes', comment = '') =>
    api.post(`/properties/${id}/review/`, { action, comment }),
  adminDecision: (id: string, action: 'approve' | 'reject' | 'request_changes', comment = '') =>
    api.post(`/properties/${id}/approval/`, { action, comment }),
}

// ─── Tax records (estimates are labelled as such by the API) ──────────────────
export const taxApi = {
  records: (params?: Record<string, unknown>) => api.get('/tax/records/', { params }),
  summary: (params?: Record<string, unknown>) => api.get('/tax/summary/', { params }),
}

// ─── Amenity charges ──────────────────────────────────────────────────────────
export const amenityApi = {
  list: () => api.get('/amenity-charges/'),
  update: (id: string, data: Record<string, unknown>) => api.patch(`/amenity-charges/${id}/`, data),
  billNow: (id: string) => api.post(`/amenity-charges/${id}/bill-now/`),
}


// ─── Refunds & reversals ──────────────────────────────────────────────────────
export const refundApi = {
  list: (params?: Record<string, unknown>) => api.get('/refunds/', { params }),
  approve: (id: string, comment = '') => api.post(`/refunds/${id}/approve/`, { comment }),
  reject: (id: string, comment: string) => api.post(`/refunds/${id}/reject/`, { comment }),
  cancel: (id: string) => api.post(`/refunds/${id}/cancel/`),
  request: (paymentId: string, data: { amount: string | number; reason: string }) => api.post(`/payments/${paymentId}/refunds/`, data),
  markPaid: (id: string, reference: string) => api.post(`/refunds/${id}/mark-paid/`, { reference }),
  payOut: (id: string) => api.post(`/refunds/${id}/pay-out/`),
  policy: () => api.get('/refunds/policy/'),
}

export const reconciliationApi = {
  runs: () => api.get('/reconciliation/runs/'),
  run: (id: string) => api.get(`/reconciliation/runs/${id}/`),
  runInternal: (period_start: string, period_end: string) => api.post('/reconciliation/runs/internal/', { period_start, period_end }),
  resolveItem: (id: string, note: string) => api.post(`/reconciliation/items/${id}/resolve/`, { note }),
  settlement: () => api.get('/settlement/summary/'),
}
