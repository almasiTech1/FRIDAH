import React, { useState, useCallback } from 'react'
import { View, Text, FlatList, TouchableOpacity, StyleSheet, RefreshControl, ActivityIndicator } from 'react-native'
import { useFocusEffect, useNavigation } from '@react-navigation/native'
import { bookingsApi } from '@/api/services'
import { Card, EmptyState, Badge } from '@/components/common/Cards'
import { getTheme, colors, spacing, typography } from '@/theme'
import { formatKES, formatDate } from '@/utils/formatters'
import type { Booking } from '@/types'

const STATUS_STYLE: Record<string, { color: string; bg: string }> = {
  pending_payment: { color: '#b45309', bg: '#fffbeb' },
  confirmed: { color: '#15803d', bg: '#f0fdf4' },
  checked_in: { color: '#15803d', bg: '#f0fdf4' },
  checked_out: { color: colors.gray600, bg: colors.gray100 },
  cancelled: { color: '#dc2626', bg: '#fef2f2' },
}

const FILTERS = [
  { value: 'all', label: 'All' },
  { value: 'upcoming', label: 'Upcoming' },
  { value: 'past', label: 'Past' },
  { value: 'cancelled', label: 'Cancelled' },
]

export const MyBookingsScreen: React.FC = () => {
  const theme = getTheme('tenant')
  const nav = useNavigation<any>()
  const [bookings, setBookings] = useState<Booking[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [filter, setFilter] = useState('all')

  const load = useCallback(async () => {
    try {
      const { data } = await bookingsApi.bookings()
      const list = (data as any).data?.results || (data as any).results || []
      setBookings(list.sort((a: Booking, b: Booking) => (b as any).created_at?.localeCompare((a as any).created_at)))
    } catch { setBookings([]) } finally { setLoading(false); setRefreshing(false) }
  }, [])

  useFocusEffect(useCallback(() => { load() }, [load]))

  const today = new Date().toISOString().slice(0, 10)
  const filtered = bookings.filter((b) => {
    if (filter === 'upcoming') return b.check_out_date >= today && b.status !== 'cancelled'
    if (filter === 'past') return b.check_out_date < today && b.status !== 'cancelled'
    if (filter === 'cancelled') return b.status === 'cancelled'
    return true
  })

  if (loading) return <View style={styles.center}><ActivityIndicator size="large" color={theme.primary} /></View>

  return (
    <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
      <View style={styles.filterRow}>
        {FILTERS.map((f) => (
          <TouchableOpacity
            key={f.value}
            style={[styles.filterChip, filter === f.value && { backgroundColor: theme.primary }]}
            onPress={() => setFilter(f.value)}
          >
            <Text style={[styles.filterText, filter === f.value && { color: colors.white }]}>{f.label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <FlatList
        data={filtered}
        keyExtractor={(b) => b.id}
        contentContainerStyle={styles.list}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} tintColor={theme.primary} />}
        ListEmptyComponent={<EmptyState emoji="🏨" message="No bookings here" />}
        renderItem={({ item }) => {
          const s = STATUS_STYLE[item.status] || STATUS_STYLE.checked_out
          return (
            <TouchableOpacity onPress={() => nav.navigate('BookingConfirmation', { bookingId: item.id })}>
              <Card style={styles.card}>
                <View style={styles.row}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.title}>{item.listing_name}</Text>
                    <Text style={styles.sub}>{item.room_type_name}</Text>
                    <Text style={styles.dates}>{formatDate(item.check_in_date)} → {formatDate(item.check_out_date)} · {item.nights} night(s)</Text>
                  </View>
                  <View style={{ alignItems: 'flex-end' }}>
                    <Badge label={item.status.replace('_', ' ')} color={s.color} bg={s.bg} />
                    <Text style={styles.amount}>{formatKES(item.total_amount)}</Text>
                  </View>
                </View>
              </Card>
            </TouchableOpacity>
          )
        }}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.gray50 },
  filterRow: { flexDirection: 'row', gap: 8, paddingHorizontal: spacing.lg, paddingTop: spacing.md, paddingBottom: 4 },
  filterChip: { paddingHorizontal: 14, paddingVertical: 7, borderRadius: 999, backgroundColor: colors.gray100 },
  filterText: { fontSize: typography.xs, fontWeight: '700', color: colors.gray600 },
  list: { padding: spacing.lg },
  card: { marginBottom: 10 },
  row: { flexDirection: 'row', justifyContent: 'space-between' },
  title: { fontSize: typography.sm, fontWeight: '700', color: colors.gray900 },
  sub: { fontSize: typography.xs, color: colors.gray500, marginTop: 2 },
  dates: { fontSize: typography.xs, color: colors.gray500, marginTop: 8 },
  amount: { fontSize: typography.sm, fontWeight: '700', color: colors.gray900, marginTop: 8 },
})
