import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/api/services', async (importOriginal) => {
  const real: any = await importOriginal()
  return {
    ...real,
    refundApi: { list: vi.fn(), request: vi.fn(), approve: vi.fn(), reject: vi.fn(), cancel: vi.fn(), markPaid: vi.fn(), payOut: vi.fn(), policy: vi.fn(), updatePolicy: vi.fn() },
    reconciliationApi: {
      runs: vi.fn(), run: vi.fn(), runInternal: vi.fn(), uploadStatement: vi.fn(), resolveItem: vi.fn(), settlement: vi.fn(),
    },
  }
})

import { refundApi, reconciliationApi } from '@/api/services'
import { useAuthStore } from '@/stores/auth'
import RefundsList from '@/components/common/RefundsList.vue'
import RefundRequestForm from '@/components/common/RefundRequestForm.vue'
import Reconciliation from '@/portals/admin/views/Reconciliation.vue'
import RefundPolicyCard from '@/components/common/RefundPolicyCard.vue'

const base = {
  id: 'r1', payment_reference: 'PAY-ABC', payment_amount: '20000', amount: '3000', kind: 'refund', reason: 'Double charged',
  status: 'requested', approval_level: 'recipient', requested_by: 'tenant-1', requested_by_name: 'Tom Tenant',
  created_at: '2026-03-10T10:00:00Z', can_decide: false, decision_comment: '', payout_reference: '',
}
const rows = (...r: any[]) => (refundApi.list as any).mockResolvedValue({ data: { data: { results: r } } })
const button = (w: any, text: string) => w.findAll('button').find((b: any) => b.text() === text)

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  ;(refundApi.policy as any).mockResolvedValue({ data: { data: { admin_approval_above: '5000.00', window_days: 180, self_approval_allowed: false, auto_payout_enabled: false } } })
})

describe('RefundsList', () => {
  it('only offers approve/reject to someone allowed to decide', async () => {
    rows({ ...base, can_decide: false }, { ...base, id: 'r2', can_decide: true })
    const w = mount(RefundsList, { props: { role: 'landlord' } })
    await flushPromises()
    expect(w.findAll('button').filter((b) => b.text() === 'Approve')).toHaveLength(1)   // only r2
    expect(w.text()).toContain('KES 3,000.00')
  })

  it('shows "Admin approval needed" for large requests and approves with no comment by default', async () => {
    rows({ ...base, can_decide: true, approval_level: 'admin' })
    ;(refundApi.approve as any).mockResolvedValue({})
    const w = mount(RefundsList, { props: { role: 'admin' } })
    await flushPromises()
    expect(w.text()).toContain('Admin approval needed')
    await button(w, 'Approve')!.trigger('click')
    expect(refundApi.approve).toHaveBeenCalledWith('r1', '', false)
  })

  it('will not reject without a reason', async () => {
    rows({ ...base, can_decide: true })
    ;(refundApi.reject as any).mockResolvedValue({})
    const w = mount(RefundsList, { props: { role: 'landlord' } })
    await flushPromises()
    await button(w, 'Reject')!.trigger('click')
    expect((button(w, 'Send')!.element as HTMLButtonElement).disabled).toBe(true)
    await w.find('input[placeholder^="Reason"]').setValue('Already refunded in cash')
    await w.find('form').trigger('submit')
    expect(refundApi.reject).toHaveBeenCalledWith('r1', 'Already refunded in cash')
  })

  it('lets only the requester cancel, and only while pending', async () => {
    useAuthStore().user = { id: 'tenant-1', role: 'tenant' } as any
    rows(base, { ...base, id: 'r2', requested_by: 'someone-else' }, { ...base, id: 'r3', status: 'approved' })
    const w = mount(RefundsList, { props: { role: 'tenant' } })
    await flushPromises()
    expect(w.findAll('button').filter((b) => b.text() === 'Cancel')).toHaveLength(1)
  })

  it('only an admin can record the M-Pesa payout, and needs a real reference', async () => {
    rows({ ...base, status: 'approved' })
    ;(refundApi.markPaid as any).mockResolvedValue({})
    const landlord = mount(RefundsList, { props: { role: 'landlord' } })
    await flushPromises()
    expect(button(landlord, 'Record payout manually')).toBeUndefined()

    const admin = mount(RefundsList, { props: { role: 'admin' } })
    await flushPromises()
    await button(admin, 'Record payout manually')!.trigger('click')
    await admin.find('input[placeholder^="M-Pesa"]').setValue('abc')
    expect((button(admin, 'Save')!.element as HTMLButtonElement).disabled).toBe(true)
    await admin.find('input[placeholder^="M-Pesa"]').setValue('QHX9PAYOUT1')
    await admin.find('form').trigger('submit')
    expect(refundApi.markPaid).toHaveBeenCalledWith('r1', 'QHX9PAYOUT1')
  })

  it('offers the negative-balance override to admins only', async () => {
    rows({ ...base, can_decide: true })
    const err = { response: { data: { error: { message: 'The recipient has already withdrawn funds from this payment.' } } } }
    ;(refundApi.approve as any).mockRejectedValue(err)

    const admin = mount(RefundsList, { props: { role: 'admin' } })
    await flushPromises()
    await button(admin, 'Approve')!.trigger('click'); await flushPromises()
    expect(admin.text()).toContain('already withdrawn')
    expect(admin.text()).toContain('Approve with negative balance')
    ;(refundApi.approve as any).mockResolvedValue({})
    await admin.findAll('button').find((b) => b.text() === 'Approve with negative balance')!.trigger('click')
    expect(refundApi.approve).toHaveBeenLastCalledWith('r1', '', true)

    ;(refundApi.approve as any).mockRejectedValue(err)
    const landlord = mount(RefundsList, { props: { role: 'landlord' } })
    await flushPromises()
    await button(landlord, 'Approve')!.trigger('click'); await flushPromises()
    expect(landlord.text()).toContain('already withdrawn')
    expect(landlord.text()).not.toContain('Approve with negative balance')
  })

  it('shows an error state when loading fails', async () => {
    ;(refundApi.list as any).mockRejectedValue(new Error('down'))
    const w = mount(RefundsList, { props: { role: 'admin' } })
    await flushPromises()
    expect(w.text()).toContain('Could not load refund requests')
  })
})

