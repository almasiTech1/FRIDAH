import React from 'react'
import { Alert } from 'react-native'
import { render, fireEvent, waitFor, configure } from '@testing-library/react-native'

jest.mock('@/api/services', () => ({
  approvalApi: { queue: jest.fn(), landlordDecision: jest.fn(), adminDecision: jest.fn() },
  authApi: { changePassword: jest.fn() },
  notificationsApi: { preferences: jest.fn(), updatePreferences: jest.fn() },
  agencyApi: { list: jest.fn(), create: jest.fn(), setStatus: jest.fn(), resetAdminPassword: jest.fn() },
  analyticsApi: { adminDashboard: jest.fn() },
  refundApi: { list: jest.fn(), approve: jest.fn(), reject: jest.fn(), cancel: jest.fn(), request: jest.fn(), markPaid: jest.fn(), payOut: jest.fn() },
  paymentsApi: { list: jest.fn() },
  reconciliationApi: { runs: jest.fn(), run: jest.fn(), runInternal: jest.fn(), resolveItem: jest.fn(), settlement: jest.fn() },
}))
jest.mock('@/stores/authStore', () => ({ useAuthStore: jest.fn() }))
jest.mock('@react-navigation/native', () => ({ useNavigation: () => ({ navigate: jest.fn() }) }))

import { approvalApi, authApi, notificationsApi, agencyApi, refundApi, paymentsApi, reconciliationApi } from '@/api/services'
import { useAuthStore } from '@/stores/authStore'
import { PropertyReviewQueue } from '@/components/common/PropertyReviewQueue'
import { ForceChangePasswordScreen } from '@/screens/auth/ForceChangePasswordScreen'
import { NotificationPreferencesCard } from '@/components/common/NotificationPreferencesCard'
import { AdminAgenciesScreen } from '@/screens/admin/AgenciesScreen'
import { RefundsQueue } from '@/components/common/RefundsQueue'
import { RefundRequestPanel } from '@/components/common/RefundRequestPanel'
import { AdminReconciliationScreen } from '@/screens/admin/ReconciliationScreen'
import { AdminProfileScreen } from '@/screens/admin/ProfileScreen'
import { AdminDashboardScreen } from '@/screens/admin/DashboardScreen'
import { analyticsApi } from '@/api/services'

const m = (fn: unknown) => fn as jest.Mock

const item = {
  id: 'p1', name: 'Karen Heights', town: 'Karen', county: 'Nairobi', landlord_name: 'Jane Owner',
  submitted_by_agency: 'Prime PM', review_state: 'awaiting_landlord', submission_version: 2,
  requires_landlord_approval: true, missing_approvals: ['landlord', 'admin'], age_days: 4,
}

jest.setTimeout(30000) // first render loads the whole component tree
configure({ asyncUtilTimeout: 10000 }) // the first findBy* in a cold run can exceed the 1s default
beforeEach(() => jest.clearAllMocks())

describe('PropertyReviewQueue', () => {
  it('shows the submission and what approvals it still needs', async () => {
    m(approvalApi.queue).mockResolvedValue({ data: { data: { results: [item] } } })
    const { findByText, getByText } = render(<PropertyReviewQueue role="landlord" color="#059669" />)
    await findByText('Karen Heights')
    expect(getByText(/Waiting 4 days/)).toBeTruthy()
    expect(getByText(/Needs Landlord and Administrator approval/)).toBeTruthy()
  })

  it('landlord approvals go to the landlord endpoint, admin approvals to the admin endpoint', async () => {
    m(approvalApi.queue).mockResolvedValue({ data: { data: { results: [item] } } })
    m(approvalApi.landlordDecision).mockResolvedValue({})
    m(approvalApi.adminDecision).mockResolvedValue({})

    const landlord = render(<PropertyReviewQueue role="landlord" color="#059669" />)
    fireEvent.press(await landlord.findByText('Approve'))
    await waitFor(() => expect(approvalApi.landlordDecision).toHaveBeenCalledWith('p1', 'approve', ''))
    expect(approvalApi.adminDecision).not.toHaveBeenCalled()
    landlord.unmount()

    const admin = render(<PropertyReviewQueue role="admin" color="#111" />)
    fireEvent.press(await admin.findByText('Approve'))
    await waitFor(() => expect(approvalApi.adminDecision).toHaveBeenCalledWith('p1', 'approve', ''))
  })

  it('will not send a rejection until a reason is typed', async () => {
    m(approvalApi.queue).mockResolvedValue({ data: { data: { results: [item] } } })
    m(approvalApi.landlordDecision).mockResolvedValue({})
    const { findByText, getByText, getByLabelText } = render(<PropertyReviewQueue role="landlord" color="#059669" />)
    fireEvent.press(await findByText('Reject'))
    fireEvent.press(getByText('Send'))
    expect(approvalApi.landlordDecision).not.toHaveBeenCalled()
    fireEvent.changeText(getByLabelText('Reason'), 'Wrong estate')
    fireEvent.press(getByText('Send'))
    await waitFor(() => expect(approvalApi.landlordDecision).toHaveBeenCalledWith('p1', 'reject', 'Wrong estate'))
  })
})

