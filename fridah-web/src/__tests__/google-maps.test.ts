import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'

// ── Fakes for Google's Places library and the map components (no network, no real Google script) ──
class FakeAutocomplete extends HTMLElement {
  placeholder = ''; value = ''; options: any
  constructor(options?: any) { super(); this.options = options }
}
if (!customElements.get('fake-place-ac')) customElements.define('fake-place-ac', FakeAutocomplete)
let lastElement: FakeAutocomplete | null = null
const places = { PlaceAutocompleteElement: class extends FakeAutocomplete { constructor(o?: any) { super(o); lastElement = this } } }
if (!customElements.get('fake-place-ac-2')) customElements.define('fake-place-ac-2', places.PlaceAutocompleteElement as any)

vi.mock('@/composables/useGoogleMapsApi', () => ({
  hasGoogleMapsApiKey: () => (import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string | undefined) === 'test-key',
  usePlacesLibrary: () => Promise.resolve(places),
  useGeometryLibrary: () => null,
}))
vi.mock('vue3-google-map', () => ({
  GoogleMap: defineComponent({ name: 'GoogleMap', emits: ['click'], setup: (_p, { slots, emit }) => () => h('div', { class: 'gm', onClick: () => emit('click', { latLng: { lat: () => -1.2920659123, lng: () => 36.8219462456 } }) }, slots.default?.()) }),
  Marker: defineComponent({ name: 'Marker', emits: ['dragend'], setup: (_p, { emit }) => () => h('i', { class: 'mk', onClick: () => emit('dragend', { latLng: { lat: () => -1.3000001, lng: () => 36.9000009 } }) }) }),
  MarkerCluster: defineComponent({ setup: (_p, { slots }) => () => h('div', slots.default?.()) }),
  InfoWindow: defineComponent({ setup: (_p, { slots }) => () => h('div', slots.default?.()) }),
}))

