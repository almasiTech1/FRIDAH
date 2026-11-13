export const formatKES = (amount: number | string): string => {
  const n = typeof amount === 'string' ? parseFloat(amount) : amount
  return `KES ${n.toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export const formatDate = (dateStr: string): string => {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('en-KE', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
}

export const formatDateTime = (dateStr: string): string => {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleString('en-KE', {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  })
}

export const relativeTime = (dateStr: string): string => {
  const diff = Date.now() - new Date(dateStr).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'Just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

export const statusColor = (status: string): string => {
  const map: Record<string, string> = {
    active: '#16a34a', confirmed: '#16a34a', paid: '#16a34a', verified: '#16a34a',
    completed: '#16a34a', resolved: '#16a34a', checked_in: '#16a34a',
    pending: '#d97706', pending_payment: '#d97706', processing: '#d97706',
    pending_approval: '#d97706', partially_paid: '#d97706', quoted: '#2563eb',
    assigned: '#2563eb', in_progress: '#2563eb', open: '#2563eb',
    overdue: '#dc2626', failed: '#dc2626', cancelled: '#dc2626', rejected: '#dc2626',
    suspended: '#dc2626', terminated: '#dc2626',
    requested: '#d97706', paid_out: '#16a34a', disputed: '#dc2626', approved: '#16a34a', awaiting_landlord: '#d97706', awaiting_admin: '#d97706',
    changes_requested: '#2563eb', estimated: '#d97706', assessed: '#2563eb',
  }
  return map[status] ?? '#6b7280'
}

export const statusBg = (status: string): string => {
  const map: Record<string, string> = {
    active: '#dcfce7', confirmed: '#dcfce7', paid: '#dcfce7', verified: '#dcfce7',
    completed: '#dcfce7', resolved: '#dcfce7', checked_in: '#dcfce7',
    pending: '#fef3c7', pending_payment: '#fef3c7', processing: '#fef3c7',
    pending_approval: '#fef3c7', partially_paid: '#fef3c7',
    assigned: '#dbeafe', in_progress: '#dbeafe', open: '#dbeafe', quoted: '#dbeafe',
    overdue: '#fee2e2', failed: '#fee2e2', cancelled: '#fee2e2', rejected: '#fee2e2',
    requested: '#fef3c7', paid_out: '#dcfce7', disputed: '#fee2e2', approved: '#dcfce7', awaiting_landlord: '#fef3c7', awaiting_admin: '#fef3c7',
    changes_requested: '#dbeafe', estimated: '#fef3c7', assessed: '#dbeafe',
  }
  return map[status] ?? '#f3f4f6'
}

export const priorityColor = (p: string): string =>
  ({ low: '#6b7280', medium: '#2563eb', high: '#d97706', urgent: '#dc2626' }[p] ?? '#6b7280')

export const truncate = (str: string, len = 60): string =>
  str && str.length > len ? str.slice(0, len) + '…' : str

export const reviewStateLabel = (state: string): string => ({
  awaiting_landlord: 'Awaiting landlord approval',
  awaiting_admin: 'Awaiting admin approval',
  approved: 'Approved & live',
  changes_requested: 'Changes requested',
  rejected: 'Rejected',
  withdrawn: 'Withdrawn',
} as Record<string, string>)[state] ?? state

export const partyLabel = (party: string): string => ({
  landlord: 'Landlord', admin: 'Administrator', agency: 'Agency', system: 'System',
} as Record<string, string>)[party] ?? party

export const refundStatusLabel = (s: string): string => ({
  requested: 'Awaiting approval', approved: 'Approved - payout pending', paid_out: 'Paid out',
  rejected: 'Rejected', cancelled: 'Cancelled',
} as Record<string, string>)[s] ?? s
