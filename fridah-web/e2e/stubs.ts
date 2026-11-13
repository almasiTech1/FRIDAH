import type { Page, Route } from '@playwright/test'

export type Handler = (body: any, url: URL) => { status?: number; json: unknown } | Promise<{ status?: number; json: unknown }>
export type Routes = Record<string, Handler>   // key: "METHOD /path/" relative to /api/v1

/** Answer every API call from `routes`; anything unlisted fails loudly so a missing stub is obvious. */
export async function stubApi(page: Page, routes: Routes) {
  const seen: { method: string; path: string; body: any }[] = []
  await page.route(/\/api\/v1\//, async (route: Route) => {
    const req = route.request()
    const url = new URL(req.url())
    const path = url.pathname.replace(/^.*\/api\/v1/, '')
    const body = req.postData() ? safeJson(req.postData()!) : undefined
    seen.push({ method: req.method(), path, body })
    const handler = routes[`${req.method()} ${path}`]
    if (!handler) return route.fulfill({ status: 599, json: { success: false, error: { message: `No stub for ${req.method()} ${path}` } } })
    const out = await handler(body, url)
    return route.fulfill({ status: out.status ?? 200, json: out.json })
  })
  return seen
}

const safeJson = (s: string) => { try { return JSON.parse(s) } catch { return s } }

export const ok = (data: unknown) => ({ json: { success: true, data } })
export const page_ = (results: unknown[]) => ({ json: { success: true, data: { results } } })
export const tokens = { access: 'a.b.c', refresh: 'r.r.r' }

export const makeUser = (role: string, over: Record<string, unknown> = {}) => ({
  id: 'u1', email: `${role}@fridah.co.ke`, first_name: 'Test', last_name: role, phone_number: '+254700000001',
  role, must_change_password: false, is_phone_verified: true, is_email_verified: true, kyc_status: 'verified', ...over,
})

export async function signIn(page: Page, email: string, password: string) {
  await page.goto('/login')
  await page.getByPlaceholder('you@example.com').fill(email)
  await page.locator('input[type="password"]').fill(password)
  await page.locator('button[type="submit"]').click()
}
