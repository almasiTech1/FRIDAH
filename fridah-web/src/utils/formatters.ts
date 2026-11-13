export const formatKES = (amount: number | string): string => {
  const n = typeof amount === 'string' ? parseFloat(amount) : amount
  return `KES ${n.toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export const formatDate = (dateStr: string): string => {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('en-KE', { day: 'numeric', month: 'short', year: 'numeric' })
}

export const formatDateTime = (dateStr: string): string => {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleString('en-KE', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
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
    active: 'badge-green', confirmed: 'badge-green', paid: 'badge-green', verified: 'badge-green',
    completed: 'badge-green', resolved: 'badge-green', checked_in: 'badge-green',
    pending: 'badge-yellow', pending_payment: 'badge-yellow', processing: 'badge-yellow',
    pending_approval: 'badge-yellow', partially_paid: 'badge-yellow', assigned: 'badge-blue',
    in_progress: 'badge-blue', quoted: 'badge-blue', open: 'badge-blue',
    overdue: 'badge-red', failed: 'badge-red', cancelled: 'badge-red', rejected: 'badge-red',
    suspended: 'badge-red', terminated: 'badge-red',
    vacant: 'badge-green', occupied: 'badge-blue', maintenance: 'badge-yellow',
    // property approval workflow + tax records
    approved: 'badge-green', awaiting_landlord: 'badge-yellow', awaiting_admin: 'badge-yellow',
    requested: 'badge-yellow', paid_out: 'badge-green', disputed: 'badge-red', reversed: 'badge-gray', refunded: 'badge-gray',
    changes_requested: 'badge-blue', withdrawn: 'badge-gray', estimated: 'badge-yellow', assessed: 'badge-blue',
  }
  return map[status] ?? 'badge-gray'
}

export const priorityColor = (priority: string): string => ({
  low: 'badge-gray', medium: 'badge-blue', high: 'badge-yellow', urgent: 'badge-red'
})[priority] ?? 'badge-gray'

export const truncate = (str: string, len = 50): string =>
  str && str.length > len ? str.slice(0, len) + '…' : str

export const reviewStateLabel = (state: string): string => ({
  awaiting_landlord: 'Awaiting landlord approval',
  awaiting_admin: 'Awaiting admin approval',
  approved: 'Approved & live',
  changes_requested: 'Changes requested',
  rejected: 'Rejected',
  withdrawn: 'Withdrawn',
})[state] ?? state

export const partyLabel = (party: string): string => ({
  landlord: 'Landlord', admin: 'Administrator', agency: 'Agency', system: 'System',
})[party] ?? party

export const refundStatusLabel = (s: string): string => ({
  requested: 'Awaiting approval', approved: 'Approved - payout pending', paid_out: 'Paid out',
  rejected: 'Rejected', cancelled: 'Cancelled',
})[s] ?? s