import AddressAutocomplete from '@/components/public/AddressAutocomplete.vue'
import LocationMap from '@/components/public/LocationMap.vue'
import LocationPicker from '@/components/public/LocationPicker.vue'
import { createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'

const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:p(.*)*', component: { render: () => h('div') } }] })
const plugins = [createPinia(), router]

beforeEach(() => { lastElement = null })
afterEach(() => vi.unstubAllEnvs())

describe('address search (Google Places, current widget)', () => {
  it('uses the new place-search widget limited to Kenya, and reports the chosen place with rounded coordinates', async () => {
    vi.stubEnv('VITE_GOOGLE_MAPS_API_KEY', 'test-key')
    const w = mount(AddressAutocomplete, { props: { label: 'Address' }, attachTo: document.body })
    await flushPromises()
    expect(lastElement).toBeTruthy()
    expect(lastElement!.options.includedRegionCodes).toEqual(['ke'])
    expect(w.element.contains(lastElement)).toBe(true)

    const place = {
      fetchFields: vi.fn().mockResolvedValue(undefined), formattedAddress: 'Lavington, Nairobi, Kenya',
      location: { lat: () => -1.2920659123456, lng: () => 36.8219462456789 },
      addressComponents: [{ longText: 'Nairobi County', types: ['administrative_area_level_1'] }, { longText: 'Lavington', types: ['locality'] }],
    }
    const ev = new Event('gmp-select'); (ev as any).placePrediction = { toPlace: () => place }
    lastElement!.dispatchEvent(ev); await flushPromises()

    expect(place.fetchFields).toHaveBeenCalledWith({ fields: ['formattedAddress', 'location', 'addressComponents'] })
    expect(w.emitted('place-selected')![0][0]).toEqual({ formattedAddress: 'Lavington, Nairobi, Kenya', lat: -1.292066, lng: 36.821946, county: 'Nairobi County', town: 'Lavington' })
    expect(w.emitted('update:modelValue')!.at(-1)).toEqual(['Lavington, Nairobi, Kenya'])
    w.unmount()
  })

  it('falls back to a plain box when Google refuses the request (for example the Places API is not enabled)', async () => {
    vi.stubEnv('VITE_GOOGLE_MAPS_API_KEY', 'test-key')
    const w = mount(AddressAutocomplete, { attachTo: document.body })
    await flushPromises()
    lastElement!.dispatchEvent(new Event('gmp-error')); await flushPromises()
    expect(w.find('input.input').exists()).toBe(true)
    expect(w.text()).toContain('Address search is unavailable right now')
    await w.find('input.input').setValue('Karen')
    expect(w.emitted('update:modelValue')!.at(-1)).toEqual(['Karen'])
    w.unmount()
  })

  it('works as a normal text box when no key is set', async () => {
    vi.stubEnv('VITE_GOOGLE_MAPS_API_KEY', '')
    const w = mount(AddressAutocomplete)
    await flushPromises()
    expect(w.find('input.input').exists()).toBe(true)
    expect(w.text()).toContain('API key not configured')
  })
})

describe('location on detail pages', () => {
  it('shows the map and directions for a pinned place', () => {
    vi.stubEnv('VITE_GOOGLE_MAPS_API_KEY', 'test-key')
    const w = mount(LocationMap, { props: { lat: '-1.292066', lng: '36.821946', title: 'Lavington Court', addressText: 'Lavington, Nairobi' }, global: { plugins } })
    expect(w.find('.gm').exists()).toBe(true)
    const links = w.findAll('a').map((a) => a.attributes('href'))
    expect(links).toContain('https://www.google.com/maps/dir/?api=1&destination=-1.292066,36.821946')
    expect(links).toContain('https://www.google.com/maps/search/?api=1&query=-1.292066,36.821946')
  })
  it('still gives people directions from the address when there is no key or no pin', () => {
    vi.stubEnv('VITE_GOOGLE_MAPS_API_KEY', '')
    const w = mount(LocationMap, { props: { lat: null, lng: null, addressText: 'Westlands, Nairobi' }, global: { plugins } })
    expect(w.find('.gm').exists()).toBe(false)
    expect(w.text()).toContain('Westlands, Nairobi')
    expect(w.findAll('a')[0].attributes('href')).toBe('https://www.google.com/maps/dir/?api=1&destination=Westlands%2C%20Nairobi')
  })
  it('ignores impossible coordinates and shows nothing when there is nothing to show', () => {
    vi.stubEnv('VITE_GOOGLE_MAPS_API_KEY', 'test-key')
    const bad = mount(LocationMap, { props: { lat: 500, lng: 36.8, addressText: 'Karen' }, global: { plugins } })
    expect(bad.find('.gm').exists()).toBe(false)
    expect(bad.findAll('a')[0].attributes('href')).toContain('destination=Karen')
    expect(mount(LocationMap, { props: {}, global: { plugins } }).html()).toBe('<!--v-if-->')
  })
})

describe('setting the pin by hand', () => {
  it('clicking the map or dragging the pin reports rounded coordinates', async () => {
    vi.stubEnv('VITE_GOOGLE_MAPS_API_KEY', 'test-key')
    const w = mount(LocationPicker, { props: { lat: null, lng: null } })
    expect(w.text()).toContain('No pin yet')
    await w.find('.gm').trigger('click')
    expect(w.emitted('update')![0][0]).toEqual({ lat: -1.292066, lng: 36.821946 })
    await w.setProps({ lat: -1.292066, lng: 36.821946 })
    expect(w.text()).toContain('Pinned at -1.29207, 36.82195')
    await w.find('.mk').trigger('click')                               // drag end
    expect(w.emitted('update')![1][0]).toEqual({ lat: -1.3, lng: 36.900001 })
  })
  it('is hidden when there is no API key (the form still works with typed details)', () => {
    vi.stubEnv('VITE_GOOGLE_MAPS_API_KEY', '')
    expect(mount(LocationPicker, { props: {} }).html()).toBe('<!--v-if-->')
  })
})
