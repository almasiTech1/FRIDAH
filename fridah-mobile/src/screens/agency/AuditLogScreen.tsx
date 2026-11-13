import React, { useState, useEffect } from 'react'
import { View, Text, FlatList, StyleSheet, RefreshControl } from 'react-native'
import { useAuthStore } from '@/stores/authStore'
import { agencyApi } from '@/api/services'
import { EmptyState } from '@/components/common/Cards'
import { agencyTheme, colors, spacing, typography } from '@/theme'

interface AuditLogEntry {
  id: string
  action: string
  actor_name?: string
  created_at: string
}

export const AgencyAuditLogScreen: React.FC = () => {
  const { agencies } = useAuthStore()
  const agency = agencies[0]
  const [logs, setLogs] = useState<AuditLogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const load = async () => {
    try {
      if (!agency) { setLogs([]); return }
      const { data } = await agencyApi.auditLogs(agency.id)
      setLogs((data as any).data?.results || (data as any).data || [])
    } catch {
      setLogs([])
    } finally {
      setLoading(false); setRefreshing(false)
    }
  }
  useEffect(() => { load() }, [agency])

  return (
    <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
      <Text style={styles.hint}>Every staffing, assignment, statement, and payout action taken in this agency.</Text>
      <FlatList
        data={logs}
        keyExtractor={(l) => l.id}
        contentContainerStyle={{ paddingHorizontal: spacing.lg, paddingBottom: spacing.lg }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} tintColor={agencyTheme.primary} />}
        renderItem={({ item: l }) => (
          <View style={styles.row}>
            <View style={[styles.dot, { backgroundColor: agencyTheme.primary }]} />
            <Text style={styles.action} numberOfLines={1}>{l.action.replace(/\./g, ' → ')}</Text>
            <Text style={styles.actor}>{l.actor_name || 'System'}</Text>
          </View>
        )}
        ListEmptyComponent={!loading ? <EmptyState emoji="📋" message="No audit entries yet." /> : null}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  hint: { fontSize: typography.xs, color: colors.gray400, paddingHorizontal: spacing.lg, paddingVertical: spacing.md },
  row: {
    flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: spacing.sm,
    borderBottomWidth: 1, borderBottomColor: colors.gray100,
  },
  dot: { width: 6, height: 6, borderRadius: 3 },
  action: { flex: 1, fontSize: typography.sm, fontWeight: '600', color: colors.gray700, textTransform: 'capitalize' },
  actor: { fontSize: typography.xs, color: colors.gray400 },
})
