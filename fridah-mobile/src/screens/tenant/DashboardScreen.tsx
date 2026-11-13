import React, { useEffect, useState } from 'react'
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, RefreshControl, TextInput } from 'react-native'
import { useNavigation } from '@react-navigation/native'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/authStore'
import { analyticsApi, rentalsApi, renewalsApi } from '@/api/services'
import { StatCard, Card, SectionHeader, StatusBadge, EmptyState, Skeleton } from '@/components/common/Cards'
import { Button } from '@/components/common/Button'
import { PortalHeader } from '@/components/common/PortalHeader'
import { getTheme } from '@/theme'
import { formatKES, formatDate } from '@/utils/formatters'
import { colors, spacing, typography, radius } from '@/theme'
import type { TenantDashboard, Lease, Invoice } from '@/types'

interface Renewal {
  id: string
  status: string
  proposed_rent_amount: number
  proposed_start_date: string
  proposed_end_date: string
}

export const TenantDashboardScreen: React.FC = () => {
  const nav = useNavigation<any>()
  const { user } = useAuthStore()
  const { t } = useTranslation()
  const theme = getTheme('tenant')
  const [stats, setStats] = useState<TenantDashboard | null>(null)
  const [lease, setLease] = useState<Lease | null>(null)
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [renewal, setRenewal] = useState<Renewal | null>(null)
  const [showDecline, setShowDecline] = useState(false)
  const [declineReason, setDeclineReason] = useState('')
  const [responding, setResponding] = useState(false)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const load = async () => {
    try {
      const [dashRes, leaseRes, invRes, renewalRes] = await Promise.all([
        analyticsApi.tenantDashboard(),
        rentalsApi.leases({ status: 'active' }),
        rentalsApi.invoices(),
        renewalsApi.list(),
      ])
      setStats(dashRes.data.data)
      const leases = leaseRes.data.data?.results || []
      setLease(leases[0] || null)
      setInvoices((invRes.data.data?.results || []).slice(0, 5))
      const renewals = (renewalRes.data as any).data?.results || (renewalRes.data as any).data || []
      setRenewal(renewals[0] || null)
    } catch {
      setStats({ pending_invoices_count: 2, pending_balance: 50000, open_maintenance_requests: 1, total_paid_this_year: 150000, rent_amount: 25000 })
    } finally {
      setLoading(false); setRefreshing(false)
    }
  }

  const respond = async (accept: boolean) => {
    if (!renewal) return
    setResponding(true)
    try {
      await renewalsApi.respond(renewal.id, accept, declineReason)
      await load()
    } finally {
      setResponding(false); setShowDecline(false)
    }
  }

  useEffect(() => { load() }, [])

  return (
    <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
      <PortalHeader theme={theme} onNotifPress={() => nav.navigate('TenantNotifications')} />
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} tintColor={theme.primary} />}
      >
        {/* KYC Alert */}
        {!user?.is_kyc_verified && (
          <TouchableOpacity style={styles.kycAlert} onPress={() => nav.navigate('TenantProfile')}>
            <Text style={styles.kycIcon}>🔒</Text>
            <View style={{ flex: 1 }}>
              <Text style={styles.kycTitle}>Complete KYC Verification</Text>
              <Text style={styles.kycSub}>Tap to upload your National ID</Text>
            </View>
            <Text style={styles.kycArrow}>→</Text>
          </TouchableOpacity>
        )}

        {/* Lease Renewal Banner */}
        {renewal && renewal.status === 'pending' && (
          <Card style={[styles.section, styles.renewalCard, { borderColor: theme.primary }]}>
            <View style={styles.sectionHead}>
              <SectionHeader title={t('renewal.title')} />
              <View style={[styles.pendingPill, { backgroundColor: '#fef3c7' }]}>
                <Text style={styles.pendingPillText}>{t('renewal.pending')}</Text>
              </View>
            </View>
            <View style={styles.leaseGrid}>
              <View style={styles.leaseItem}>
                <Text style={styles.leaseLabel}>{t('renewal.proposedRent')}</Text>
                <Text style={[styles.leaseVal, { fontSize: typography.base }]}>{formatKES(renewal.proposed_rent_amount)}</Text>
              </View>
              <View style={styles.leaseItem}>
                <Text style={styles.leaseLabel}>{t('renewal.proposedTerm')}</Text>
                <Text style={styles.leaseVal}>{formatDate(renewal.proposed_start_date)} - {formatDate(renewal.proposed_end_date)}</Text>
              </View>
            </View>
            {showDecline ? (
              <>
                <TextInput
                  style={styles.declineInput}
                  placeholder={t('renewal.declineReasonPlaceholder') as string}
                  placeholderTextColor={colors.gray400}
                  value={declineReason}
                  onChangeText={setDeclineReason}
                  multiline
                />
                <View style={styles.renewalBtnRow}>
                  <Button label={t('renewal.confirmDecline')} color={colors.red500} onPress={() => respond(false)} loading={responding} style={{ flex: 1 }} />
                  <Button label="Cancel" variant="outline" onPress={() => setShowDecline(false)} style={{ flex: 1 }} />
                </View>
              </>
            ) : (
              <View style={styles.renewalBtnRow}>
                <Button label={t('renewal.accept')} color={theme.primary} onPress={() => respond(true)} loading={responding} style={{ flex: 1 }} />
                <Button label={t('renewal.decline')} variant="outline" onPress={() => setShowDecline(true)} style={{ flex: 1 }} />
              </View>
            )}
          </Card>
        )}

        {/* Stats */}
        {loading ? (
          <View style={styles.statsGrid}>
            {[0,1,2,3].map(i => <Skeleton key={i} height={80} style={{ flex: 1 }} />)}
          </View>
        ) : (
          <View style={styles.statsGrid}>
            <StatCard label="Monthly Rent" value={stats?.rent_amount || 0} currency style={{ flex: 1 }} color={theme.primary} />
            <StatCard label="Pending Balance" value={stats?.pending_balance || 0} currency style={{ flex: 1 }} />
          </View>
        )}
        {!loading && (
          <View style={[styles.statsGrid, { marginTop: 10 }]}>
            <StatCard label="Unpaid Invoices" value={stats?.pending_invoices_count || 0} style={{ flex: 1 }} />
            <StatCard label="Open Maintenance" value={stats?.open_maintenance_requests || 0} style={{ flex: 1 }} />
          </View>
        )}

        {/* Active Lease */}
        {lease && (
          <Card style={styles.section}>
            <SectionHeader title="Active Lease" />
            <View style={styles.leaseGrid}>
              <View style={styles.leaseItem}><Text style={styles.leaseLabel}>Property</Text><Text style={styles.leaseVal}>{lease.property_name}</Text></View>
              <View style={styles.leaseItem}><Text style={styles.leaseLabel}>Unit</Text><Text style={styles.leaseVal}>{lease.unit_number}</Text></View>
              <View style={styles.leaseItem}><Text style={styles.leaseLabel}>Start</Text><Text style={styles.leaseVal}>{formatDate(lease.start_date)}</Text></View>
              <View style={styles.leaseItem}><Text style={styles.leaseLabel}>Due Day</Text><Text style={styles.leaseVal}>Day {lease.rent_due_day}</Text></View>
            </View>
          </Card>
        )}

        {/* Quick actions */}
        <View style={styles.quickRow}>
          {[
            { icon: '🧾', label: 'Invoices', route: 'TenantInvoices' },
            { icon: '🔧', label: 'Maintenance', route: 'TenantMaintenance' },
            { icon: '🏠', label: 'Browse', route: 'TenantProperties' },
            { icon: '💳', label: 'Payments', route: 'TenantPayments' },
            { icon: '📋', label: 'Applications', route: 'MyApplications' },
            { icon: '🏨', label: 'Stays', route: 'BrowseStays' },
            { icon: '🛎️', label: 'My Bookings', route: 'MyBookings' },
          ].map(q => (
            <TouchableOpacity key={q.route} style={styles.quickBtn} onPress={() => nav.navigate(q.route)}>
              <Text style={styles.quickIcon}>{q.icon}</Text>
              <Text style={styles.quickLabel}>{q.label}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Recent invoices */}
        <Card style={styles.section}>
          <View style={styles.sectionHead}>
            <SectionHeader title="Recent Invoices" />
            <TouchableOpacity onPress={() => nav.navigate('TenantInvoices')}>
              <Text style={[styles.viewAll, { color: theme.primary }]}>View all</Text>
            </TouchableOpacity>
          </View>
          {invoices.length === 0
            ? <EmptyState emoji="🧾" message="No invoices yet" />
            : invoices.map(inv => (
              <View key={inv.id} style={styles.invoiceRow}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.invoiceNum}>{inv.invoice_number}</Text>
                  <Text style={styles.invoicePeriod}>{formatDate(inv.period_start)}</Text>
                </View>
                <View style={{ alignItems: 'flex-end', gap: 4 }}>
                  <Text style={styles.invoiceAmt}>{formatKES(inv.amount)}</Text>
                  <StatusBadge status={inv.status} />
                </View>
              </View>
            ))
          }
        </Card>
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  scroll: { padding: spacing.lg, gap: 12 },
  kycAlert: {
    backgroundColor: '#fef3c7', borderRadius: radius.lg,
    padding: spacing.md, flexDirection: 'row', alignItems: 'center', gap: 10,
    borderWidth: 1, borderColor: '#fde68a',
  },
  kycIcon: { fontSize: 20 },
  kycTitle: { fontSize: typography.sm, fontWeight: '600', color: '#92400e' },
  kycSub: { fontSize: typography.xs, color: '#b45309', marginTop: 2 },
  kycArrow: { fontSize: 18, color: '#92400e' },
  renewalCard: { borderWidth: 2 },
  pendingPill: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: radius.full, marginBottom: spacing.md },
  pendingPillText: { fontSize: typography.xs, fontWeight: '700', color: '#92400e' },
  declineInput: {
    borderWidth: 1, borderColor: colors.gray200, borderRadius: radius.md,
    padding: spacing.md, fontSize: typography.sm, minHeight: 60, marginBottom: 10,
    color: colors.gray900, textAlignVertical: 'top',
  },
  renewalBtnRow: { flexDirection: 'row', gap: 8 },
  statsGrid: { flexDirection: 'row', gap: 10 },
  section: { marginTop: 4 },
  sectionHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  viewAll: { fontSize: typography.sm, fontWeight: '600', marginBottom: spacing.md },
  leaseGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  leaseItem: { width: '45%' },
  leaseLabel: { fontSize: typography.xs, color: colors.gray500 },
  leaseVal: { fontSize: typography.sm, fontWeight: '600', color: colors.gray900, marginTop: 2 },
  quickRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  quickBtn: {
    width: '31%', backgroundColor: colors.white, borderRadius: radius.lg,
    padding: spacing.md, alignItems: 'center', borderWidth: 1, borderColor: colors.gray100,
  },
  quickIcon: { fontSize: 22, marginBottom: 4 },
  quickLabel: { fontSize: typography.xs, fontWeight: '500', color: colors.gray700 },
  invoiceRow: {
    flexDirection: 'row', justifyContent: 'space-between',
    paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: colors.gray100,
  },
  invoiceNum: { fontSize: typography.xs, fontFamily: 'monospace', color: colors.gray600, fontWeight: '600' },
  invoicePeriod: { fontSize: typography.xs, color: colors.gray400, marginTop: 2 },
  invoiceAmt: { fontSize: typography.sm, fontWeight: '700', color: colors.gray900 },
})
