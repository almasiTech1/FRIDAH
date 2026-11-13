import React, { useState, useEffect, useCallback } from 'react'
import { View, Text, FlatList, RefreshControl, StyleSheet } from 'react-native'
import { blacklistApi } from '@/api/services'
import { Card, Badge, EmptyState } from '@/components/common/Cards'
import { Button } from '@/components/common/Button'
import { getTheme, colors, spacing, typography } from '@/theme'
import { formatKES, formatDate } from '@/utils/formatters'

export const AdminBlacklistScreen: React.FC = () => {
  const theme = getTheme('admin')
  const [entries, setEntries] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [reviewing, setReviewing] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const { data } = await blacklistApi.list({ status: 'disputed' })
      setEntries((data as any).data?.results || (data as any).data || [])
    } catch { setEntries([]) } finally { setLoading(false); setRefreshing(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const review = async (id: string, status: 'active' | 'removed') => {
    setReviewing(id)
    try { await blacklistApi.review(id, status); load() } finally { setReviewing(null) }
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
      <FlatList
        data={entries} keyExtractor={i => i.id}
        contentContainerStyle={{ padding: spacing.lg, gap: 12 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} tintColor={theme.primary} />}
        ListEmptyComponent={!loading ? <EmptyState emoji="✅" message="No disputed blacklist flags to review." /> : null}
        renderItem={({ item }) => (
          <Card style={{ padding: spacing.lg }}>
            <Text style={styles.tenant}>{item.tenant_name} <Text style={styles.phone}>({item.tenant_phone})</Text></Text>
            <Text style={styles.meta}>Flagged by {item.flagged_by_name} on {formatDate(item.created_at)}</Text>
            <View style={{ marginTop: 8, alignSelf: 'flex-start' }}>
              <Badge label={item.reason.replace('_', ' ')} color={colors.red600} bg="#fee2e2" />
            </View>
            <Text style={styles.details}>{item.details}</Text>
            {item.amount_owed ? <Text style={styles.owed}>Amount owed: {formatKES(item.amount_owed)}</Text> : null}
            {item.tenant_response ? (
              <View style={styles.responseBox}>
                <Text style={styles.responseLabel}>Tenant's response:</Text>
                <Text style={styles.details}>{item.tenant_response}</Text>
              </View>
            ) : null}
            <View style={{ flexDirection: 'row', gap: 8, marginTop: 12 }}>
              <Button label="Keep active" color="#059669" onPress={() => review(item.id, 'active')} loading={reviewing === item.id} size="sm" style={{ flex: 1 }} />
              <Button label="Remove flag" variant="outline" onPress={() => review(item.id, 'removed')} loading={reviewing === item.id} size="sm" style={{ flex: 1 }} />
            </View>
          </Card>
        )}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  tenant: { fontSize: typography.base, fontWeight: '700', color: colors.gray900 },
  phone: { fontWeight: '400', color: colors.gray400, fontSize: typography.sm },
  meta: { fontSize: typography.xs, color: colors.gray400, marginTop: 2 },
  details: { fontSize: typography.sm, color: colors.gray700, marginTop: 8 },
  owed: { fontSize: typography.sm, fontWeight: '600', color: colors.gray900, marginTop: 4 },
  responseBox: { marginTop: 8, backgroundColor: colors.gray50, borderRadius: 8, padding: 10 },
  responseLabel: { fontSize: typography.xs, fontWeight: '700', color: colors.gray500 },
})
