// ============================================================
// FRIDAH — Shared TypeScript types
// ============================================================

export type Role = 'tenant' | 'landlord' | 'admin' | 'service_provider' | 'hotel_owner'
export type KYCStatus = 'not_submitted' | 'pending' | 'verified' | 'rejected'

export interface User {
  id: string
  username: string
  email: string
  phone_number: string
  first_name: string
  last_name: string
  role: Role
  kyc_status: KYCStatus
  is_kyc_verified: boolean
  is_phone_verified: boolean
  must_change_password?: boolean
  county?: string
  town?: string
  profile_photo?: string
  business_name?: string
  service_category?: string
  created_at: string
}

export interface AuthTokens {
  access: string
  refresh: string
}

// ---------- Properties ----------
export interface Property {
  id: string
  landlord: string
  landlord_name: string
  name: string
  description: string
  property_type: string
  status: 'active' | 'pending_approval' | 'suspended' | 'archived'
  county: string
  town: string
  estate?: string
  address_detail?: string
  latitude?: number
  longitude?: number
  total_units: number
  vacant_units_count: number
  amenities: string[]
  primary_image?: string
  min_rent?: number
  created_at: string
  units?: Unit[]
  images?: { id: string; image: string }[]
  landlord_phone?: string
  average_rating?: number
  review_state?: 'awaiting_landlord' | 'awaiting_admin' | 'approved' | 'changes_requested' | 'rejected' | 'withdrawn'
  submission_version?: number
  requires_landlord_approval?: boolean
}

export interface Unit {
  id: string
  property: string
  property_name: string
  unit_number: string
  bedrooms: number
  bathrooms: number
  size_sqm?: number
  rent_amount: number
  deposit_amount: number
  status: 'vacant' | 'occupied' | 'maintenance' | 'reserved'
  floor?: string
  description?: string
}

// ---------- Rentals ----------
export interface Lease {
  id: string
  tenant: string
  tenant_name: string
  unit: string
  unit_number: string
  property_name: string
  landlord: string
  start_date: string
  end_date?: string
  rent_amount: number
  deposit_amount: number
  deposit_paid: boolean
  rent_due_day: number
  status: 'pending' | 'active' | 'terminated' | 'expired'
  created_at: string
}

export interface Invoice {
  id: string
  invoice_number: string
  lease: string
  tenant: string
  tenant_name: string
  invoice_type: 'rent' | 'deposit' | 'penalty' | 'utility' | 'other'
  amount: number
  amount_paid: number
  balance: number
  period_start: string
  period_end: string
  due_date: string
  status: 'pending' | 'paid' | 'partially_paid' | 'overdue' | 'cancelled'
  is_overdue: boolean
  pdf_receipt?: string
  created_at: string
}

export interface MaintenanceRequest {
  id: string
  tenant: string
  tenant_name: string
  unit: string
  unit_number: string
  property_name: string
  category: string
  title: string
  description: string
  priority: 'low' | 'medium' | 'high' | 'urgent'
  status: 'open' | 'assigned' | 'in_progress' | 'resolved' | 'closed'
  assigned_provider?: string
  provider_name?: string
  resolved_at?: string
  resolution_notes?: string
  created_at: string
}

// ---------- Bookings ----------
export interface Listing {
  id: string
  host: string
  host_name: string
  host_phone?: string
  name: string
  description: string
  listing_type: 'hotel' | 'bnb' | 'apartment_stay' | 'villa'
  status: 'active' | 'pending_approval' | 'suspended'
  county: string
  town: string
  address_detail?: string
  latitude?: number
  longitude?: number
  amenities: string[]
  primary_image?: string
  min_price?: number
  check_in_time: string
  check_out_time: string
  cancellation_policy?: string
  images?: { id: string; image: string; is_primary: boolean }[]
  room_types?: RoomType[]
}

export interface RoomType {
  id: string
  listing: string
  name: string
  description: string
  max_occupancy: number
  price_per_night: number
  total_rooms: number
  amenities: string[]
}

export interface Booking {
  id: string
  guest: string
  guest_name: string
  listing: string
  listing_name: string
  room_type: string
  room_type_name: string
  host: string
  check_in_date: string
  check_out_date: string
  nights: number
  num_guests: number
  num_rooms: number
  total_amount: number
  amount_paid: number
  status: 'pending_payment' | 'confirmed' | 'checked_in' | 'checked_out' | 'cancelled'
  booking_reference: string
  special_requests?: string
  created_at: string
}

