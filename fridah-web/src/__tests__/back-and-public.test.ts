import { describe, it, expect, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { defineComponent, h } from 'vue'
import { i18n } from '@/i18n'
import BackButton from '@/components/ui/BackButton.vue'
import DashboardShowcase from '@/components/public/DashboardShowcase.vue'

const Stub = defineComponent({ render: () => h('div') })
const mk = () => createRouter({ history: createMemoryHistory(), routes: [{ path: '/:p(.*)*', component: Stub }] })

describe('BackButton', () => {
  beforeEach(() => window.history.replaceState({}, ''))

  it('goes to the fallback when there is no previous page', async () => {
    const router = mk(); router.push('/tenant/invoices'); await router.isReady()
    const w = mount(BackButton, { props: { fallback: '/tenant/dashboard' }, global: { plugins: [router] } })
    await w.find('button').trigger('click'); await flushPromises()
    expect(router.currentRoute.value.path).toBe('/tenant/dashboard')
  })

  it('uses browser history when there is one', async () => {
    const router = mk(); router.push('/a'); await router.isReady()
    const spy = vi_spy(router)
    window.history.replaceState({ back: '/a' }, '')
    const w = mount(BackButton, { global: { plugins: [router] } })
    await w.find('button').trigger('click')
    expect(spy.called).toBe(true)
  })
})
function vi_spy(router: any) { const o = { called: false }; router.back = () => { o.called = true }; return o }

describe('public dashboard showcase', () => {
  it('renders, switches portal and look', async () => {
    const pinia = createPinia(); setActivePinia(pinia); const router = mk(); router.push('/'); await router.isReady()
    const w = mount(DashboardShowcase, { global: { plugins: [pinia, router, i18n], directives: { reveal: {}, spot: {} } } })
    expect(w.text()).toContain('Rent collected')
    await w.findAll('.fx-seg button').find((b) => b.text() === 'Hotel')!.trigger('click')
    expect(w.text()).toContain('Hello, Barbara')
    await w.findAll('.fx-look')[3].trigger('click')
    expect(document.documentElement.dataset.skin).toBe('lime')
  })
})
