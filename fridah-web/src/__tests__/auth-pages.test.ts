import { describe, it, expect } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { defineComponent, h } from 'vue'
import { i18n } from '@/i18n'
import LoginView from '@/portals/auth/LoginView.vue'
import RegisterView from '@/portals/auth/RegisterView.vue'

const Stub = defineComponent({ render: () => h('div') })
async function setup(comp: any) {
  const pinia = createPinia(); setActivePinia(pinia)
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:p(.*)*', component: Stub }] }); router.push('/login'); await router.isReady()
  return mount(comp, { global: { plugins: [pinia, router, i18n] } })
}

describe('glass auth pages', () => {
  it('login shows the form, a back button, and toggles password visibility', async () => {
    const w = await setup(LoginView)
    expect(w.find('.fx-back').exists()).toBe(true)
    const pw = w.find('input[autocomplete="current-password"]')
    expect(pw.attributes('type')).toBe('password')
    await w.find('.fx-pw button').trigger('click')
    expect(pw.attributes('type')).toBe('text')
    expect(document.documentElement.dataset.skin).toBe('sand')
  })

  it('register rates password strength and blocks mismatched passwords', async () => {
    const w = await setup(RegisterView)
    await w.find('input[autocomplete="new-password"]').setValue('Abcdef12!')
    expect(w.findAll('.fx-meter i').filter((i) => i.attributes('style')).length).toBe(4)
    await w.findAll('input[autocomplete="new-password"]')[1].setValue('different')
    await flushPromises()
    expect(w.text()).toContain('Passwords don’t match')
    expect(w.find('.fx-submit').attributes('disabled')).toBeDefined()
  })
})
