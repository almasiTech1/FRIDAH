import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('@/api/services', () => ({
  approvalApi: {
    queue: vi.fn(), history: vi.fn(), landlordDecision: vi.fn(), adminDecision: vi.fn(),
  },
  notificationsApi: { preferences: vi.fn(), updatePreferences: vi.fn() },
  agencyApi: { list: vi.fn(), create: vi.fn(), setStatus: vi.fn(), resetAdminPassword: vi.fn() },
}))

import { approvalApi, notificationsApi, agencyApi } from '@/api/services'
import PropertyReviewList from '@/components/common/PropertyReviewList.vue'
import NotificationPreferences from '@/components/common/NotificationPreferences.vue'
import Agencies from '@/portals/admin/views/Agencies.vue'
import { reviewStateLabel, partyLabel } from '@/utils/formatters'

const item = {
  id: 'p1', name: 'Karen Heights', town: 'Karen', county: 'Nairobi', landlord_name: 'Jane Owner',
  submitted_by_agency: 'Prime PM', review_state: 'awaiting_landlord', submission_version: 2,
  requires_landlord_approval: true, missing_approvals: ['landlord', 'admin'], age_days: 4,
}
const queue = (rows: any[]) => (approvalApi.queue as any).mockResolvedValue({ data: { data: { results: rows } } })

beforeEach(() => vi.clearAllMocks())

describe('formatters', () => {
  it('labels states and parties, falling back to the raw value', () => {
    expect(reviewStateLabel('awaiting_admin')).toBe('Awaiting admin approval')
    expect(reviewStateLabel('mystery')).toBe('mystery')
    expect(partyLabel('admin')).toBe('Administrator')
  })
})

describe('PropertyReviewList', () => {
  it('shows what is still needed and how long it has waited', async () => {
    queue([item])
    const w = mount(PropertyReviewList, { props: { role: 'landlord' } })
    await flushPromises()
    expect(w.text()).toContain('Karen Heights')
    expect(w.text()).toContain('Waiting 4 days')
    expect(w.text()).toContain('Landlord and Administrator approval')
  })

  it('landlords decide through the landlord endpoint, admins through the admin endpoint', async () => {
    queue([item])
    ;(approvalApi.landlordDecision as any).mockResolvedValue({})
    ;(approvalApi.adminDecision as any).mockResolvedValue({})
    const landlord = mount(PropertyReviewList, { props: { role: 'landlord' } })
    await flushPromises()
    await landlord.findAll('button').find((b) => b.text() === 'Approve')!.trigger('click')
    expect(approvalApi.landlordDecision).toHaveBeenCalledWith('p1', 'approve', '')
    expect(approvalApi.adminDecision).not.toHaveBeenCalled()

    const admin = mount(PropertyReviewList, { props: { role: 'admin' } })
    await flushPromises()
    await admin.findAll('button').find((b) => b.text() === 'Approve')!.trigger('click')
    expect(approvalApi.adminDecision).toHaveBeenCalledWith('p1', 'approve', '')
  })

  it('will not send a rejection without a reason', async () => {
    queue([item])
    ;(approvalApi.landlordDecision as any).mockResolvedValue({})
    const w = mount(PropertyReviewList, { props: { role: 'landlord' } })
    await flushPromises()
    await w.findAll('button').find((b) => b.text() === 'Reject')!.trigger('click')
    const send = w.findAll('button').find((b) => b.text() === 'Send')!
    expect((send.element as HTMLButtonElement).disabled).toBe(true)
    await w.find('textarea').setValue('Wrong estate')
    expect((send.element as HTMLButtonElement).disabled).toBe(false)
    await w.find('form').trigger('submit')
    expect(approvalApi.landlordDecision).toHaveBeenCalledWith('p1', 'reject', 'Wrong estate')
  })

  it('shows an empty state and a retry on failure', async () => {
    queue([])
    expect(mount(PropertyReviewList, { props: { role: 'admin' } }).html()).toBeTruthy()
    ;(approvalApi.queue as any).mockRejectedValue(new Error('down'))
    const w = mount(PropertyReviewList, { props: { role: 'admin' } })
    await flushPromises()
    expect(w.text()).toContain('Could not load the review queue')
    expect(w.text()).toContain('Try again')
  })
})

