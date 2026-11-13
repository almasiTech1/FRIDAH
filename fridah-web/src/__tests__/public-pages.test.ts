import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { defineComponent, h } from 'vue'

const props = [1, 2, 3].map((i) => ({ id: `p${i}`, name: `Home ${i}`, town: 'Nairobi', county: 'Nairobi', property_type: 'apartment', min_rent: 20000 * i, vacant_units_count: i, latitude: -1.2, longitude: 36.8 }))
vi.mock('@/api/services', async (orig) => {
  const real: any = await orig()
  const ok = (results: any[]) => Promise.resolve({ data: { data: { results } } })
  return { ...real, propertiesApi: { ...real.propertiesApi, publicList: () => ok(props), list: () => ok(props), search: () => ok(props) },
    bookingsApi: { ...real.bookingsApi, listings: () => ok([{ id: 'h1', name: 'Villa One', listing_type: 'bnb', town: 'Diani', county: 'Kwale', amenities: ['WiFi'], min_price: 9000, rating: 4.5 }]) } }
})
import { i18n } from '@/i18n'
import Properties from '@/pages/public/Properties.vue'
import Hotels from '@/pages/public/Hotels.vue'

const Stub = defineComponent({ render: () => h('div') })
beforeEach(() => localStorage.clear())

async function mountProps(role: string | null) {
  const pinia = createPinia(); setActivePinia(pinia)
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:p(.*)*', component: Stub }] }); router.push('/properties'); await router.isReady()
  if (role) { const { useAuthStore } = await import('@/stores/auth'); (useAuthStore() as any).user = { id: 'u1', role, first_name: 'A', last_name: 'B' } }
  const w = mount(Properties, { global: { plugins: [pinia, router, i18n], directives: { reveal: {} }, stubs: { GoogleMapView: true } } })
  await flushPromises(); return { w, router }
}

describe('opening a listed house', () => {
  it('a signed-in tenant goes straight to the house page where they can apply', async () => {
    const { w, router } = await mountProps('tenant')
    await w.findAll('.group')[0].trigger('click'); await flushPromises()
    expect(router.currentRoute.value.path).toBe('/tenant/properties/p1')
  })
  it('a visitor is asked to sign in and returns to the same house afterwards', async () => {
    const { w, router } = await mountProps(null)
    await w.findAll('.group')[1].trigger('click'); await flushPromises()
    expect(router.currentRoute.value.path).toBe('/login')
    expect(router.currentRoute.value.query.redirect).toBe('/tenant/properties/p2')
  })
  it('a landlord is told to use a tenant account instead of being bounced away', async () => {
    const { w, router } = await mountProps('landlord')
    await w.findAll('.group')[0].trigger('click'); await flushPromises()
    expect(router.currentRoute.value.path).toBe('/properties')
  })
})

describe('Properties page', () => {
  it('lets visitors save homes and filter to saved ones', async () => {
    const pinia = createPinia(); setActivePinia(pinia)
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:p(.*)*', component: Stub }] }); router.push('/properties'); await router.isReady()
    const w = mount(Properties, { global: { plugins: [pinia, router, i18n], directives: { reveal: {} }, stubs: { GoogleMapView: true } } })
    await flushPromises()
    const hearts = w.findAll('.fx-fav')
    expect(hearts).toHaveLength(3)
    await hearts[1].trigger('click')
    expect(w.findAll('.fx-fav.on')).toHaveLength(1)
    expect(w.text()).toContain('Saved (1)')
    await w.findAll('.fx-look')[0].trigger('click')
    expect(w.findAll('.fx-fav')).toHaveLength(1)
    expect(JSON.parse(localStorage.getItem('fridah-saved-property')!)).toEqual(['p2'])
  })
})


describe('hotel cards', () => {
  it('Book Now opens the listing (where the booking form is), never the register page', async () => {
    const pinia = createPinia(); setActivePinia(pinia)
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:p(.*)*', component: Stub }] }); router.push('/hotels'); await router.isReady()
    const { useAuthStore } = await import('@/stores/auth'); (useAuthStore() as any).user = { id: 'u1', role: 'tenant', first_name: 'A', last_name: 'B' }
    const w = mount(Hotels, { global: { plugins: [pinia, router, i18n], directives: { reveal: {} }, stubs: { GoogleMapView: true } } })
    await flushPromises()
    const book = w.findAll('a').find((a) => a.text() === 'Book Now')!
    expect(book.attributes('href')).toBe('/hotels/h1')
  })
})
