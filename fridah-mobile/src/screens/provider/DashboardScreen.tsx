import React, { useState, useEffect } from 'react'
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, RefreshControl } from 'react-native'
import { useNavigation } from '@react-navigation/native'
import { analyticsApi } from '@/api/services'
import { StatCard, Card, SectionHeader, Skeleton } from '@/components/common/Cards'
import { PortalHeader } from '@/components/common/PortalHeader'
import { getTheme, colors, spacing, typography, radius } from '@/theme'
import { formatKES } from '@/utils/formatters'
import { useAuthStore } from '@/stores/authStore'
import type { ServiceProviderDashboard } from '@/types'

export const ProviderDashboardScreen: React.FC = () => {
  const nav = useNavigation<any>()
  const theme = getTheme('service_provider')
  const { user } = useAuthStore()
  const [stats, setStats] = useState<ServiceProviderDashboard | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  const load = async () => {
    try { const { data } = await analyticsApi.serviceProviderDashboard(); setStats(data.data) }
    catch { setStats({ active_jobs: 2, completed_jobs: 18, pending_quotes: 3, accepted_quotes: 1, wallet_balance: 45000, available_open_jobs: 12 }) }
    finally { setRefreshing(false) }
  }
  useEffect(() => { load() }, [])

  const quickLinks = [
    { icon: '🔍', label: 'Browse Jobs', route: 'ProviderJobs', color: theme.primary },
    { icon: '🔧', label: 'My Jobs', route: 'ProviderMyJobs', color: '#6366f1' },
    { icon: '📝', label: 'My Quotes', route: 'ProviderMyJobs', color: '#10b981' },
    { icon: '💰', label: 'Wallet', route: 'ProviderWallet', color: '#f59e0b' },
  ]

  return (
    <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
      <PortalHeader theme={theme} />
      <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: 12 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} tintColor={theme.primary} />}>

        <View style={[styles.hero, { backgroundColor: theme.primary }]}>
          <Text style={styles.heroSub}>Welcome back, {user?.first_name} 🔧</Text>
          <Text style={styles.heroTitle}>Service Dashboard</Text>
          {stats && (
            <View style={styles.heroRow}>
              {[{ l: 'Active Jobs', v: stats.active_jobs }, { l: 'Completed', v: stats.completed_jobs }, { l: 'Wallet', v: formatKES(stats.wallet_balance) }].map(h => (
                <View key={h.l} style={styles.heroBadge}>
                  <Text style={styles.heroBadgeVal}>{h.v}</Text>
                  <Text style={styles.heroBadgeLbl}>{h.l}</Text>
                </View>
              ))}
            </View>
          )}
        </View>

        {stats ? (
          <View style={{ gap: 10 }}>
            <View style={styles.row}>
              <StatCard label="Active Jobs" value={stats.active_jobs} icon="🔧" color={theme.primary} style={{ flex: 1 }} />
              <StatCard label="Pending Quotes" value={stats.pending_quotes} icon="📝" color="#6366f1" style={{ flex: 1 }} />
            </View>
            <View style={styles.row}>
              <StatCard label="Open Jobs Available" value={stats.available_open_jobs} icon="🔍" color="#10b981" style={{ flex: 1 }} />
              <StatCard label="Wallet Balance" value={stats.wallet_balance} currency icon="💰" color="#f59e0b" style={{ flex: 1 }} />
            </View>
          </View>
        ) : (
          <View style={styles.row}><Skeleton height={80} style={{ flex: 1 }} /><Skeleton height={80} style={{ flex: 1 }} /></View>
        )}

        {stats && stats.available_open_jobs > 0 && (
          <TouchableOpacity style={[styles.openJobsBanner, { borderColor: theme.primary + '40', backgroundColor: theme.primaryBg }]}
            onPress={() => nav.navigate('ProviderJobs')}>
            <Text style={styles.openJobsIcon}>💼</Text>
            <View style={{ flex: 1 }}>
              <Text style={[styles.openJobsTitle, { color: theme.primaryDark }]}>{stats.available_open_jobs} open jobs near you</Text>
              <Text style={[styles.openJobsSub, { color: theme.primary }]}>Tap to browse and submit quotes</Text>
            </View>
            <Text style={{ fontSize: 18, color: theme.primary }}>→</Text>
          </TouchableOpacity>
        )}

        <SectionHeader title="Quick Actions" />
        <View style={styles.quickGrid}>
          {quickLinks.map(q => (
            <TouchableOpacity key={q.route + q.label} style={styles.quickBtn} onPress={() => nav.navigate(q.route)}>
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
  hero: { borderRadius: radius.xl, padding: spacing.xl },
  heroSub: { color: 'rgba(255,255,255,0.7)', fontSize: typography.sm, fontWeight: '500' },
  heroTitle: { color: colors.white, fontSize: typography.xxl, fontWeight: '800', marginTop: 2 },
  heroRow: { flexDirection: 'row', gap: 10, marginTop: 16 },
  heroBadge: { flex: 1, backgroundColor: 'rgba(255,255,255,0.18)', borderRadius: radius.lg, padding: 10, alignItems: 'center' },
  heroBadgeVal: { color: colors.white, fontSize: typography.sm, fontWeight: '800' },
  heroBadgeLbl: { color: 'rgba(255,255,255,0.6)', fontSize: typography.xs, marginTop: 2 },
  row: { flexDirection: 'row', gap: 10 },
  openJobsBanner: { flexDirection: 'row', alignItems: 'center', gap: 12, borderRadius: radius.xl, borderWidth: 1.5, padding: spacing.md },
  openJobsIcon: { fontSize: 24 },
  openJobsTitle: { fontSize: typography.sm, fontWeight: '700' },
  openJobsSub: { fontSize: typography.xs, marginTop: 2 },
  quickGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  quickBtn: { width: '47%', backgroundColor: colors.white, borderRadius: radius.xl, padding: spacing.md, alignItems: 'center', borderWidth: 1, borderColor: colors.gray100 },
  quickIcon: { width: 48, height: 48, borderRadius: radius.lg, alignItems: 'center', justifyContent: 'center', marginBottom: 6 },
  quickLabel: { fontSize: typography.xs, fontWeight: '600', color: colors.gray700, textAlign: 'center' },
})