// ---------- Services ----------
export interface ServiceJob {
  id: string
  posted_by: string
  posted_by_name: string
  category: string
  category_name: string
  title: string
  description: string
  county: string
  town: string
  budget_estimate?: number
  status: 'open' | 'quoted' | 'assigned' | 'in_progress' | 'completed' | 'cancelled'
  assigned_provider?: string
  provider_name?: string
  scheduled_date?: string
  completed_at?: string
  quotes: Quote[]
  created_at: string
}

export interface Quote {
  id: string
  job: string
  provider: string
  provider_name: string
  provider_phone: string
  amount: number
  message: string
  estimated_days: number
  status: 'pending' | 'accepted' | 'rejected' | 'withdrawn'
  created_at: string
}

// ---------- Payments ----------
export interface Payment {
  id: string
  payer: string
  payer_name: string
  invoice?: string
  booking?: string
  method: 'mpesa_stk' | 'mpesa_c2b' | 'cash' | 'bank'
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'
  amount: number
  phone_number: string
  reference: string
  description?: string
  failure_reason?: string
  created_at: string
  completed_at?: string
}

export interface WalletTransaction {
  id: string
  entry_type: 'credit' | 'debit'
  amount: number
  balance_after: number
  description: string
  created_at: string
}

export interface Payout {
  id: string
  recipient: string
  recipient_name: string
  amount: number
  commission_amount: number
  phone_number: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  transaction_id?: string
  result_desc?: string
  created_at: string
}

// ---------- Notifications ----------
export interface Notification {
  id: string
  title: string
  message: string
  notification_type: string
  is_read: boolean
  metadata: Record<string, unknown>
  created_at: string
}

// ---------- API response wrapper ----------
export interface ApiResponse<T> {
  success: boolean
  message: string
  data: T
}

export interface PaginatedResponse<T> {
  count: number
  next?: string
  previous?: string
  results: T[]
}

// ---------- Dashboard types ----------
export interface TenantDashboard {
  active_lease_id?: string
  rent_amount?: number
  pending_invoices_count: number
  pending_balance: number
  open_maintenance_requests: number
  total_paid_this_year: number
}

export interface LandlordDashboard {
  collected_by_month?: { month: string; amount: number }[]
  total_properties: number
  total_units: number
  occupied_units: number
  vacant_units: number
  active_leases: number
  overdue_invoices_count: number
  overdue_amount: number
  collected_this_month: number
  open_maintenance_requests: number
  wallet_balance: number
}

export interface AdminDashboard {
  revenue_by_month?: { month: string; amount: number }[]
  payouts_by_month?: { month: string; amount: number }[]
  total_users: number
  users_by_role: Record<string, number>
  total_properties: number
  total_listings: number
  pending_property_approvals: number
  pending_listing_approvals: number
  pending_kyc: number
  active_leases: number
  active_bookings: number
  total_revenue_this_month: number
  total_payouts_this_month: number
  open_maintenance_requests: number
  new_signups_this_month: number
}

export interface ServiceProviderDashboard {
  earnings_by_month?: { month: string; amount: number }[]
  active_jobs: number
  completed_jobs: number
  pending_quotes: number
  accepted_quotes: number
  wallet_balance: number
  available_open_jobs: number
}

export interface HotelDashboard {
  revenue_by_month?: { month: string; amount: number }[]
  total_listings: number
  active_listings: number
  upcoming_checkins: number
  current_guests: number
  total_bookings_this_month: number
  revenue_this_month: number
  wallet_balance: number
}

// ============================================================
// Agency Management
// ============================================================
export type AgencyStatus = 'pending_approval' | 'active' | 'suspended' | 'archived'
export type AgencyRoleType = 'agency_admin' | 'property_manager' | 'caretaker' | 'finance_officer' | 'leasing_agent' | 'custom'
export type MembershipStatus = 'invited' | 'active' | 'suspended' | 'removed'
export type AssignmentStatus = 'active' | 'ended' | 'terminated'
export type PayoutRule = 'owner_direct' | 'agency_collects'
export type StatementStatus = 'draft' | 'issued' | 'paid'
export type OwnerPayoutStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface Agency {
  id: string
  name: string
  registration_number?: string
  kra_pin?: string
  status: AgencyStatus
  logo?: string
  email?: string
  phone_number?: string
  county?: string
  town?: string
  address_detail?: string
  default_fee_percent: number
  managed_properties_count: number
  owners_count: number
  created_at: string
}