describe('ForceChangePasswordScreen', () => {
  const store = { fetchMe: jest.fn(), fetchAgencies: jest.fn(), logout: jest.fn() }
  beforeEach(() => m(useAuthStore).mockReturnValue(store))

  const fill = (r: ReturnType<typeof render>, a: string, b: string, c: string) => {
    const inputs = r.UNSAFE_getAllByType(require('react-native').TextInput)
    fireEvent.changeText(inputs[0], a); fireEvent.changeText(inputs[1], b); fireEvent.changeText(inputs[2], c)
  }

  it('refuses mismatched passwords without calling the API', async () => {
    const r = render(<ForceChangePasswordScreen />)
    fill(r, 'Temp1234abcd', 'My-New-Passw0rd!', 'different')
    fireEvent.press(r.getByText('Save and continue'))
    expect(await r.findByText('The new passwords do not match.')).toBeTruthy()
    expect(authApi.changePassword).not.toHaveBeenCalled()
  })

  it('changes the password then reloads the user so the app unlocks', async () => {
    m(authApi.changePassword).mockResolvedValue({})
    const r = render(<ForceChangePasswordScreen />)
    fill(r, 'Temp1234abcd', 'My-New-Passw0rd!', 'My-New-Passw0rd!')
    fireEvent.press(r.getByText('Save and continue'))
    await waitFor(() => expect(authApi.changePassword).toHaveBeenCalledWith('Temp1234abcd', 'My-New-Passw0rd!'))
    await waitFor(() => { expect(store.fetchMe).toHaveBeenCalled(); expect(store.fetchAgencies).toHaveBeenCalled() })
  })

  it('shows the server\'s reason when the password is rejected', async () => {
    m(authApi.changePassword).mockRejectedValue({ response: { data: { new_password: ['This password is too common.'] } } })
    const r = render(<ForceChangePasswordScreen />)
    fill(r, 'Temp1234abcd', 'password', 'password')
    fireEvent.press(r.getByText('Save and continue'))
    expect(await r.findByText('This password is too common.')).toBeTruthy()
    expect(store.fetchMe).not.toHaveBeenCalled()
  })
})

describe('NotificationPreferencesCard quiet hours', () => {
  const prefs = { sms_enabled: true, push_enabled: true, email_enabled: false, payment_alerts: true, maintenance_alerts: true,
                  quiet_hours_start: '22:00:00', quiet_hours_end: '06:30:00' }

  it('loads saved quiet hours as HH:MM', async () => {
    m(notificationsApi.preferences).mockResolvedValue({ data: prefs })
    const { findByDisplayValue } = render(<NotificationPreferencesCard accentColor="#000" />)
    expect(await findByDisplayValue('22:00')).toBeTruthy()
    expect(await findByDisplayValue('06:30')).toBeTruthy()
  })

  it('rejects one time without the other and malformed times', async () => {
    m(notificationsApi.preferences).mockResolvedValue({ data: { ...prefs, quiet_hours_start: null, quiet_hours_end: null } })
    const { findByLabelText, getByText, findByText } = render(<NotificationPreferencesCard accentColor="#000" />)
    fireEvent.changeText(await findByLabelText('Quiet hours start'), '21:00')
    fireEvent.press(getByText('Save preferences'))
    expect(await findByText('Set both quiet-hours times, or leave both empty.')).toBeTruthy()
    fireEvent.changeText(await findByLabelText('Quiet hours end'), '7pm')
    fireEvent.press(getByText('Save preferences'))
    expect(await findByText('Use 24-hour times like 21:00.')).toBeTruthy()
    expect(notificationsApi.updatePreferences).not.toHaveBeenCalled()
  })

  it('saves valid times', async () => {
    m(notificationsApi.preferences).mockResolvedValue({ data: prefs })
    m(notificationsApi.updatePreferences).mockResolvedValue({})
    const { findByText, getByText } = render(<NotificationPreferencesCard accentColor="#000" />)
    await findByText('Notifications')
    fireEvent.press(getByText('Save preferences'))
    await waitFor(() => expect(notificationsApi.updatePreferences).toHaveBeenCalledWith(
      expect.objectContaining({ quiet_hours_start: '22:00', quiet_hours_end: '06:30' })))
  })
})

