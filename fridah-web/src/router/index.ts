import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getAccessToken } from '@/api/client'

const routes: RouteRecordRaw[] = [
  // ---------- Public marketing site ----------
  {
    path: '/',
    component: () => import('@/layouts/PublicLayout.vue'),
    children: [
      { path: '',            component: () => import('@/pages/public/Home.vue') },
      { path: 'about',       component: () => import('@/pages/public/About.vue') },
      { path: 'services',    component: () => import('@/pages/public/Services.vue') },
      { path: 'pricing',     component: () => import('@/pages/public/Pricing.vue') },
      { path: 'properties',  component: () => import('@/pages/public/Properties.vue') },
      { path: 'hotels',      component: () => import('@/pages/public/Hotels.vue') },
      { path: 'hotels/:id',  component: () => import('@/pages/public/ListingDetail.vue') },
      { path: 'bookings/:id', component: () => import('@/pages/public/BookingConfirmation.vue'), meta: { requiresAuth: true } },
      { path: 'my-bookings', component: () => import('@/pages/public/MyBookings.vue'), meta: { requiresAuth: true } },
      { path: 'marketplace', component: () => import('@/pages/public/Marketplace.vue') },
      { path: 'blog',        component: () => import('@/pages/public/Blog.vue') },
      { path: 'contact',     component: () => import('@/pages/public/Contact.vue') },
      { path: 'help',        component: () => import('@/pages/public/HelpCenter.vue') },
      { path: 'careers',     component: () => import('@/pages/public/Careers.vue') },
      { path: 'privacy',     component: () => import('@/pages/public/Privacy.vue') },
      { path: 'terms',       component: () => import('@/pages/public/Terms.vue') },
    ],
  },

  { path: '/login',    component: () => import('@/portals/auth/LoginView.vue'),    meta: { guest: true } },
  { path: '/change-password', component: () => import('@/portals/auth/ChangePasswordView.vue'), meta: { requiresAuth: true } },
  { path: '/register', component: () => import('@/portals/auth/RegisterView.vue'), meta: { guest: true } },

  // ---------- Tenant ----------
  {
    path: '/tenant',
    component: () => import('@/layouts/TenantLayout.vue'),
    meta: { requiresAuth: true, role: 'tenant' },
    children: [
      { path: '', redirect: '/tenant/dashboard' },
      { path: 'dashboard',    component: () => import('@/portals/tenant/views/Dashboard.vue') },
      { path: 'lease',        component: () => import('@/portals/tenant/views/Lease.vue') },
      { path: 'invoices',     component: () => import('@/portals/tenant/views/Invoices.vue') },
      { path: 'payments',     component: () => import('@/portals/tenant/views/Payments.vue') },
      { path: 'refunds',      component: () => import('@/portals/tenant/views/Refunds.vue') },
      { path: 'maintenance',  component: () => import('@/portals/tenant/views/Maintenance.vue') },
      { path: 'messages',     component: () => import('@/portals/tenant/views/Messages.vue') },
      { path: 'properties',   component: () => import('@/portals/tenant/views/Properties.vue') },
      { path: 'properties/:id', component: () => import('@/portals/tenant/views/PropertyDetail.vue') },
      { path: 'applications', component: () => import('@/portals/tenant/views/Applications.vue') },
      { path: 'notifications',component: () => import('@/portals/tenant/views/Notifications.vue') },
      { path: 'profile',      component: () => import('@/portals/tenant/views/Profile.vue') },
    ],
  },

  // ---------- Landlord ----------
  {
    path: '/landlord',
    component: () => import('@/layouts/LandlordLayout.vue'),
    meta: { requiresAuth: true, role: 'landlord' },
    children: [
      { path: '', redirect: '/landlord/dashboard' },
      { path: 'dashboard',   component: () => import('@/portals/landlord/views/Dashboard.vue') },
      { path: 'properties',  component: () => import('@/portals/landlord/views/Properties.vue') },
      { path: 'units',       component: () => import('@/portals/landlord/views/Units.vue') },
      { path: 'leases',      component: () => import('@/portals/landlord/views/Leases.vue') },
      { path: 'applications', component: () => import('@/portals/landlord/views/Applications.vue') },
      { path: 'renewals',    component: () => import('@/portals/landlord/views/Renewals.vue') },
      { path: 'screening',   component: () => import('@/portals/landlord/views/TenantScreening.vue') },
      { path: 'documents',   component: () => import('@/portals/landlord/views/Documents.vue') },
      { path: 'rent-estimator', component: () => import('@/portals/landlord/views/RentEstimator.vue') },
      { path: 'invoices',    component: () => import('@/portals/landlord/views/Invoices.vue') },
      { path: 'statements',  component: () => import('@/portals/landlord/views/Statements.vue') },
      { path: 'approvals',   component: () => import('@/portals/landlord/views/Approvals.vue') },
      { path: 'refunds',     component: () => import('@/portals/landlord/views/Refunds.vue') },
      { path: 'tax',         component: () => import('@/portals/landlord/views/Tax.vue') },
      { path: 'amenities',   component: () => import('@/portals/landlord/views/Amenities.vue') },
      { path: 'managed',     component: () => import('@/portals/landlord/views/ManagedProperties.vue') },
      { path: 'maintenance', component: () => import('@/portals/landlord/views/Maintenance.vue') },
      { path: 'messages',    component: () => import('@/portals/landlord/views/Messages.vue') },
      { path: 'analytics',   component: () => import('@/portals/landlord/views/Analytics.vue') },
      { path: 'wallet',      component: () => import('@/portals/landlord/views/Wallet.vue') },
      { path: 'profile',     component: () => import('@/portals/landlord/views/Profile.vue') },
    ],
  },

  // ---------- Agency ----------
  {
    path: '/agency',
    component: () => import('@/layouts/AgencyLayout.vue'),
    meta: { requiresAuth: true, agencyOnly: true },
    children: [
      { path: '', redirect: '/agency/dashboard' },
      { path: 'dashboard',  component: () => import('@/portals/agency/views/Dashboard.vue') },
      { path: 'properties', component: () => import('@/portals/agency/views/Properties.vue') },
      { path: 'staff',      component: () => import('@/portals/agency/views/Staff.vue') },
      { path: 'statements', component: () => import('@/portals/agency/views/Statements.vue') },
      { path: 'payouts',    component: () => import('@/portals/agency/views/Payouts.vue') },
      { path: 'expenses',   component: () => import('@/portals/agency/views/Expenses.vue') },
      { path: 'chat',       component: () => import('@/portals/agency/views/Chat.vue') },
      { path: 'audit-log',  component: () => import('@/portals/agency/views/AuditLog.vue') },
      { path: 'profile',    component: () => import('@/portals/agency/views/Profile.vue') },
    ],
  },

  // ---------- Admin ----------
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { requiresAuth: true, role: 'admin' },
    children: [
      { path: '', redirect: '/admin/dashboard' },
      { path: 'dashboard',  component: () => import('@/portals/admin/views/Dashboard.vue') },
      { path: 'users',      component: () => import('@/portals/admin/views/Users.vue') },
      { path: 'kyc',        component: () => import('@/portals/admin/views/KYCReview.vue') },
      { path: 'properties', component: () => import('@/portals/admin/views/Properties.vue') },
      { path: 'agencies',   component: () => import('@/portals/admin/views/Agencies.vue') },
      { path: 'refunds',    component: () => import('@/portals/admin/views/Refunds.vue') },
      { path: 'profile',    component: () => import('@/portals/admin/views/Profile.vue') },
      { path: 'reconciliation', component: () => import('@/portals/admin/views/Reconciliation.vue') },
      { path: 'review-queue', component: () => import('@/portals/admin/views/ReviewQueue.vue') },
      { path: 'portfolio',  component: () => import('@/portals/admin/views/Portfolio.vue') },
      { path: 'tax-settings', component: () => import('@/portals/admin/views/TaxSettings.vue') },
      { path: 'listings',   component: () => import('@/portals/admin/views/Listings.vue') },
      { path: 'payments',   component: () => import('@/portals/admin/views/Payments.vue') },
      { path: 'paybill',    component: () => import('@/portals/admin/views/PaybillReconciliation.vue') },
      { path: 'blacklist',  component: () => import('@/portals/admin/views/Blacklist.vue') },
      { path: 'analytics',  component: () => import('@/portals/admin/views/Analytics.vue') },
    ],
  },

  // ---------- Service Provider ----------
  {
    path: '/provider',
    component: () => import('@/layouts/ProviderLayout.vue'),
    meta: { requiresAuth: true, role: 'service_provider' },
    children: [
      { path: '', redirect: '/provider/dashboard' },
      { path: 'dashboard',    component: () => import('@/portals/service-provider/views/Dashboard.vue') },
      { path: 'jobs',         component: () => import('@/portals/service-provider/views/Jobs.vue') },
      { path: 'my-jobs',      component: () => import('@/portals/service-provider/views/MyJobs.vue') },
      { path: 'quotes',       component: () => import('@/portals/service-provider/views/Quotes.vue') },
      { path: 'messages',     component: () => import('@/portals/service-provider/views/Messages.vue') },
      { path: 'wallet',       component: () => import('@/portals/service-provider/views/Wallet.vue') },
      { path: 'profile',      component: () => import('@/portals/service-provider/views/Profile.vue') },
    ],
  },

  // ---------- Hotel/BnB ----------
  {
    path: '/hotel',
    component: () => import('@/layouts/HotelLayout.vue'),
    meta: { requiresAuth: true, role: 'hotel_owner' },
    children: [
      { path: '', redirect: '/hotel/dashboard' },
      { path: 'dashboard',  component: () => import('@/portals/hotel/views/Dashboard.vue') },
      { path: 'listings',   component: () => import('@/portals/hotel/views/Listings.vue') },
      { path: 'rooms',      component: () => import('@/portals/hotel/views/Rooms.vue') },
      { path: 'calendar',   component: () => import('@/portals/hotel/views/Calendar.vue') },
      { path: 'bookings',   component: () => import('@/portals/hotel/views/Bookings.vue') },
      { path: 'statements', component: () => import('@/portals/hotel/views/Statements.vue') },
      { path: 'managed',    component: () => import('@/portals/hotel/views/ManagedProperties.vue') },
      { path: 'messages',   component: () => import('@/portals/hotel/views/Messages.vue') },
      { path: 'wallet',     component: () => import('@/portals/hotel/views/Wallet.vue') },
      { path: 'profile',    component: () => import('@/portals/hotel/views/Profile.vue') },
    ],
  },

  { path: '/:pathMatch(.*)*', component: () => import('@/portals/auth/NotFound.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

// Navigation guard
router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (to.meta.guest) {
    if (getAccessToken() && !auth.user) await auth.fetchMe()
    if (auth.user) return safeRedirect(to.query.redirect) ?? roleHome(auth.user.role, auth.isAgencyStaff)
    return true
  }

  if (to.meta.requiresAuth) {
    // Remember where the person was going so signing in lands them there (e.g. the house they wanted to rent).
    const toLogin = { path: '/login', query: { redirect: to.fullPath } }
    if (!getAccessToken()) return toLogin
    if (!auth.user) await auth.fetchMe()
    if (!auth.user) return toLogin

    // An admin-issued temporary password must be replaced before anything else is reachable.
    if (auth.user.must_change_password && to.path !== '/change-password') return '/change-password'
    if (!auth.user.must_change_password && to.path === '/change-password') return roleHome(auth.user.role, auth.isAgencyStaff)

    if (to.meta.agencyOnly) {
      if (!auth.agencies.length) await auth.fetchAgencies()
      if (!auth.isAgencyStaff) {
        // Agencies are registered by a platform administrator only, so there is no
        // self-service bootstrap screen: every agency route requires real membership.
        return roleHome(auth.user.role, false)
      }
      return true
    }

    if (to.meta.role && auth.user.role !== to.meta.role) return roleHome(auth.user.role, auth.isAgencyStaff)
  }

  return true
})

/** Only follow same-site paths from ?redirect= (never another website, never back to a guest page). */
function safeRedirect(raw: unknown): string | null {
  const p = Array.isArray(raw) ? raw[0] : raw
  if (typeof p !== 'string' || !p.startsWith('/') || p.startsWith('//') || p.includes('://') || p.startsWith('/login') || p.startsWith('/register')) return null
  return p
}

function roleHome(role: string, isAgencyStaff = false) {
  if (isAgencyStaff) return '/agency/dashboard'
  const map: Record<string, string> = {
    tenant: '/tenant/dashboard',
    landlord: '/landlord/dashboard',
    admin: '/admin/dashboard',
    service_provider: '/provider/dashboard',
    hotel_owner: '/hotel/dashboard',
  }
  return map[role] ?? '/login'
}

export default router
export { roleHome, safeRedirect }