export interface AgencyRole {
  id: string
  agency: string
  name: string
  role_type: AgencyRoleType
  permissions: string[]
  created_at: string
}

export interface AgencyMembership {
  id: string
  agency: string
  user: string
  user_name: string
  user_email: string
  role: string
  role_name: string
  role_type: AgencyRoleType
  status: MembershipStatus
  invited_by?: string
  joined_at?: string
  removed_at?: string
  created_at: string
}

export interface PropertyStaffAssignment {
  id: string
  property: string
  property_name: string
  membership: string
  user_name: string
  is_active: boolean
  assigned_at: string
  removed_at?: string
}

export interface AgencyFeeRule {
  id: string
  agency: string
  name: string
  fee_type: 'percentage' | 'flat'
  fee_value: number
  is_default: boolean
  created_at: string
}

export interface ManagementAgreement {
  id: string
  property: string
  property_name: string
  agency: string
  agency_name: string
  owner: string
  fee_rule?: string
  management_fee_percent: number
  payout_rule: PayoutRule
  start_date: string
  end_date?: string
  status: 'draft' | 'pending_signatures' | 'active' | 'ended' | 'terminated'
  document?: string
  terms: Record<string, unknown>
  signed_by_owner_at?: string
  signed_by_agency_at?: string
  is_fully_signed: boolean
  created_at: string
}

export interface PropertyManagementAssignment {
  id: string
  property: string | null
  property_name: string | null
  listing: string | null
  listing_name: string | null
  item_type: 'property' | 'listing'
  location: string
  owner_name: string
  owner_email: string | null
  owner_phone: string | null
  agency: string
  agency_name: string
  agreement?: string
  fee_rule?: string
  management_fee_percent: number
  payout_rule: PayoutRule
  start_date: string
  end_date?: string
  status: AssignmentStatus
  approved_by?: string
  ended_reason?: string
  ended_at?: string
  created_at: string
}

export interface OwnerStatement {
  id: string
  property: string | null
  property_name: string | null
  listing: string | null
  listing_name: string | null
  agency?: string
  agency_name?: string
  owner: string
  owner_name: string
  period_start: string
  period_end: string
  gross_rent_collected: number
  vacancy_loss: number
  arrears: number
  agency_commission: number
  approved_expenses: number
  other_deductions: number
  net_payable: number
  status: StatementStatus
  pdf_statement?: string
  issued_at?: string
  created_at: string
}

export interface OwnerPayout {
  id: string
  statement: string
  owner: string
  amount: number
  method: string
  phone_number?: string
  status: OwnerPayoutStatus
  reference: string
  transaction_id?: string
  created_at: string
  completed_at?: string
}

export interface AgencyCommission {
  id: string
  agency: string
  property: string
  property_name: string
  assignment?: string
  statement?: string
  period_start: string
  period_end: string
  gross_amount: number
  commission_rate: number
  commission_amount: number
  created_at: string
}

export interface AgencyExpense {
  id: string
  agency: string
  property: string
  property_name: string
  category: 'maintenance' | 'utilities' | 'compliance' | 'security' | 'cleaning' | 'other'
  description: string
  amount: number
  receipt?: string
  is_deductible_from_owner: boolean
  incurred_on: string
  recorded_by?: string
  approved_by?: string
  statement?: string
  created_at: string
}

export interface AgencyAuditLog {
  id: string
  agency: string
  actor?: string
  actor_name?: string
  action: string
  target_type: string
  target_id: string
  changes: Record<string, unknown>
  created_at: string
}

export interface AgencyDirectoryEntry {
  id: string
  name: string
  logo?: string
  county?: string
  town?: string
  managed_properties_count: number
  owners_count: number
}

export interface OwnedProperty {
  id: string
  name: string
  town: string
  county: string
  self_managed: boolean
  managing_agency: {
    id: string
    name: string
    email: string
    phone_number: string
    assignment_id: string
    management_fee_percent: string
    payout_rule: PayoutRule
    managed_since: string
    agreement_id: string | null
    agreement_status: ManagementAgreement['status'] | null
  } | null
}

