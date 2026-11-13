import React, { useState, useEffect } from 'react'
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, RefreshControl } from 'react-native'
import { useNavigation } from '@react-navigation/native'
import { analyticsApi } from '@/api/services'
import { StatCard, Card, SectionHeader, Skeleton } from '@/components/common/Cards'
import { PortalHeader } from '@/components/common/PortalHeader'
import { getTheme, colors, spacing, typography, radius } from '@/theme'
import { formatKES } from '@/utils/formatters'
import type { AdminDashboard } from '@/types'

export const AdminDashboardScreen: React.FC = () => {
  const nav = useNavigation<any>()
  const theme = getTheme('admin')
  const [stats, setStats] = useState<AdminDashboard | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [loadError, setLoadError] = useState(false)

  const load = async () => {
    setLoadError(false)
    try { const { data } = await analyticsApi.adminDashboard(); setStats(data.data) }
    catch { setLoadError(true) }
    finally { setRefreshing(false) }
  }
  useEffect(() => { load() }, [])

  const alerts = stats ? [
    { icon: '🔒', label: 'Pending KYC', count: stats.pending_kyc, color: '#f59e0b', route: 'AdminKYC' },
    { icon: '🏠', label: 'Pending Properties', count: stats.pending_property_approvals, color: '#6366f1', route: 'AdminProperties' },
    { icon: '🏨', label: 'Pending Listings', count: stats.pending_listing_approvals, color: '#10b981', route: 'AdminProperties' },
  ] : []

  return (
    <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
      <PortalHeader theme={theme} />
      <ScrollView
        contentContainerStyle={{ padding: spacing.lg, gap: 12 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} tintColor={theme.primary} />}
      >
        <View style={[styles.hero, { backgroundColor: theme.primary }]}>
          <Text style={styles.heroLabel}>Admin Control Panel ⚙️</Text>
          <Text style={styles.heroTitle}>Platform Overview</Text>
          {stats && (
            <View style={styles.heroRow}>
              {[{ l: 'Users', v: stats.total_users }, { l: 'Revenue', v: formatKES(stats.total_revenue_this_month) }, { l: 'Signups', v: `+${stats.new_signups_this_month}` }].map(h => (
                <View key={h.l} style={styles.heroBadge}>
                  <Text style={styles.heroBadgeVal}>{h.v}</Text>
                  <Text style={styles.heroBadgeLbl}>{h.l}</Text>
                </View>
              ))}
            </View>
          )}
        </View>

        <View style={styles.quick}>
          {[{ l: 'Agencies', r: 'AdminAgencies', i: '🏢' }, { l: 'Refunds', r: 'AdminRefunds', i: '↩️' }, { l: 'Reconcile', r: 'AdminReconciliation', i: '⚖️' },
            { l: 'Review queue', r: 'AdminReviewQueue', i: '✅' }, { l: 'My account', r: 'AdminProfile', i: '👤' }].map((q) => (
            <TouchableOpacity key={q.r} style={styles.quickBtn} accessibilityRole="button" accessibilityLabel={q.l} onPress={() => nav.navigate(q.r)}>
              <Text style={{ fontSize: 20 }}>{q.i}</Text><Text style={styles.quickLbl}>{q.l}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {alerts.map(a => (
          <TouchableOpacity key={a.label} style={[styles.alertCard, { borderColor: a.color + '40' }]} onPress={() => nav.navigate(a.route)}>
            <View style={[styles.alertCount, { backgroundColor: a.color + '20' }]}>
              <Text style={[styles.alertNum, { color: a.color }]}>{a.count}</Text>
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.alertLabel}>{a.label}</Text>
              <Text style={styles.alertSub}>Requires review</Text>
            </View>
            <Text style={styles.alertArrow}>→</Text>
          </TouchableOpacity>
        ))}

        {loadError ? (
          <View style={styles.errorBox} accessibilityRole="alert">
            <Text style={{ color: '#b91c1c', fontWeight: '600' }}>Could not load the platform figures.</Text>
            <Text style={{ color: '#6b7280', fontSize: 12 }}>Pull down to try again. Nothing is shown rather than showing wrong numbers.</Text>
          </View>
        ) : stats ? (
          <View style={{ gap: 10 }}>
            <View style={styles.statRow}>
              <StatCard label="Total Users" value={stats.total_users} icon="👥" color={theme.primary} style={{ flex: 1 }} />
              <StatCard label="Properties" value={stats.total_properties} icon="🏠" color="#6366f1" style={{ flex: 1 }} />
            </View>
            <View style={styles.statRow}>
              <StatCard label="Active Leases" value={stats.active_leases} icon="📋" color="#10b981" style={{ flex: 1 }} />
              <StatCard label="Commission" value={stats.total_revenue_this_month - stats.total_payouts_this_month} currency icon="💹" color="#f59e0b" style={{ flex: 1 }} />
            </View>
          </View>
        ) : (
          <View style={styles.statRow}><Skeleton height={80} style={{ flex: 1 }} /><Skeleton height={80} style={{ flex: 1 }} /></View>
        )}

        {stats && (
          <Card style={{ padding: spacing.lg }}>
            <SectionHeader title="Users by Role" />
            {Object.entries(stats.users_by_role).map(([role, count]) => (
              <View key={role} style={{ marginBottom: 10 }}>
                <View style={styles.barLabel}>
                  <Text style={styles.roleName}>{role.replace(/_/g, ' ')}</Text>
                  <Text style={styles.roleCount}>{count as number}</Text>
                </View>
                <View style={styles.barTrack}>
                  <View style={[styles.barFill, { width: `${Math.round((count as number) / stats.total_users * 100)}%` as any, backgroundColor: theme.primary }]} />
                </View>
              </View>
            ))}
          </Card>
        )}
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  errorBox: { backgroundColor: '#fef2f2', borderColor: '#fecaca', borderWidth: 1, borderRadius: 12, padding: 14, gap: 4 },
  quick: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  quickBtn: { width: '31%', backgroundColor: colors.white, borderRadius: radius.lg, paddingVertical: 12, alignItems: 'center', gap: 4, borderWidth: 1, borderColor: colors.gray100 },
  quickLbl: { fontSize: typography.xs, fontWeight: '600', color: colors.gray700 },
  hero: { borderRadius: radius.xl, padding: spacing.xl },
  heroLabel: { color: 'rgba(255,255,255,0.7)', fontSize: typography.sm, fontWeight: '500' },
  heroTitle: { color: colors.white, fontSize: typography.xxl, fontWeight: '800', marginTop: 2 },
  heroRow: { flexDirection: 'row', gap: 10, marginTop: 16 },
  heroBadge: { flex: 1, backgroundColor: 'rgba(255,255,255,0.18)', borderRadius: radius.lg, padding: 10, alignItems: 'center' },
  heroBadgeVal: { color: colors.white, fontSize: typography.sm, fontWeight: '800' },
  heroBadgeLbl: { color: 'rgba(255,255,255,0.6)', fontSize: typography.xs, marginTop: 2 },
  alertCard: { flexDirection: 'row', alignItems: 'center', gap: 12, backgroundColor: colors.white, borderRadius: radius.xl, borderWidth: 1.5, padding: spacing.md },
  alertCount: { width: 44, height: 44, borderRadius: radius.lg, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  alertNum: { fontSize: typography.lg, fontWeight: '800' },
  alertLabel: { fontSize: typography.sm, fontWeight: '700', color: colors.gray900 },
  alertSub: { fontSize: typography.xs, color: colors.gray400 },
  alertArrow: { fontSize: 18, color: colors.gray300 },
  statRow: { flexDirection: 'row', gap: 10 },
  barLabel: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
  roleName: { fontSize: typography.xs, fontWeight: '500', color: colors.gray600, textTransform: 'capitalize' },
  roleCount: { fontSize: typography.xs, fontWeight: '700', color: colors.gray900 },
  barTrack: { height: 6, backgroundColor: colors.gray100, borderRadius: 3, overflow: 'hidden' },
  barFill: { height: '100%', borderRadius: 3 },
})
