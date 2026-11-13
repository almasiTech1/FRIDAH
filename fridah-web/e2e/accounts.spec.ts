import { test, expect } from '@playwright/test'
import { stubApi, ok, page_, tokens, makeUser, signIn } from './stubs'

test.describe('signed out', () => {
  test('every portal sends a visitor to the login page', async ({ page }) => {
    await stubApi(page, {})
    for (const path of ['/tenant/dashboard', '/landlord/approvals', '/agency/dashboard', '/admin/agencies']) {
      await page.goto(path)
      await expect(page).toHaveURL(/\/login$/)
    }
  })
})

test.describe('admin-issued temporary password', () => {
  test('the agency admin is forced to choose a new password before reaching the app', async ({ page }) => {
    let changed = false
    const calls = await stubApi(page, {
      'POST /auth/login/': () => ok({ user: makeUser('landlord', { must_change_password: !changed }), tokens }),
      'GET /me/': () => ok(makeUser('landlord', { must_change_password: !changed })),
      // the API refuses everything but the password change while the temporary password is active
      'GET /agencies/': () => changed ? page_([{ id: 'a1', name: 'Prime Property Managers' }]) : { status: 403, json: { detail: 'You must change your temporary password before continuing.' } },
      'POST /auth/change-password/': (b) => { changed = true; return ok({}) },
    })
    await signIn(page, 'kamau@primepm.co.ke', 'Hk7mQ2xTnR4v')
    await expect(page).toHaveURL(/\/change-password$/)
    await expect(page.getByRole('heading', { name: 'Set your own password' })).toBeVisible()

    // cannot skip it by typing a URL
    await page.goto('/agency/dashboard')
    await expect(page).toHaveURL(/\/change-password$/)

    await page.getByLabel('Temporary password').fill('Hk7mQ2xTnR4v')
    await page.getByLabel('New password', { exact: true }).fill('My-New-Passw0rd!')
    await page.getByLabel('Confirm new password').fill('something-else')
    await page.getByRole('button', { name: 'Save and continue' }).click()
    await expect(page.getByRole('alert')).toContainText('do not match')
    expect(calls.some((c) => c.path === '/auth/change-password/')).toBe(false)

    await page.getByLabel('Confirm new password').fill('My-New-Passw0rd!')
    await page.getByRole('button', { name: 'Save and continue' }).click()
    await expect(page).toHaveURL(/\/agency\/dashboard$/)
    const sent = calls.find((c) => c.path === '/auth/change-password/')!
    expect(sent.body).toMatchObject({ old_password: 'Hk7mQ2xTnR4v', new_password: 'My-New-Passw0rd!' })
  })
})

test.describe('nobody can become an agency', () => {
  for (const role of ['tenant', 'landlord'] as const) {
    test(`${role}: the agency portal is not reachable and no create option exists`, async ({ page }) => {
      await stubApi(page, {
        'POST /auth/login/': () => ok({ user: makeUser(role), tokens }),
        'GET /me/': () => ok(makeUser(role)),
        'GET /agencies/': () => page_([]),
      })
      await signIn(page, `${role}@fridah.co.ke`, 'x')
      await expect(page).toHaveURL(new RegExp(`/${role}/dashboard$`))
      await page.goto('/agency/dashboard')
      await expect(page).toHaveURL(new RegExp(`/${role}/dashboard$`))
      await expect(page.getByText(/become an agency|create an agency|manage properties as an agency/i)).toHaveCount(0)
    })
  }
})

test.describe('admin registers an agency', () => {
  test('shows the one-time temporary password, and it disappears when dismissed', async ({ page }) => {
    const calls = await stubApi(page, {
      'POST /auth/login/': () => ok({ user: makeUser('admin'), tokens }),
      'GET /me/': () => ok(makeUser('admin')),
      'GET /agencies/': () => ({ json: { success: true, data: { results: [] } } }),
      'POST /agencies/': () => ok({ id: 'a1', credentials: { login_email: 'kamau@primepm.co.ke', temporary_password: 'Hk7mQ2xTnR4v' } }),
    })
    await signIn(page, 'admin@fridah.co.ke', 'x')
    await page.goto('/admin/agencies')
    await page.getByRole('button', { name: '+ Register agency' }).click()
    await page.getByLabel(/First name/).fill('Kamau')
    await page.getByLabel(/Last name/).fill('Mwangi')
    await page.getByLabel(/Login email/).fill('kamau@primepm.co.ke')
    await page.getByLabel(/^Phone/).first().fill('+254700000071')
    await page.getByLabel(/Agency name/).fill('Prime Property Managers')
    await page.getByRole('button', { name: 'Register agency' }).click()

    await expect(page.getByText('Hk7mQ2xTnR4v')).toBeVisible()
    await expect(page.getByText(/shown only once/i)).toBeVisible()
    expect(calls.find((c) => c.method === 'POST' && c.path === '/agencies/')!.body).toMatchObject({
      admin_first_name: 'Kamau', admin_email: 'kamau@primepm.co.ke', name: 'Prime Property Managers',
    })
    await page.getByRole('button', { name: /I have saved it/ }).click()
    await expect(page.getByText('Hk7mQ2xTnR4v')).toHaveCount(0)
  })
})
