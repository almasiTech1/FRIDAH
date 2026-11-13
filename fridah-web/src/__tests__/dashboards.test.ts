/**
 * Smoke tests for the glass dashboards: every portal home renders its KPI tiles from the offline
 * fallback data, the shared shell sets the active skin, and the command palette / skin switcher work.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { nextTick, defineComponent, h } from 'vue'
import { LayoutDashboard, Users } from 'lucide-vue-next'

vi.mock('@/api/services', async (importOriginal) => {
  const real: any = await importOriginal()
  const fail = () => Promise.reject(new Error('offline'))
  return {
    ...real,
    analyticsApi: { ...real.analyticsApi, adminDashboard: fail, landlordDashboard: fail, tenantDashboard: fail, hotelDashboard: fail, serviceProviderDashboard: () => Promise.resolve({ data: { data: { active_jobs: 2, completed_jobs: 9, pending_quotes: 1, accepted_quotes: 1, wallet_balance: 5000, available_open_jobs: 4, earnings_by_month: Array.from({ length: 12 }, (_, i) => ({ month: `2026-${String(i + 1).padStart(2, '0')}`, amount: (i + 1) * 500 })) } } }) },
    rentalsApi: { ...real.rentalsApi, leases: fail, invoices: fail },
    notificationsApi: { ...real.notificationsApi, unreadCount: () => Promise.resolve({ data: { data: { unread_count: 3 } } }), list: () => Promise.resolve({ data: { data: { results: [] } } }) },
    agencyApi: {
      ...real.agencyApi,
      statements: () => Promise.resolve({ data: { data: { results: [{ id: 's1', status: 'draft' }] } } }),
      payouts: () => Promise.resolve({ data: { data: { results: [{ id: 'p1', status: 'pending' }] } } }),
      dashboard: () => Promise.resolve({ data: { data: { collected_by_month: Array.from({ length: 12 }, (_, i) => ({ month: `2026-${String(i + 1).padStart(2, '0')}`, amount: (i + 1) * 1000 })), summary: { occupied_units: 8, vacant_units: 2, gross_rent_collected_this_month: '12000' }, properties: [{ property_name: 'Karen Heights', collected_this_month: '120000' }, { property_name: 'Lavington Court', collected_this_month: '90000' }] } } }),
    },
  }
})

import { i18n } from '@/i18n'
import { useAuthStore } from '@/stores/auth'
import { useSkinStore, SKINS } from '@/stores/skin'
import PortalLayout from '@/layouts/PortalLayout.vue'
import AdminDash from '@/portals/admin/views/Dashboard.vue'
import LandlordDash from '@/portals/landlord/views/Dashboard.vue'
import TenantDash from '@/portals/tenant/views/Dashboard.vue'
import AgencyDash from '@/portals/agency/views/Dashboard.vue'
import HotelDash from '@/portals/hotel/views/Dashboard.vue'
import ProviderDash from '@/portals/service-provider/views/Dashboard.vue'

const Stub = defineComponent({ render: () => h('div') })
const makeRouter = (path = '/') => {
  const r = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:p(.*)*', component: Stub }] })
  r.push(path)
  return r
}
const mountWith = async (comp: any, path: string, props: any = {}, slots: any = {}) => {
  const pinia = createPinia(); setActivePinia(pinia)
  const router = makeRouter(path); await router.isReady()
  const auth = useAuthStore()
  ;(auth as any).user = { id: 'u1', first_name: 'Jerald', last_name: 'K', email: 'j@x.ke', role: 'landlord', username: 'j', kyc_status: 'verified' }
  ;(auth as any).agencies = [{ id: 'a1', name: 'Prime Property Managers', managed_properties_count: 12, owners_count: 5 }]
  const w = mount(comp, { props, slots, global: { plugins: [pinia, router, i18n], directives: { spot: {} }, stubs: { Teleport: true } }, attachTo: document.body })
  await flushPromises(); await nextTick()
  return { w, router }
}

beforeEach(() => { localStorage.clear(); document.documentElement.removeAttribute('data-skin') })

describe('portal dashboards', () => {
  it.each([
    ['admin', AdminDash, '/admin/dashboard', 'Active people'],
    ['landlord', LandlordDash, '/landlord/dashboard', 'Collected (month)'],
    ['tenant', TenantDash, '/tenant/dashboard', 'Pending balance'],
    ['agency', AgencyDash, '/agency/dashboard', 'Managed properties'],
    ['hotel', HotelDash, '/hotel/dashboard', 'Bookings (month)'],
    ['provider', ProviderDash, '/provider/dashboard', 'Active jobs'],
  ])('%s home renders its tiles and a greeting', async (_n, comp, path, label) => {
    const { w } = await mountWith(comp, path)
    expect(w.text()).toContain(label)
    expect(w.find('.fx-head h2').text()).toMatch(/Good (morning|afternoon|evening), (Jerald|there)/)
    expect(w.findAll('.fx-kpi').length).toBeGreaterThan(2)
  })

  it('charts respond to the range toggle and bar selection', async () => {
    const { w } = await mountWith(LandlordDash, '/landlord/dashboard')
    expect(w.findAll('.fx-bar-col')).toHaveLength(6)
    await w.findAll('.fx-seg button')[2].trigger('click')
    expect(w.findAll('.fx-bar-col')).toHaveLength(9)
    await w.findAll('.fx-bar-col')[1].trigger('click')
    expect(w.findAll('.fx-bar-col')[1].classes()).toContain('sel')
  })

  it('agency shows a real month-by-month chart when the API provides history', async () => {
    const { w } = await mountWith(AgencyDash, '/agency/dashboard')
    expect(w.text()).toContain('Rent collected, month by month')
    expect(w.findAll('.fx-bar-tip').map((t) => t.text()).slice(0, 6)).toEqual(['KES 7K', 'KES 8K', 'KES 9K', 'KES 10K', 'KES 11K', 'KES 12K'])
  })

  it('service provider sees real monthly earnings', async () => {
    const { w } = await mountWith(ProviderDash, '/provider/dashboard')
    expect(w.text()).toContain('Actual wallet credits after commission')
    expect(w.findAll('.fx-bar-tip').map((t) => t.text())[5]).toBe('KES 6K')
  })

  it('the donut legend highlights a slice on hover', async () => {
    const { w } = await mountWith(AdminDash, '/admin/dashboard')
    await w.findAll('.fx-legend button')[0].trigger('mouseenter')
    expect(w.find('.fx-legend button.on').exists()).toBe(true)
  })

  it('to-do items can be ticked off', async () => {
    const { w } = await mountWith(AdminDash, '/admin/dashboard')
    const first = w.find('.fx-task'); await first.trigger('click')
    expect(first.classes()).toContain('done')
  })
})

describe('portal shell', () => {
  const nav = [{ to: '/admin/dashboard', label: 'Dashboard', icon: LayoutDashboard }, { to: '/admin/users', label: 'Users', icon: Users }]

  it('applies the portal default skin, then remembers a chosen one', async () => {
    const { w } = await mountWith(PortalLayout, '/admin/dashboard', { portalLabel: 'Admin Portal', navItems: nav })
    expect(document.documentElement.dataset.skin).toBe('aurora')
    const skin = useSkinStore(); skin.set('lime')
    expect(document.documentElement.dataset.skin).toBe('lime')
    expect(document.documentElement.dataset.mode).toBe('light')
    expect(localStorage.getItem('fridah-skin')).toBe('lime')
    w.unmount()
  })

  it('every skin has a light/dark mode and a nav layout', () => {
    expect(SKINS).toHaveLength(6)
    for (const s of SKINS) { expect(['light', 'dark']).toContain(s.mode); expect(['sidebar', 'topnav', 'rail']).toContain(s.nav) }
  })

  it('Ctrl+K opens the command palette and Enter navigates', async () => {
    const { w, router } = await mountWith(PortalLayout, '/admin/dashboard', { portalLabel: 'Admin Portal', navItems: nav })
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true })); await nextTick()
    const input = document.querySelector('.fx-cmdk input') as HTMLInputElement
    expect(input).toBeTruthy()
    input.value = 'users'; input.dispatchEvent(new Event('input')); await nextTick()
    ;(document.querySelector('.fx-cmdk') as HTMLElement).dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true })); await flushPromises()
    expect(router.currentRoute.value.path).toBe('/admin/users')
    w.unmount()
  })
})
