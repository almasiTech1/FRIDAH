import { test, expect } from '@playwright/test'
import { stubApi, ok, page_, tokens, makeUser, signIn } from './stubs'

const queueItem = {
  id: 'p1', name: 'Karen Heights Apartments', town: 'Karen', county: 'Nairobi', landlord_name: 'Jane Wanjiru',
  submitted_by_agency: 'Prime Property Managers', review_state: 'awaiting_landlord', submission_version: 1,
  requires_landlord_approval: true, missing_approvals: ['landlord', 'admin'], age_days: 4,
}

test.describe('landlord approves an agency-submitted property', () => {
  test('approve goes to the landlord endpoint; a rejection needs a reason', async ({ page }) => {
    const calls = await stubApi(page, {
      'POST /auth/login/': () => ok({ user: makeUser('landlord'), tokens }),
      'GET /me/': () => ok(makeUser('landlord')),
      'GET /agencies/': () => page_([]),
      'GET /properties/review-queue/': () => ok({ role: 'landlord', count: 1, results: [queueItem] }),
      'POST /properties/p1/review/': () => ok({ status: 'pending_approval', review_state: 'awaiting_admin', missing_approvals: ['admin'] }),
    })
    await signIn(page, 'landlord@fridah.co.ke', 'x')
    await page.goto('/landlord/approvals')
    await expect(page.getByText('Karen Heights Apartments')).toBeVisible()
    await expect(page.getByText(/Landlord and Administrator approval/)).toBeVisible()

    await page.getByRole('button', { name: 'Reject' }).click()
    await expect(page.getByRole('button', { name: 'Send' })).toBeDisabled()
    await page.getByLabel(/rejecting/i).fill('Wrong estate')
    await expect(page.getByRole('button', { name: 'Send' })).toBeEnabled()

    await page.getByRole('button', { name: 'Approve' }).click()
    await expect.poll(() => calls.some((c) => c.path === '/properties/p1/review/' && c.body?.action === 'approve')).toBe(true)
  })
})

test.describe('admin handles a refund', () => {
  const refund = {
    id: 'r1', payment_reference: 'PAY-7K2M9X', payment_amount: '20000', amount: '3000', kind: 'refund', reason: 'Charged twice',
    status: 'approved', approval_level: 'recipient', requested_by: 'u9', requested_by_name: 'Tom Otieno',
    created_at: '2026-10-26T09:00:00Z', can_decide: false, auto_payout_available: false, payout_status: null,
  }

  test('records the M-Pesa payout only with a real reference', async ({ page }) => {
    let status = 'approved'
    const calls = await stubApi(page, {
      'POST /auth/login/': () => ok({ user: makeUser('admin'), tokens }),
      'GET /me/': () => ok(makeUser('admin')),
      'GET /agencies/': () => page_([]),
      'GET /refunds/policy/': () => ok({ admin_approval_above: '5000.00', window_days: 180, self_approval_allowed: false, auto_payout_enabled: false }),
      'GET /refunds/': () => page_([{ ...refund, status, payout_reference: status === 'paid_out' ? 'QHX9PAYOUT1' : '' }]),
      'POST /refunds/r1/mark-paid/': () => { status = 'paid_out'; return ok({}) },
    })
    await signIn(page, 'admin@fridah.co.ke', 'x')
    await page.goto('/admin/refunds')
    await expect(page.getByText('PAY-7K2M9X')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Send via M-Pesa' })).toHaveCount(0)   // automatic payouts are off

    await page.getByRole('button', { name: 'Record payout manually' }).click()
    await page.getByPlaceholder(/M-Pesa reference/).fill('abc')
    await expect(page.getByRole('button', { name: 'Save' })).toBeDisabled()
    await page.getByPlaceholder(/M-Pesa reference/).fill('QHX9PAYOUT1')
    await page.getByRole('button', { name: 'Save' }).click()
    await expect.poll(() => calls.find((c) => c.path === '/refunds/r1/mark-paid/')?.body).toEqual({ reference: 'QHX9PAYOUT1' })
    await expect(page.getByText(/Paid out · ref QHX9PAYOUT1/)).toBeVisible()
  })

  test('the refund policy can be changed and a server error is shown', async ({ page }) => {
    let fail = false
    await stubApi(page, {
      'POST /auth/login/': () => ok({ user: makeUser('admin'), tokens }),
      'GET /me/': () => ok(makeUser('admin')),
      'GET /agencies/': () => page_([]),
      'GET /refunds/': () => page_([]),
      'GET /refunds/policy/': () => ok({ admin_approval_above: '5000.00', window_days: 180, self_approval_allowed: false, auto_payout_enabled: false }),
      'PUT /refunds/policy/': () => fail
        ? { status: 400, json: { success: false, error: { message: 'The refund window must be between 1 and 730 days.' } } }
        : ok({ admin_approval_above: '2000.00', window_days: 90, self_approval_allowed: false, auto_payout_enabled: false }),
    })
    await signIn(page, 'admin@fridah.co.ke', 'x')
    await page.goto('/admin/refunds')
    await page.getByLabel('Admin approval needed above (KES)').fill('2000')
    await page.getByLabel('Refund window (days)').fill('90')
    await page.getByRole('button', { name: 'Save policy' }).click()
    await expect(page.getByText('Saved')).toBeVisible()
    fail = true
    await page.getByLabel('Refund window (days)').fill('9999')
    await page.getByRole('button', { name: 'Save policy' }).click()
    await expect(page.getByRole('alert')).toContainText('between 1 and 730 days')
  })
})

test('reduced-motion users get no animated list entry', async ({ browser }) => {
  const context = await browser.newContext({ reducedMotion: 'reduce' })
  const page = await context.newPage()
  await stubApi(page, {
    'POST /auth/login/': () => ok({ user: makeUser('landlord'), tokens }),
    'GET /me/': () => ok(makeUser('landlord')),
    'GET /agencies/': () => page_([]),
    'GET /properties/review-queue/': () => ok({ role: 'landlord', count: 1, results: [queueItem] }),
  })
  await signIn(page, 'landlord@fridah.co.ke', 'x')
  await page.goto('/landlord/approvals')
  const card = page.locator('.stagger > *').first()
  await expect(card).toBeVisible()
  const duration = await card.evaluate((el) => getComputedStyle(el).animationDuration)
  expect(parseFloat(duration)).toBeLessThan(0.01)       // collapsed by the prefers-reduced-motion rule
  await context.close()
})