describe('AdminAgenciesScreen', () => {
  it('shows the temporary password once after registering, and it can be dismissed', async () => {
    m(agencyApi.list).mockResolvedValue({ data: { results: [] } })
    m(agencyApi.create).mockResolvedValue({ data: { data: { id: 'a1',
      credentials: { login_email: 'kamau@primepm.co.ke', temporary_password: 'Abcd2345efgh' } } } })
    const r = render(<AdminAgenciesScreen />)
    fireEvent.press(await r.findByText('+ Register agency'))
    fireEvent.changeText(r.getByPlaceholderText('First name *'), 'Kamau')
    fireEvent.changeText(r.getByPlaceholderText('Last name *'), 'Mwangi')
    fireEvent.changeText(r.getByPlaceholderText('Login email *'), 'kamau@primepm.co.ke')
    fireEvent.changeText(r.getByPlaceholderText('Phone (+2547XXXXXXXX) *'), '+254700000071')
    fireEvent.changeText(r.getByPlaceholderText('Agency name *'), 'Prime Property Managers')
    fireEvent.press(r.getByText('Register agency'))
    expect(await r.findByText(/Temporary password: Abcd2345efgh/)).toBeTruthy()
    expect(agencyApi.create).toHaveBeenCalledWith(expect.objectContaining({
      admin_first_name: 'Kamau', admin_email: 'kamau@primepm.co.ke', name: 'Prime Property Managers' }))
    fireEvent.press(r.getByText('I have saved it - dismiss'))
    expect(r.queryByText(/Abcd2345efgh/)).toBeNull()
  })

  it('requires the agency admin details before calling the API', async () => {
    m(agencyApi.list).mockResolvedValue({ data: { results: [] } })
    const r = render(<AdminAgenciesScreen />)
    fireEvent.press(await r.findByText('+ Register agency'))
    fireEvent.changeText(r.getByPlaceholderText('Agency name *'), 'Prime')
    fireEvent.press(r.getByText('Register agency'))
    expect(await r.findByText(/first name, last name, email and phone are required/)).toBeTruthy()
    expect(agencyApi.create).not.toHaveBeenCalled()
  })
})


describe('RefundsQueue', () => {
  const base = {
    id: 'r1', payment_reference: 'PAY-ABC', payment_amount: '20000', amount: '3000', kind: 'refund', reason: 'Double charged',
    status: 'requested', approval_level: 'recipient', requested_by: 'tenant-1', requested_by_name: 'Tom Tenant',
    created_at: '2026-03-10T10:00:00Z', can_decide: false, decision_comment: '', payout_reference: '',
  }
  const list = (...rows: any[]) => m(refundApi.list).mockResolvedValue({ data: { data: { results: rows } } })
  beforeEach(() => m(useAuthStore).mockReturnValue({ user: { id: 'tenant-1' } }))

  it('shows approve/reject only for requests the user may decide', async () => {
    list({ ...base, can_decide: false }, { ...base, id: 'r2', can_decide: true })
    const { findAllByText, queryAllByText } = render(<RefundsQueue color="#000" />)
    expect((await findAllByText('Approve'))).toHaveLength(1)
    expect(queryAllByText('Reject')).toHaveLength(1)
  })

  it('lets the requester cancel their own pending request only', async () => {
    list(base, { ...base, id: 'r2', requested_by: 'someone-else' }, { ...base, id: 'r3', status: 'approved' })
    m(refundApi.cancel).mockResolvedValue({})
    const { findAllByText } = render(<RefundsQueue color="#000" />)
    const cancels = await findAllByText('Cancel request')
    expect(cancels).toHaveLength(1)
    fireEvent.press(cancels[0])
    await waitFor(() => expect(refundApi.cancel).toHaveBeenCalledWith('r1'))
  })

  it('approves with the right id and does not allow rejecting without a reason', async () => {
    list({ ...base, can_decide: true })
    m(refundApi.approve).mockResolvedValue({})
    m(refundApi.reject).mockResolvedValue({})
    const { findByText, getByText, getByLabelText } = render(<RefundsQueue color="#000" />)
    fireEvent.press(await findByText('Reject'))
    fireEvent.press(getByText('Send'))
    expect(refundApi.reject).not.toHaveBeenCalled()
    fireEvent.changeText(getByLabelText('Reason'), 'Already refunded in cash')
    fireEvent.press(getByText('Send'))
    await waitFor(() => expect(refundApi.reject).toHaveBeenCalledWith('r1', 'Already refunded in cash'))
  })

  it('shows the server reason when an approval is refused', async () => {
    list({ ...base, can_decide: true })
    m(refundApi.approve).mockRejectedValue({ response: { data: { error: { message: 'The recipient has already withdrawn funds.' } } } })
    const { findByText } = render(<RefundsQueue color="#000" />)
    fireEvent.press(await findByText('Approve'))
    expect(await findByText('The recipient has already withdrawn funds.')).toBeTruthy()
  })

  it('flags requests that need an administrator and shows the payout reference', async () => {
    list({ ...base, approval_level: 'admin' }, { ...base, id: 'r2', status: 'paid_out', payout_reference: 'QHX9PAYOUT1' })
    const { findByText } = render(<RefundsQueue color="#000" />)
    expect(await findByText('Needs a FRIDAH administrator')).toBeTruthy()
    expect(await findByText(/QHX9PAYOUT1/)).toBeTruthy()
  })
})