describe('RefundRequestForm', () => {
  const payment = { id: 'p1', reference: 'PAY-ABC', amount: '20000', refunded_amount: '5000' }

  it('shows what can still be refunded and submits the request', async () => {
    ;(refundApi.request as any).mockResolvedValue({})
    const w = mount(RefundRequestForm, { props: { payment } })
    expect(w.text()).toContain('KES 15,000.00')
    expect(w.find('select').exists()).toBe(false)                    // customers cannot choose "reversal"
    await w.find('input[type="number"]').setValue('2500')
    await w.find('input[placeholder^="Why"]').setValue('Overcharged')
    await w.find('form').trigger('submit')
    await flushPromises()
    expect(refundApi.request).toHaveBeenCalledWith('p1', { amount: 2500, reason: 'Overcharged', kind: 'refund' })
    expect(w.emitted('done')).toBeTruthy()
  })

  it('a reversal pre-fills the full remaining amount', async () => {
    const w = mount(RefundRequestForm, { props: { payment, canReverse: true } })
    await w.find('select').setValue('reversal')
    expect((w.find('input[type="number"]').element as HTMLInputElement).value).toBe('15000')
  })

  it('shows the server\'s reason when refused', async () => {
    ;(refundApi.request as any).mockRejectedValue({ response: { data: { error: { message: 'Only KES 15000 of this payment can still be refunded.' } } } })
    const w = mount(RefundRequestForm, { props: { payment } })
    await w.find('input[type="number"]').setValue('99999')
    await w.find('input[placeholder^="Why"]').setValue('x')
    await w.find('form').trigger('submit')
    await flushPromises()
    expect(w.text()).toContain('can still be refunded')
    expect(w.emitted('done')).toBeFalsy()
  })
})

describe('Reconciliation page', () => {
  it('requires a resolution note before an item can be resolved', async () => {
    ;(reconciliationApi.settlement as any).mockResolvedValue({ data: { data: { gross_collected: '20000', platform_commission: '1000',
      credited_to_recipients: '19000', wallet_liability: '19000', refunds_approved: '0', refunds_awaiting_payout: '0',
      payouts_sent_to_recipients: '0', recovered_from_recipient_wallets: '0' } } })
    ;(reconciliationApi.runs as any).mockResolvedValue({ data: { data: { results: [
      { id: 'run1', source: 'internal', period_start: '2026-03-10', period_end: '2026-03-10', rows_checked: 3, matched: 2, open_issues: 1, created_at: '2026-03-11T01:00:00Z' }] } } })
    ;(reconciliationApi.run as any).mockResolvedValue({ data: { data: { items: [
      { id: 'i1', kind: 'missing_wallet_credit', kind_label: 'Completed payment without a wallet credit', note: 'PAY-ABC: no wallet credit',
        receipt: '', expected_amount: '20000', actual_amount: null, resolved: false, resolution_note: '' }] } } })
    ;(reconciliationApi.resolveItem as any).mockResolvedValue({})
    const w = mount(Reconciliation)
    await flushPromises()
    expect(w.text()).toContain('KES 19,000.00')
    await button(w, 'View')!.trigger('click'); await flushPromises()
    expect(w.text()).toContain('Completed payment without a wallet credit')
    await button(w, 'Resolve')!.trigger('click')
    expect((button(w, 'Mark resolved')!.element as HTMLButtonElement).disabled).toBe(true)
    await w.find('input[placeholder^="What was done"]').setValue('Credited manually on 11 Mar')
    await w.find('form[class*="mt-2"]').trigger('submit'); await flushPromises()
    expect(reconciliationApi.resolveItem).toHaveBeenCalledWith('i1', 'Credited manually on 11 Mar')
  })
})


