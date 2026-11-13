import { reviewStateLabel, partyLabel, statusColor } from '../formatters'

describe('approval workflow labels', () => {
  it('names every review state in plain language', () => {
    expect(reviewStateLabel('awaiting_landlord')).toBe('Awaiting landlord approval')
    expect(reviewStateLabel('awaiting_admin')).toBe('Awaiting admin approval')
    expect(reviewStateLabel('approved')).toBe('Approved & live')
    expect(reviewStateLabel('changes_requested')).toBe('Changes requested')
    expect(reviewStateLabel('rejected')).toBe('Rejected')
    expect(reviewStateLabel('withdrawn')).toBe('Withdrawn')
  })

  it('falls back to the raw value for unknown states instead of crashing', () => {
    expect(reviewStateLabel('something_new')).toBe('something_new')
  })

  it('names the approving parties', () => {
    expect(partyLabel('landlord')).toBe('Landlord')
    expect(partyLabel('admin')).toBe('Administrator')
    expect(partyLabel('agency')).toBe('Agency')
    expect(partyLabel('system')).toBe('System')
    expect(partyLabel('other')).toBe('other')
  })

  it('gives the new states a colour so badges are never blank', () => {
    for (const s of ['approved', 'awaiting_landlord', 'awaiting_admin', 'changes_requested', 'estimated', 'assessed']) {
      expect(statusColor(s)).toBeTruthy()
    }
  })
})
