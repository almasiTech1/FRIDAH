import React, { useState, useEffect, useCallback } from 'react'
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, RefreshControl } from 'react-native'
import { useNavigation } from '@react-navigation/native'
import { useAuthStore } from '@/stores/authStore'
import { agencyApi } from '@/api/services'
import { StatCard, Card, SectionHeader, EmptyState, Skeleton } from '@/components/common/Cards'
import { agencyTheme, colors, spacing, typography, radius } from '@/theme'
import type { OwnerStatement, OwnerPayout } from '@/types'

export const AgencyDashboardScreen: React.FC = () => {
  const nav = useNavigation<any>()
  const { user, agencies } = useAuthStore()
  const [statements, setStatements] = useState<OwnerStatement[]>([])
  const [payouts, setPayouts] = useState<OwnerPayout[]>([])
  const [rollup, setRollup] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const agency = agencies[0]

  const load = useCallback(async () => {
    try {
      if (!agency) { setStatements([]); setPayouts([]); setRollup(null); return }
      const [stRes, poRes] = await Promise.all([agencyApi.statements(), agencyApi.payouts()])
      setStatements((stRes.data as any).data?.results || (stRes.data as any).data || [])
      setPayouts((poRes.data as any).data?.results || (poRes.data as any).data || [])
      try {
        const { data } = await agencyApi.dashboard(agency.id)
        setRollup((data as any).data)
      } catch {
        setRollup(null)
      }
    } catch {
      setStatements([]); setPayouts([]); setRollup(null)
    } finally {
      setLoading(false); setRefreshing(false)
    }
  }, [agency])

  useEffect(() => { load() }, [load])

  const draftCount = statements.filter((s) => s.status === 'draft').length
  const pendingPayouts = payouts.filter((p) => p.status === 'pending' || p.status === 'processing').length

  const quickLinks = [
    { to: 'AgencyProperties', icon: '🏠', label: 'Properties' },
    { to: 'AgencyStaff', icon: '👥', label: 'Staff' },
    { to: 'AgencyStatements', icon: '🧾', label: 'Statements' },
    { to: 'AgencyMessages', icon: '💬', label: 'Chat' },
    { to: 'AgencyExpenses', icon: '💸', label: 'Expenses' },
    { to: 'AgencyAuditLog', icon: '📋', label: 'Audit Log' },
  ]

  return (
    <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
      <View style={[styles.hero, { backgroundColor: agencyTheme.primary }]}>
        <Text style={styles.heroGreeting}>Welcome back, {user?.first_name} 🏢</Text>
        <Text style={styles.heroTitle}>{agency?.name || 'Your Agency'}</Text>
      </View>

      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} tintColor={agencyTheme.primary} />}
      >
        {!agency ? (
          <Card style={{ alignItems: 'center', paddingVertical: 32 }}>
            <Text style={{ color: colors.gray600, fontWeight: '600', marginBottom: 6 }}>You're not part of an agency.</Text>
            <Text style={{ color: colors.gray400, textAlign: 'center', paddingHorizontal: spacing.lg }}>
              Agencies are registered by a FRIDAH administrator. Contact support if your company should have one.
            </Text>
          </Card>
        ) : (
          <>
            <View style={styles.statsGrid}>
              <StatCard label="Managed Properties" value={agency.managed_properties_count} icon="🏠" style={styles.statCell} />
              <StatCard label="Property Owners" value={agency.owners_count} icon="👥" style={styles.statCell} />
              <StatCard label="Draft Statements" value={draftCount} icon="🧾" color="#d97706" style={styles.statCell} />
              <StatCard label="Pending Payouts" value={pendingPayouts} icon="💰" color="#16a34a" style={styles.statCell} />
            </View>

            {rollup && (
              <>
                <SectionHeader title="Portfolio Overview" style={{ marginTop: spacing.lg }} />
                <Card>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 }}>
                    <Text style={styles.rollupLabel}>Occupancy</Text>
                    <Text style={styles.rollupValue}>{rollup.summary.occupied_units}/{rollup.summary.total_units} units ({rollup.summary.occupancy_rate}%)</Text>
                  </View>
                  <View style={styles.progressTrack}>
                    <View style={[styles.progressFill, { width: `${rollup.summary.occupancy_rate}%`, backgroundColor: agencyTheme.primary }]} />
                  </View>

                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: spacing.md }}>
                    <Text style={styles.rollupLabel}>Collected this month</Text>
                    <Text style={[styles.rollupValue, { color: '#16a34a' }]}>KES {Number(rollup.summary.gross_rent_collected_this_month).toLocaleString()}</Text>
                  </View>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 6 }}>
                    <Text style={styles.rollupLabel}>Arrears</Text>
                    <Text style={[styles.rollupValue, { color: '#dc2626' }]}>KES {Number(rollup.summary.total_arrears).toLocaleString()}</Text>
                  </View>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 6 }}>
                    <Text style={styles.rollupLabel}>Open maintenance</Text>
                    <Text style={styles.rollupValue}>{rollup.summary.open_maintenance_requests}</Text>
                  </View>
                </Card>

                {rollup.properties.length > 0 && (
                  <>
                    <SectionHeader title="By Property" style={{ marginTop: spacing.lg }} />
                    <Card style={{ paddingVertical: 4 }}>
                      {rollup.properties.map((p: any, i: number) => (
                        <View key={p.property_id} style={[styles.propertyRow, i > 0 && styles.propertyRowBorder]}>
                          <View style={{ flex: 1 }}>
                            <Text style={styles.propertyName}>{p.property_name}</Text>
                            <Text style={styles.propertySub}>{p.occupied_units}/{p.total_units} occupied · {p.open_maintenance_requests} open jobs</Text>
                          </View>
                          <Text style={styles.propertyAmount}>KES {Number(p.collected_this_month).toLocaleString()}</Text>
                        </View>
                      ))}
                    </Card>
                  </>
                )}
              </>
            )}

            <SectionHeader title="Quick Actions" style={{ marginTop: spacing.lg }} />
            <View style={styles.quickGrid}>
              {quickLinks.map((q) => (
                <TouchableOpacity key={q.to} style={styles.quickCard} onPress={() => nav.navigate(q.to)}>
                  <Text style={styles.quickIcon}>{q.icon}</Text>
                  <Text style={styles.quickLabel}>{q.label}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </>
        )}

      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  hero: { paddingHorizontal: spacing.xl, paddingTop: spacing.xxl, paddingBottom: spacing.xl },
  heroGreeting: { color: 'rgba(255,255,255,0.75)', fontSize: typography.sm, fontWeight: '500' },
  heroTitle: { color: colors.white, fontSize: typography.xxl, fontWeight: '900', marginTop: 4 },
  scroll: { padding: spacing.lg },
  statsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md },
  statCell: { minWidth: '45%' },
  quickGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md, marginTop: spacing.sm },
  quickCard: {
    width: '46%', backgroundColor: colors.white, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.gray100,
    paddingVertical: spacing.lg, alignItems: 'center', gap: 6,
  },
  quickIcon: { fontSize: 26 },
  quickLabel: { fontSize: typography.sm, fontWeight: '600', color: colors.gray700 },
  rollupLabel: { fontSize: typography.sm, color: colors.gray500, fontWeight: '500' },
  rollupValue: { fontSize: typography.sm, color: colors.gray900, fontWeight: '700' },
  progressTrack: { height: 8, borderRadius: 999, backgroundColor: colors.gray100, overflow: 'hidden' },
  progressFill: { height: '100%', borderRadius: 999 },
  propertyRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 12, paddingHorizontal: 4 },
  propertyRowBorder: { borderTopWidth: 1, borderTopColor: colors.gray100 },
  propertyName: { fontSize: typography.sm, fontWeight: '700', color: colors.gray900 },
  propertySub: { fontSize: typography.xs, color: colors.gray500, marginTop: 2 },
  propertyAmount: { fontSize: typography.sm, fontWeight: '700', color: '#16a34a' },
  input: {
    borderWidth: 1, borderColor: colors.gray200, borderRadius: radius.md, paddingHorizontal: 12, paddingVertical: 10,
    fontSize: typography.sm, marginBottom: spacing.sm, color: colors.gray900,
  },
})