describe('Mobile refund requests', () => {
  const pay = (over: any = {}) => ({ id: 'p1', reference: 'PAY-ABC', amount: '20000', refunded_amount: '5000', status: 'completed', created_at: '2026-03-10T10:00:00Z', ...over })

  it('lists only completed payments with something left to refund, then submits a request', async () => {
    m(paymentsApi.list).mockResolvedValue({ data: { data: { results: [
      pay(), pay({ id: 'p2', reference: 'PAY-FAILED', status: 'failed' }), pay({ id: 'p3', reference: 'PAY-FULL', refunded_amount: '20000' })] } } })
    m(refundApi.request).mockResolvedValue({})
    const done = jest.fn()
    const { findByText, queryByText, getByLabelText, getByText } = render(<RefundRequestPanel color="#000" onDone={done} />)
    fireEvent.press(await findByText('PAY-ABC'))
    expect(queryByText('PAY-FAILED')).toBeNull()
    expect(queryByText('PAY-FULL')).toBeNull()
    fireEvent.changeText(getByLabelText('Refund amount'), '2500')
    fireEvent.press(getByText('Submit request'))
    expect(refundApi.request).not.toHaveBeenCalled()             // a reason is required first
    fireEvent.changeText(getByLabelText('Refund reason'), 'Overcharged')
    fireEvent.press(getByText('Submit request'))
    await waitFor(() => expect(refundApi.request).toHaveBeenCalledWith('p1', { amount: '2500', reason: 'Overcharged' }))
    await waitFor(() => expect(done).toHaveBeenCalled())
  })

  it('says so when nothing can be refunded and shows the server reason when refused', async () => {
    m(paymentsApi.list).mockResolvedValue({ data: { data: { results: [] } } })
    expect(await render(<RefundRequestPanel color="#000" onDone={jest.fn()} />).findByText(/no completed payments/)).toBeTruthy()
    m(paymentsApi.list).mockResolvedValue({ data: { data: { results: [pay()] } } })
    m(refundApi.request).mockRejectedValue({ response: { data: { error: { message: 'Only KES 15000 of this payment can still be refunded.' } } } })
    const r = render(<RefundRequestPanel color="#000" onDone={jest.fn()} />)
    fireEvent.press(await r.findByText('PAY-ABC'))
    fireEvent.changeText(r.getByLabelText('Refund reason'), 'x')
    fireEvent.press(r.getByText('Submit request'))
    expect(await r.findByText(/can still be refunded/)).toBeTruthy()
  })
})

