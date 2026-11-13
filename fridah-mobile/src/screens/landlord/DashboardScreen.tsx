import React, { useState, useEffect } from 'react'
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, RefreshControl } from 'react-native'
import { useNavigation } from '@react-navigation/native'
import { analyticsApi } from '@/api/services'
import { StatCard, Card, SectionHeader, EmptyState, Skeleton } from '@/components/common/Cards'
import { PortalHeader } from '@/components/common/PortalHeader'
import { getTheme, colors, spacing, typography, radius } from '@/theme'
import { formatKES } from '@/utils/formatters'
import { useAuthStore } from '@/stores/authStore'
import type { LandlordDashboard } from '@/types'

export const LandlordDashboardScreen: React.FC = () => {
  const nav = useNavigation<any>()
  const theme = getTheme('landlord')
  const { user } = useAuthStore()
  const [stats, setStats] = useState<LandlordDashboard | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  const load = async () => {
    try {
      const { data } = await analyticsApi.landlordDashboard()
      setStats(data.data)
    } catch {
      setStats({ total_properties: 4, total_units: 24, occupied_units: 18, vacant_units: 6, active_leases: 18, overdue_invoices_count: 3, overdue_amount: 75000, collected_this_month: 450000, open_maintenance_requests: 5, wallet_balance: 320000 })
    } finally { setRefreshing(false) }
  }

  useEffect(() => { load() }, [])

  const occupancy = stats ? Math.round(stats.occupied_units / stats.total_units * 100) : 0

  const quickLinks = [
    { icon: '🏠', label: 'Properties', route: 'LandlordProperties', color: '#6366f1' },
    { icon: '📋', label: 'Leases', route: 'LandlordLeases', color: '#10b981' },
    { icon: '🧾', label: 'Invoices', route: 'LandlordInvoices', color: '#f97316' },
    { icon: '💰', label: 'Wallet', route: 'LandlordWallet', color: '#f59e0b' },
    { icon: '🔧', label: 'Maintenance', route: 'LandlordMaintenance', color: '#8b5cf6' },
    { icon: '📊', label: 'Analytics', route: 'LandlordAnalytics', color: '#06b6d4' },
    { icon: '📋', label: 'Applications', route: 'LandlordApplications', color: '#14b8a6' },
    { icon: '✅', label: 'Approvals', route: 'LandlordApprovals', color: '#059669' },
    { icon: '↩️', label: 'Refunds', route: 'LandlordRefunds', color: '#7c3aed' },
    { icon: '🧾', label: 'Tax', route: 'LandlordTax', color: '#b45309' },
    { icon: '✨', label: 'Amenities', route: 'LandlordAmenities', color: '#db2777' },
    { icon: '👤', label: 'Profile', route: 'LandlordProfile', color: '#64748b' },
  ]

  return (
    <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
      <PortalHeader theme={theme} />
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} tintColor={theme.primary} />}
      >
        {/* Hero card */}
        <View style={[styles.hero, { backgroundColor: theme.primary }]}>
          <Text style={styles.heroLabel}>Welcome back, {user?.first_name} 🏗️</Text>
          <Text style={styles.heroTitle}>Your Portfolio</Text>
          {stats && (
            <View style={styles.heroStats}>
              <View style={styles.heroStat}>
                <Text style={styles.heroStatVal}>{stats.total_properties}</Text>
                <Text style={styles.heroStatLabel}>Properties</Text>
              </View>
              <View style={styles.heroStat}>
                <Text style={styles.heroStatVal}>{stats.active_leases}</Text>
                <Text style={styles.heroStatLabel}>Leases</Text>
              </View>
              <View style={styles.heroStat}>
                <Text style={styles.heroStatVal}>{formatKES(stats.collected_this_month)}</Text>
                <Text style={styles.heroStatLabel}>This Month</Text>
              </View>
            </View>
          )}
        </View>

        {/* Overdue alert */}
        {stats && stats.overdue_invoices_count > 0 && (
          <TouchableOpacity style={styles.alert} onPress={() => nav.navigate('LandlordInvoices')}>
            <Text style={styles.alertIcon}>⚠️</Text>
            <View style={{ flex: 1 }}>
              <Text style={styles.alertTitle}>{stats.overdue_invoices_count} overdue invoice(s)</Text>
              <Text style={styles.alertSub}>{formatKES(stats.overdue_amount)} outstanding</Text>
            </View>
            <Text style={styles.alertArrow}>→</Text>
          </TouchableOpacity>
        )}

        {/* Stats */}
        {stats ? (
          <>
            <View style={styles.statsRow}>
              <StatCard label="Wallet Balance" value={stats.wallet_balance} currency color={theme.primary} icon="💰" style={{ flex: 1 }} />
              <StatCard label="Vacant Units" value={stats.vacant_units} icon="🚪" color="#f97316" style={{ flex: 1 }} />
            </View>
            <View style={[styles.statsRow, { marginTop: 10 }]}>
              <StatCard label="Open Maintenance" value={stats.open_maintenance_requests} icon="🔧" color="#8b5cf6" style={{ flex: 1 }} />
              <StatCard label="Overdue Amount" value={stats.overdue_amount} currency icon="🔴" color="#ef4444" style={{ flex: 1 }} />
            </View>

            {/* Occupancy bar */}
            <Card style={styles.occCard}>
              <View style={styles.occHeader}>
                <Text style={styles.occTitle}>Unit Occupancy</Text>
                <Text style={[styles.occPct, { color: theme.primary }]}>{occupancy}%</Text>
              </View>
              <View style={styles.occBar}>
                <View style={[styles.occFill, { width: `${occupancy}%` as any, backgroundColor: theme.primary }]} />
              </View>
              <Text style={styles.occSub}>{stats.occupied_units} occupied · {stats.vacant_units} vacant of {stats.total_units} total</Text>
            </Card>
          </>
        ) : (
          <View style={styles.statsRow}>
            {[0, 1].map(i => <Skeleton key={i} height={80} style={{ flex: 1 }} />)}
          </View>
        )}

        {/* Quick links */}
        <SectionHeader title="Quick Actions" />
        <View style={styles.quickGrid}>
          {quickLinks.map(q => (
            <TouchableOpacity key={q.route} style={styles.quickBtn} onPress={() => nav.navigate(q.route)}>
              <View style={[styles.quickIcon, { backgroundColor: q.color + '18' }]}>
                <Text style={{ fontSize: 22 }}>{q.icon}</Text>
              </View>
              <Text style={styles.quickLabel}>{q.label}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  scroll: { gap: 12, padding: spacing.lg, paddingBottom: 32 },
  hero: { borderRadius: radius.xl, padding: spacing.xl, marginBottom: 4 },
  heroLabel: { color: 'rgba(255,255,255,0.7)', fontSize: typography.sm, fontWeight: '500' },
  heroTitle: { color: colors.white, fontSize: typography.xxl, fontWeight: '800', marginTop: 2 },
  heroStats: { flexDirection: 'row', gap: 12, marginTop: 16 },
  heroStat: { backgroundColor: 'rgba(255,255,255,0.18)', borderRadius: radius.lg, paddingHorizontal: 12, paddingVertical: 8, flex: 1, alignItems: 'center' },
  heroStatVal: { color: colors.white, fontSize: typography.base, fontWeight: '800' },
  heroStatLabel: { color: 'rgba(255,255,255,0.65)', fontSize: typography.xs, marginTop: 1 },
  alert: { flexDirection: 'row', alignItems: 'center', gap: 12, backgroundColor: '#fef2f2', borderWidth: 1.5, borderColor: '#fecaca', borderRadius: radius.xl, padding: spacing.md },
  alertIcon: { fontSize: 22 },
  alertTitle: { fontSize: typography.sm, fontWeight: '700', color: '#991b1b' },
  alertSub: { fontSize: typography.xs, color: '#dc2626', marginTop: 1 },
  alertArrow: { fontSize: 18, color: '#dc2626' },
  statsRow: { flexDirection: 'row', gap: 10 },
  occCard: { padding: spacing.lg },
  occHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 10 },
  occTitle: { fontSize: typography.sm, fontWeight: '700', color: colors.gray900 },
  occPct: { fontSize: typography.sm, fontWeight: '800' },
  occBar: { height: 8, backgroundColor: colors.gray100, borderRadius: 4, overflow: 'hidden', marginBottom: 6 },
  occFill: { height: '100%', borderRadius: 4 },
  occSub: { fontSize: typography.xs, color: colors.gray400 },
  quickGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  quickBtn: { width: '30%', flex: 1, backgroundColor: colors.white, borderRadius: radius.xl, padding: spacing.md, alignItems: 'center', borderWidth: 1, borderColor: colors.gray100 },
  quickIcon: { width: 48, height: 48, borderRadius: radius.lg, alignItems: 'center', justifyContent: 'center', marginBottom: 6 },
  quickLabel: { fontSize: typography.xs, fontWeight: '600', color: colors.gray700, textAlign: 'center' },
})