describe('NotificationPreferences quiet hours', () => {
  const prefs = { sms_enabled: true, push_enabled: true, email_enabled: false, payment_alerts: true, maintenance_alerts: true,
                  quiet_hours_start: '22:00:00', quiet_hours_end: '06:30:00' }

  it('loads saved quiet hours as HH:MM', async () => {
    ;(notificationsApi.preferences as any).mockResolvedValue({ data: prefs })
    const w = mount(NotificationPreferences)
    await flushPromises()
    expect((w.find('#qh-start').element as HTMLInputElement).value).toBe('22:00')
    expect((w.find('#qh-end').element as HTMLInputElement).value).toBe('06:30')
  })

  it('refuses to save only one of the two times', async () => {
    ;(notificationsApi.preferences as any).mockResolvedValue({ data: { ...prefs, quiet_hours_start: null, quiet_hours_end: null } })
    const w = mount(NotificationPreferences)
    await flushPromises()
    await w.find('#qh-start').setValue('21:00')
    await w.find('form').trigger('submit')
    expect(w.text()).toContain('Set both quiet-hours times')
    expect(notificationsApi.updatePreferences).not.toHaveBeenCalled()
  })

  it('sends null when both are cleared (platform default applies)', async () => {
    ;(notificationsApi.preferences as any).mockResolvedValue({ data: prefs })
    ;(notificationsApi.updatePreferences as any).mockResolvedValue({})
    const w = mount(NotificationPreferences)
    await flushPromises()
    await w.find('#qh-start').setValue('')
    await w.find('#qh-end').setValue('')
    await w.find('form').trigger('submit')
    await flushPromises()
    const sent = (notificationsApi.updatePreferences as any).mock.calls[0][0]
    expect(sent.quiet_hours_start).toBeNull()
    expect(sent.quiet_hours_end).toBeNull()
  })
})

describe('Admin Agencies page', () => {
  const fill = async (w: any) => {
    await w.find('#ag-fn').setValue('Kamau')
    await w.find('#ag-ln').setValue('Mwangi')
    await w.find('#ag-admin').setValue('kamau@primepm.co.ke')
    await w.find('#ag-aphone').setValue('+254700000071')
    await w.find('#ag-name').setValue('Prime Property Managers')
  }

  it('shows the temporary password once, then it can be dismissed and is gone', async () => {
    ;(agencyApi.list as any).mockResolvedValue({ data: { results: [] } })
    ;(agencyApi.create as any).mockResolvedValue({ data: { data: {
      id: 'a1', credentials: { login_email: 'kamau@primepm.co.ke', temporary_password: 'Abcd2345efgh' } } } })
    const w = mount(Agencies)
    await flushPromises()
    await w.find('button.btn').trigger('click')          // + Register agency
    await fill(w)
    await w.find('form').trigger('submit')
    await flushPromises()
    expect(w.text()).toContain('Abcd2345efgh')
    expect(w.text()).toContain('shown only once')
    expect((agencyApi.create as any).mock.calls[0][0]).toMatchObject({
      admin_first_name: 'Kamau', admin_email: 'kamau@primepm.co.ke', name: 'Prime Property Managers',
    })
    await w.findAll('button').find((b) => b.text().includes('I have saved it'))!.trigger('click')
    expect(w.text()).not.toContain('Abcd2345efgh')
  })

  it('surfaces the server\'s field errors next to the field', async () => {
    ;(agencyApi.list as any).mockResolvedValue({ data: { results: [] } })
    ;(agencyApi.create as any).mockRejectedValue({ response: { data: { admin_email: ['An account with this email already exists.'] } } })
    const w = mount(Agencies)
    await flushPromises()
    await w.find('button.btn').trigger('click')
    await fill(w)
    await w.find('form').trigger('submit')
    await flushPromises()
    expect(w.text()).toContain('An account with this email already exists.')
  })
})