describe('Automatic M-Pesa payout button', () => {
  const approved = { ...base, status: 'approved' }

  it('appears for admins only when automatic payouts are available and none is in flight', async () => {
    rows({ ...approved, auto_payout_available: true }, { ...approved, id: 'r2', auto_payout_available: true, payout_status: 'processing' }, { ...approved, id: 'r3', auto_payout_available: false })
    ;(refundApi.payOut as any).mockResolvedValue({})
    const admin = mount(RefundsList, { props: { role: 'admin' } })
    await flushPromises()
    expect(admin.findAll('button').filter((b) => b.text() === 'Send via M-Pesa')).toHaveLength(1)
    expect(admin.text()).toContain('M-Pesa payout processing')
    expect(admin.findAll('button').filter((b) => b.text() === 'Record payout manually')).toHaveLength(3)   // manual always possible
    await button(admin, 'Send via M-Pesa')!.trigger('click')
    expect(refundApi.payOut).toHaveBeenCalledWith('r1')

    const landlord = mount(RefundsList, { props: { role: 'landlord' } })
    await flushPromises()
    expect(button(landlord, 'Send via M-Pesa')).toBeUndefined()
  })

  it('shows why a payout could not be sent', async () => {
    rows({ ...approved, auto_payout_available: true })
    ;(refundApi.payOut as any).mockRejectedValue({ response: { data: { error: { message: 'M-Pesa rejected the payout: Insufficient float' } } } })
    const w = mount(RefundsList, { props: { role: 'admin' } })
    await flushPromises()
    await button(w, 'Send via M-Pesa')!.trigger('click'); await flushPromises()
    expect(w.text()).toContain('Insufficient float')
  })
})

describe('RefundPolicyCard', () => {
  it('shows the current policy and what is fixed by configuration', async () => {
    const w = mount(RefundPolicyCard)
    await flushPromises()
    expect((w.find('#rp-limit').element as HTMLInputElement).value).toBe('5000')
    expect((w.find('#rp-days').element as HTMLInputElement).value).toBe('180')
    expect(w.text()).toContain('approving your own request is not allowed')
    expect(w.text()).toContain('automatic M-Pesa payouts are off')
  })

  it('saves new limits and shows the server error when they are refused', async () => {
    ;(refundApi.updatePolicy as any).mockResolvedValueOnce({ data: { data: { admin_approval_above: '2000.00', window_days: 90, self_approval_allowed: false, auto_payout_enabled: false } } })
    const w = mount(RefundPolicyCard)
    await flushPromises()
    await w.find('#rp-limit').setValue('2000')
    await w.find('#rp-days').setValue('90')
    await w.find('form').trigger('submit'); await flushPromises()
    expect(refundApi.updatePolicy).toHaveBeenCalledWith(2000, 90)
    expect(w.text()).toContain('Saved')

    ;(refundApi.updatePolicy as any).mockRejectedValueOnce({ response: { data: { error: { message: 'The refund window must be between 1 and 730 days.' } } } })
    await w.find('#rp-days').setValue('9999')
    await w.find('form').trigger('submit'); await flushPromises()
    expect(w.text()).toContain('between 1 and 730 days')
  })
})

describe('RefundRequestForm uses the live approval limit', () => {
  it('tells the customer the limit finance configured, not a hard-coded number', async () => {
    ;(refundApi.policy as any).mockResolvedValue({ data: { data: { admin_approval_above: '2000.00' } } })
    const w = mount(RefundRequestForm, { props: { payment: { id: 'p1', reference: 'PAY-ABC', amount: '20000' } } })
    await flushPromises()
    expect(w.text()).toContain('Refunds over KES 2,000.00')
  })
})