export interface OwnedListing {
  id: string
  name: string
  town: string
  county: string
  listing_type: string
  self_managed: boolean
  managing_agency: {
    id: string
    name: string
    email: string
    phone_number: string
    assignment_id: string
    management_fee_percent: string
    payout_rule: PayoutRule
    managed_since: string
    agreement_id: string | null
    agreement_status: ManagementAgreement['status'] | null
  } | null
}

// ============================================================
// FRIDAH Chat
// ============================================================
export type ThreadType =
  | 'tenant_landlord' | 'tenant_agency' | 'tenant_caretaker' | 'tenant_provider'
  | 'landlord_agency' | 'agency_provider' | 'property_group' | 'listing_inquiry'
  | 'service_job' | 'direct'
export type MessageType =
  | 'text' | 'image' | 'video' | 'document' | 'voice_note'
  | 'property_card' | 'invoice_card' | 'payment_request' | 'maintenance_card'
  | 'booking_card' | 'lease_card' | 'system'

export interface ChatParticipant {
  id: string
  name: string
  role: string
}

export interface ChatThreadSummary {
  id: string
  thread_type: ThreadType
  subject: string
  is_group: boolean
  property_id?: string
  unread_count: number
  participants: ChatParticipant[]
  last_message: { body: string; message_type: MessageType; created_at: string; sender: string } | null
  updated_at: string
}

export interface ChatMessage {
  id: string
  thread_id: string
  sender_id?: string
  sender_name: string
  message_type: MessageType
  body: string
  attachment_url?: string
  attachments: { id: string; url: string; file_type: string; duration_seconds?: number; thumbnail_url?: string }[]
  shared_object?: { id: string; object_type: string; card_data: Record<string, unknown> }
  reply_to_id?: string
  reactions: Record<string, string[]>
  is_edited: boolean
  is_deleted: boolean
  delivery_status?: string
  created_at: string
}

export interface ChatRelationship {
  id: string
  name: string
  role: string
  relationships: string[]
}

// ============================================================
// Payment Engine Extensions
// ============================================================
export interface PaymentMethod {
  id: string
  method_type: 'mpesa' | 'bank' | 'card'
  label: string
  phone_number?: string
  bank_name?: string
  account_number?: string
  account_name?: string
  is_default: boolean
  is_verified: boolean
  created_at: string
}

export interface TenantAdvance {
  id: string
  tenant: string
  tenant_name: string
  invoice?: string
  lease: string
  amount: number
  amount_repaid: number
  balance_outstanding: number
  reason: string
  status: 'pending_approval' | 'active' | 'repaid' | 'written_off' | 'rejected'
  approved_by?: string
  requested_at: string
  approved_at?: string
  due_date?: string
}

export interface ServiceProviderInvoice {
  id: string
  job: string
  provider: string
  provider_name: string
  amount: number
  description: string
  attachment?: string
  status: 'submitted' | 'approved' | 'disputed' | 'paid' | 'rejected'
  reviewed_by?: string
  review_notes?: string
  reviewed_at?: string
  payout?: string
  created_at: string
}


// ---- Owner portfolio (landlord / hotel owner's view of everything they own) ----
export interface PortfolioManager {
  id: string
  name: string
  email: string
  phone_number: string
  management_fee_percent: string
  payout_rule: PayoutRule
  managed_since: string
}

export interface PortfolioProperty {
  id: string
  name: string
  town: string
  county: string
  status: string
  self_managed: boolean
  managed_by: PortfolioManager | null
  total_units: number
  occupied_units: number
  tenants: { name: string; phone_number: string; unit: string; rent_amount: string; lease_end: string | null }[]
  revenue_collected: string
  agency_fee: string
  net_to_owner: string
  arrears: string
}

export interface PortfolioListing {
  id: string
  name: string
  town: string
  county: string
  listing_type: string
  self_managed: boolean
  managed_by: PortfolioManager | null
  occupancy_percent: string
  guests_in_house: { name: string; room_type: string; check_in: string; check_out: string }[]
  revenue_collected: string
  agency_fee: string
  net_to_owner: string
}

export interface OwnerPortfolio {
  period_start: string
  period_end: string
  totals: {
    revenue_collected: string
    agency_fees: string
    net_to_owner: string
    agency_managed: number
    self_managed: number
  }
  properties: PortfolioProperty[]
  listings: PortfolioListing[]
}
