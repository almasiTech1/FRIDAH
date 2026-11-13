// ============================================================
// FRIDAH Mobile — Shared TypeScript types
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
  national_id?: string
  kyc_rejection_reason?: string
  profile_photo?: string
  business_name?: string
  service_category?: string
  fcm_token?: string
  created_at: string
}

export interface AuthTokens {
  access: string
  refresh: string
}

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
  total_units: number
  vacant_units_count: number
  amenities: string[]
  primary_image?: string
  min_rent?: number
  created_at: string
  units?: Unit[]
  images?: { id: string; image: string }[]
}

export interface Unit {
  id: string
  property: string
  property_name: string
  unit_number: string
  bedrooms: number
  bathrooms: number
  rent_amount: number
  deposit_amount: number
  status: 'vacant' | 'occupied' | 'maintenance' | 'reserved'
}

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
  price_per_night: number
  total_rooms: number
  max_occupancy: number
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
  total_amount: number
  amount_paid: number
  status: 'pending_payment' | 'confirmed' | 'checked_in' | 'checked_out' | 'cancelled'
  booking_reference: string
  created_at: string
}

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
  quotes: Quote[]
  scheduled_date?: string
  created_at: string
}

export interface Quote {
  id: string
  job: string
  provider: string
  provider_name: string
  amount: number
  message: string
  estimated_days: number
  status: 'pending' | 'accepted' | 'rejected' | 'withdrawn'
  created_at: string
}

export interface Payment {
  id: string
  payer: string
  payer_name: string
  invoice?: string
  booking?: string
  method: string
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'
  amount: number
  phone_number: string
  reference: string
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

export interface Notification {
  id: string
  title: string
  message: string
  notification_type: string
  is_read: boolean
  created_at: string
}

export interface TenantDashboard {
  active_lease_id?: string
  rent_amount?: number
  pending_invoices_count: number
  pending_balance: number
  open_maintenance_requests: number
  total_paid_this_year: number
}

export interface LandlordDashboard {
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
  active_jobs: number
  completed_jobs: number
  pending_quotes: number
  accepted_quotes: number
  wallet_balance: number
  available_open_jobs: number
}

export interface HotelDashboard {
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
  status: AgencyStatus
  logo?: string
  email?: string
  phone_number?: string
  county?: string
  town?: string
  default_fee_percent: number
  managed_properties_count: number
  owners_count: number
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

export interface AgencyRole {
  id: string
  agency: string
  name: string
  role_type: AgencyRoleType
  permissions: string[]
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
  joined_at?: string
  created_at: string
}

export interface PropertyManagementAssignment {
  id: string
  property: string
  property_name: string
  owner_name: string
  agency: string
  agency_name: string
  management_fee_percent: number
  payout_rule: PayoutRule
  start_date: string
  end_date?: string
  status: AssignmentStatus
  created_at: string
}

export interface OwnerStatement {
  id: string
  property: string
  property_name: string
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
  issued_at?: string
  created_at: string
}

export interface OwnerPayout {
  id: string
  statement: string
  owner: string
  amount: number
  status: OwnerPayoutStatus
  reference: string
  created_at: string
  completed_at?: string
}

export interface AgencyExpense {
  id: string
  agency: string
  property: string
  property_name: string
  category: 'maintenance' | 'utilities' | 'compliance' | 'security' | 'cleaning' | 'other'
  description: string
  amount: number
  is_deductible_from_owner: boolean
  incurred_on: string
  created_at: string
}

export interface OwnedProperty {
  id: string
  name: string
  town: string
  county: string
  self_managed: boolean
  managing_agency: { id: string; name: string } | null
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
  attachments: { id: string; url: string; file_type: string; duration_seconds?: number }[]
  shared_object?: { id: string; object_type: string; card_data: Record<string, unknown> }
  reactions: Record<string, string[]>
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
