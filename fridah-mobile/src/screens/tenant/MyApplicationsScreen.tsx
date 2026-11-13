import React, { useState, useCallback } from 'react'
import { View, Text, FlatList, TouchableOpacity, StyleSheet, RefreshControl, ActivityIndicator, Alert } from 'react-native'
import { useFocusEffect } from '@react-navigation/native'
import { rentalsApi } from '@/api/services'
import { Card, EmptyState, Badge } from '@/components/common/Cards'
import { getTheme, colors, spacing, typography } from '@/theme'
import { formatKES, formatDate } from '@/utils/formatters'

const STATUS_STYLE: Record<string, { color: string; bg: string }> = {
  pending: { color: '#b45309', bg: '#fffbeb' },
  approved: { color: '#15803d', bg: '#f0fdf4' },
  rejected: { color: '#dc2626', bg: '#fef2f2' },
  withdrawn: { color: colors.gray600, bg: colors.gray100 },
}

export const MyApplicationsScreen: React.FC = () => {
  const theme = getTheme('tenant')
  const [applications, setApplications] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [withdrawing, setWithdrawing] = useState('')

  const load = useCallback(async () => {
    try {
      const { data } = await rentalsApi.applications()
      setApplications((data as any).results || (data as any).data || [])
    } catch { setApplications([]) } finally { setLoading(false); setRefreshing(false) }
  }, [])

  useFocusEffect(useCallback(() => { load() }, [load]))

  const withdraw = (id: string) => {
    Alert.alert('Withdraw application?', 'This cannot be undone.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Withdraw', style: 'destructive', onPress: async () => {
          setWithdrawing(id)
          try { await rentalsApi.withdrawApplication(id); await load() }
          finally { setWithdrawing('') }
        },
      },
    ])
  }

  if (loading) return <View style={styles.center}><ActivityIndicator size="large" color={theme.primary} /></View>

  return (
    <FlatList
      style={{ backgroundColor: colors.gray50 }}
      data={applications}
      keyExtractor={(a) => a.id}
      contentContainerStyle={styles.list}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} tintColor={theme.primary} />}
      ListEmptyComponent={<EmptyState emoji="📋" message="No applications yet" />}
      renderItem={({ item }) => {
        const s = STATUS_STYLE[item.status] || STATUS_STYLE.withdrawn
        return (
          <Card style={styles.card}>
            <View style={styles.row}>
              <View style={{ flex: 1 }}>
                <Text style={styles.title}>{item.property_name}</Text>
                <Text style={styles.sub}>Unit {item.unit_number} &middot; {formatKES(item.rent_amount)}/mo</Text>
                {item.status === 'rejected' && item.rejection_reason ? (
                  <Text style={styles.reason}>{item.rejection_reason}</Text>
                ) : null}
                <Text style={styles.date}>Applied {formatDate(item.created_at)}</Text>
              </View>
              <View style={{ alignItems: 'flex-end' }}>
                <Badge label={item.status} color={s.color} bg={s.bg} />
                {item.status === 'pending' && (
                  <TouchableOpacity disabled={withdrawing === item.id} onPress={() => withdraw(item.id)} style={{ marginTop: 8 }}>
                    <Text style={styles.withdrawText}>{withdrawing === item.id ? 'Withdrawing…' : 'Withdraw'}</Text>
                  </TouchableOpacity>
                )}
              </View>
            </View>
          </Card>
        )
      }}
    />
  )
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.gray50 },
  list: { padding: spacing.lg },
  card: { marginBottom: 10 },
  row: { flexDirection: 'row', justifyContent: 'space-between' },
  title: { fontSize: typography.sm, fontWeight: '700', color: colors.gray900 },
  sub: { fontSize: typography.xs, color: colors.gray500, marginTop: 2 },
  reason: { fontSize: typography.xs, color: '#dc2626', marginTop: 6 },
  date: { fontSize: typography.xs, color: colors.gray400, marginTop: 6 },
  withdrawText: { fontSize: typography.xs, fontWeight: '700', color: '#dc2626' },
})
