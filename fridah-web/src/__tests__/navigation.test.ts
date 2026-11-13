/**
 * Integration tests: the real router + real auth store + real guards, with only the network mocked.
 * They exercise the navigation rules behind the account flows (admin-registered agencies, forced
 * password change, role separation) the way a browser session would.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/api/services', async (importOriginal) => {
  const real: any = await importOriginal()
  return {
    ...real,
    authApi: { ...real.authApi, me: vi.fn(), login: vi.fn(), logout: vi.fn() },
    agencyApi: { ...real.agencyApi, list: vi.fn() },
  }
})

import { authApi, agencyApi } from '@/api/services'
import { setTokens, clearTokens } from '@/api/client'
import router from '@/router'
import { useAuthStore } from '@/stores/auth'
import { safeRedirect } from '@/router'

const user = (role: string, extra: Record<string, unknown> = {}) => ({ id: 'u1', role, must_change_password: false, ...extra })
const signedInAs = (u: any, agencies: any[] = []) => {
  setTokens('access', 'refresh')
  ;(authApi.me as any).mockResolvedValue({ data: { data: u } })
  // The HTTP client's interceptor wraps paginated bodies as { success, data: { results } }; mock that final shape.
  ;(agencyApi.list as any).mockResolvedValue({ data: { success: true, data: { results: agencies } } })
}
const go = async (path: string) => { await router.push(path).catch(() => {}); return router.currentRoute.value.path }

window.scrollTo = vi.fn() as any

beforeEach(async () => {
  setActivePinia(createPinia())
  clearTokens()
  vi.clearAllMocks()
  ;(agencyApi.list as any).mockResolvedValue({ data: { success: true, data: { results: [] } } })
  await router.replace('/login').catch(() => {})
})

describe('signed-out visitors', () => {
  it('are sent to the login page from every portal', async () => {
    for (const path of ['/tenant/dashboard', '/landlord/dashboard', '/agency/dashboard', '/admin/agencies']) {
      expect(await go(path)).toBe('/login')
    }
  })

  it('cannot reach the forced password screen either', async () => {
    expect(await go('/change-password')).toBe('/login')
  })
})

describe('nobody can become an agency', () => {
  it.each(['tenant', 'landlord', 'service_provider', 'hotel_owner'])('%s is bounced from the agency portal to their own home', async (role) => {
    signedInAs(user(role))
    const home = { tenant: '/tenant/dashboard', landlord: '/landlord/dashboard',
      service_provider: '/provider/dashboard', hotel_owner: '/hotel/dashboard' }[role]
    expect(await go('/agency/dashboard')).toBe(home)
    expect(await go('/agency/staff')).toBe(home)
  })

  it('a member of an admin-registered agency is taken to the agency portal', async () => {
    signedInAs(user('landlord'), [{ id: 'a1', name: 'Prime Property Managers' }])
    expect(await go('/agency/dashboard')).toBe('/agency/dashboard')
    expect(await go('/login')).toBe('/agency/dashboard')   // already signed in: guest pages bounce home
  })
})

describe('role separation', () => {
  it('a tenant cannot open the admin agency page', async () => {
    signedInAs(user('tenant'))
    expect(await go('/admin/agencies')).toBe('/tenant/dashboard')
  })

  it('a landlord cannot open admin pages', async () => {
    signedInAs(user('landlord'))
    expect(await go('/admin/review-queue')).toBe('/landlord/dashboard')
    expect(await go('/admin/tax-settings')).toBe('/landlord/dashboard')
  })

  it('an admin can open the agency, review-queue and portfolio pages', async () => {
    signedInAs(user('admin'))
    expect(await go('/admin/agencies')).toBe('/admin/agencies')
    expect(await go('/admin/review-queue')).toBe('/admin/review-queue')
    expect(await go('/admin/portfolio')).toBe('/admin/portfolio')
  })

  it('a landlord can open their approvals, tax and amenities pages', async () => {
    signedInAs(user('landlord'))
    for (const p of ['/landlord/approvals', '/landlord/tax', '/landlord/amenities']) expect(await go(p)).toBe(p)
  })
})

describe('admin-issued temporary password', () => {
  it('traps the user on the change-password screen until it is changed', async () => {
    signedInAs(user('landlord', { must_change_password: true }), [{ id: 'a1' }])
    for (const path of ['/agency/dashboard', '/landlord/dashboard', '/tenant/dashboard']) {
      expect(await go(path)).toBe('/change-password')
    }
  })

  it('releases the user to their home once the flag is cleared', async () => {
    signedInAs(user('landlord', { must_change_password: true }), [{ id: 'a1' }])
    expect(await go('/agency/dashboard')).toBe('/change-password')
    const auth = useAuthStore()
    ;(authApi.me as any).mockResolvedValue({ data: { data: user('landlord', { must_change_password: false }) } })
    await auth.fetchMe()
    await auth.fetchAgencies()
    expect(await go('/agency/dashboard')).toBe('/agency/dashboard')
    expect(await go('/change-password')).toBe('/agency/dashboard')   // nothing left to change
  })

  it('a normal user who opens the change-password screen is sent home', async () => {
    signedInAs(user('tenant'))
    expect(await go('/change-password')).toBe('/tenant/dashboard')
  })
})


describe('coming back to the house you wanted', () => {
  it('a signed-out visitor who opens a house is sent to sign in, remembering which house', async () => {
    expect(await go('/tenant/properties/abc-123')).toBe('/login')
    expect(router.currentRoute.value.query.redirect).toBe('/tenant/properties/abc-123')
  })

  it('after signing in the tenant is taken to that house, not just their dashboard', async () => {
    signedInAs(user('tenant'))
    expect(await go('/login?redirect=/tenant/properties/abc-123')).toBe('/tenant/properties/abc-123')
  })

  it('a signed-in tenant can open a house page directly', async () => {
    signedInAs(user('tenant'))
    expect(await go('/tenant/properties/abc-123')).toBe('/tenant/properties/abc-123')
  })

  it('only follows same-site redirect targets', () => {
    expect(safeRedirect('/tenant/properties/1')).toBe('/tenant/properties/1')
    for (const bad of ['https://evil.example', '//evil.example', 'javascript:alert(1)', '/login', '/register', undefined, 42]) expect(safeRedirect(bad as any)).toBeNull()
  })
})
