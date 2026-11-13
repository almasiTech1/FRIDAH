import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { defineComponent, h } from 'vue'

const months = ['2026-03', '2026-04', '2026-05', '2026-06', '2026-07', '2026-08', '2026-09', '2026-10', '2026-11']
const history = months.map((m, i) => ({ month: m, amount: (i + 1) * 10000 }))
const base = { total_properties: 2, total_units: 10, occupied_units: 8, vacant_units: 2, active_leases: 8, overdue_invoices_count: 0, overdue_amount: 0, collected_this_month: 90000, open_maintenance_requests: 0, wallet_balance: 5000 }
let payload: any = { ...base, collected_by_month: history }

vi.mock('@/api/services', async (orig) => {
  const real: any = await orig()
  return { ...real, analyticsApi: { ...real.analyticsApi, landlordDashboard: () => Promise.resolve({ data: { data: payload } }) } }
})
import { i18n } from '@/i18n'
import LandlordDash from '@/portals/landlord/views/Dashboard.vue'

const Stub = defineComponent({ render: () => h('div') })
async function mountDash() {
  const pinia = createPinia(); setActivePinia(pinia)
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:p(.*)*', component: Stub }] }); router.push('/landlord/dashboard'); await router.isReady()
  const w = mount(LandlordDash, { global: { plugins: [pinia, router, i18n], directives: { spot: {} } } })
  await flushPromises(); return w
}

describe('dashboard trend data', () => {
  it('plots the real monthly figures from the API and says so', async () => {
    payload = { ...base, collected_by_month: history }
    const w = await mountDash()
    expect(w.text()).toContain('Actual payments received')
    const tips = w.findAll('.fx-bar-tip').map((t) => t.text())
    expect(tips).toEqual(['KES 40K', 'KES 50K', 'KES 60K', 'KES 70K', 'KES 80K', 'KES 90K']) // last 6 months, not an estimate
  })
  it('falls back to a labelled estimate when the API has no history', async () => {
    payload = { ...base }
    const w = await mountDash()
    expect(w.text()).toContain('Estimated trend')
    expect(w.findAll('.fx-bar-col')).toHaveLength(6)
  })
})