describe('Admin payouts on mobile', () => {
  const approved = { id: 'r1', payment_reference: 'PAY-ABC', payment_amount: '20000', amount: '3000', kind: 'refund', reason: 'Charged twice',
    status: 'approved', approval_level: 'recipient', requested_by: 'u1', created_at: '2026-03-10T10:00:00Z', can_decide: false,
    auto_payout_available: false, payout_status: null }
  beforeEach(() => m(useAuthStore).mockReturnValue({ user: { id: 'admin-1' } }))

  it('only admins see payout controls, and a real reference is required', async () => {
    m(refundApi.list).mockResolvedValue({ data: { data: { results: [approved] } } })
    m(refundApi.markPaid).mockResolvedValue({})
    const user = render(<RefundsQueue color="#000" />)
    await user.findByText(/KES 3,000.00/)
    expect(user.queryByText('Record payout')).toBeNull()

    const admin = render(<RefundsQueue color="#000" admin />)
    fireEvent.press(await admin.findByText('Record payout'))
    fireEvent.changeText(admin.getByLabelText('Payout reference'), 'abc')
    fireEvent.press(admin.getByText('Save payout'))
    expect(refundApi.markPaid).not.toHaveBeenCalled()
    fireEvent.changeText(admin.getByLabelText('Payout reference'), 'QHX9PAYOUT1')
    fireEvent.press(admin.getByText('Save payout'))
    await waitFor(() => expect(refundApi.markPaid).toHaveBeenCalledWith('r1', 'QHX9PAYOUT1'))
  })

  it('offers "Send via M-Pesa" only when automatic payouts are available and none is in flight', async () => {
    m(refundApi.list).mockResolvedValue({ data: { data: { results: [
      { ...approved, auto_payout_available: true }, { ...approved, id: 'r2', auto_payout_available: true, payout_status: 'processing' }] } } })
    m(refundApi.payOut).mockResolvedValue({})
    const admin = render(<RefundsQueue color="#000" admin />)
    const send = await admin.findAllByText('Send via M-Pesa')
    expect(send).toHaveLength(1)
    expect(admin.getByText(/payout processing/)).toBeTruthy()
    fireEvent.press(send[0])
    await waitFor(() => expect(refundApi.payOut).toHaveBeenCalledWith('r1'))
  })
})

describe('Admin reconciliation on mobile', () => {
  it('needs a note to resolve an item and refreshes afterwards', async () => {
    m(reconciliationApi.settlement).mockResolvedValue({ data: { data: { gross_collected: '20000', platform_commission: '1000', wallet_liability: '19000', refunds_awaiting_payout: '0' } } })
    m(reconciliationApi.runs).mockResolvedValue({ data: { data: { results: [
      { id: 'run1', source: 'internal', period_start: '2026-03-10', period_end: '2026-03-10', rows_checked: 3, matched: 2, open_issues: 1 }] } } })
    m(reconciliationApi.run).mockResolvedValue({ data: { data: { items: [
      { id: 'i1', kind_label: 'Completed payment without a wallet credit', note: 'PAY-ABC: no wallet credit', resolved: false }] } } })
    m(reconciliationApi.resolveItem).mockResolvedValue({})
    const r = render(<AdminReconciliationScreen />)
    fireEvent.press(await r.findByText('View'))
    fireEvent.press(await r.findByText('Resolve'))
    fireEvent.press(r.getByText('Mark resolved'))
    expect(reconciliationApi.resolveItem).not.toHaveBeenCalled()
    fireEvent.changeText(r.getByLabelText('Resolution note'), 'Credited manually')
    fireEvent.press(r.getByText('Mark resolved'))
    await waitFor(() => expect(reconciliationApi.resolveItem).toHaveBeenCalledWith('i1', 'Credited manually'))
  })
})

describe('AdminProfileScreen', () => {
  it('shows the admin, the notification preferences card, and signs out', async () => {
    const logout = jest.fn()
    m(useAuthStore).mockReturnValue({ user: { first_name: 'Ada', last_name: 'Admin', email: 'ada@fridah.co.ke' }, logout })
    m(notificationsApi.preferences).mockResolvedValue({ data: { sms_enabled: true, push_enabled: true, email_enabled: false, payment_alerts: true, maintenance_alerts: true, quiet_hours_start: null, quiet_hours_end: null } })
    const r = render(<AdminProfileScreen />)
    expect(r.getByText('Ada Admin')).toBeTruthy()
    expect(await r.findByText('Notifications')).toBeTruthy()
    fireEvent.press(r.getByText('Sign out'))
    expect(logout).toHaveBeenCalled()
  })
})


describe('AdminDashboardScreen', () => {
  it('shows an error, never made-up figures, when the platform stats cannot be loaded', async () => {
    m(useAuthStore).mockReturnValue({ user: { first_name: 'Ada' }, logout: jest.fn() })
    m(analyticsApi.adminDashboard).mockRejectedValue(new Error('network'))
    const r = render(<AdminDashboardScreen />)
    expect(await r.findByText('Could not load the platform figures.')).toBeTruthy()
    expect(r.queryByText('342')).toBeNull()
  })
})
