import React, { useState, useEffect, useCallback } from 'react'
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, ActivityIndicator, Alert } from 'react-native'
import { useRoute, useNavigation } from '@react-navigation/native'
import { bookingsApi } from '@/api/services'
import { Card, Badge } from '@/components/common/Cards'
import { Button } from '@/components/common/Button'
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

export const BookingConfirmationScreen: React.FC = () => {
  const theme = getTheme('tenant')
  const route = useRoute<any>()
  const nav = useNavigation<any>()
  const { bookingId } = route.params || {}

  const [booking, setBooking] = useState<Booking | null>(null)
  const [loading, setLoading] = useState(true)
  const [cancelling, setCancelling] = useState(false)

  const load = useCallback(async () => {
    try {
      const { data } = await bookingsApi.getBooking(bookingId)
      setBooking((data as any).data || data)
    } catch { setBooking(null) } finally { setLoading(false) }
  }, [bookingId])

  useEffect(() => { load() }, [load])

  const cancel = () => {
    // Alert.prompt is iOS-only in React Native, so a plain confirm (no reason
    // text field) is used here to work identically on Android too.
    Alert.alert('Cancel booking?', 'This cannot be undone.', [
      { text: 'No', style: 'cancel' },
      {
        text: 'Yes, cancel', style: 'destructive', onPress: async () => {
          setCancelling(true)
          try { await bookingsApi.cancelBooking(bookingId, ''); await load() }
          finally { setCancelling(false) }
        },
      },
    ])
  }

  if (loading) return <View style={styles.center}><ActivityIndicator size="large" color={theme.primary} /></View>
  if (!booking) return <View style={styles.center}><Text style={{ color: colors.gray400 }}>Booking not found.</Text></View>

  const s = STATUS_STYLE[booking.status] || STATUS_STYLE.checked_out

  return (
    <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
      <ScrollView contentContainerStyle={styles.content}>
        <TouchableOpacity onPress={() => nav.goBack()} style={{ marginBottom: 16 }}>
          <Text style={{ color: colors.gray500, fontWeight: '600' }}>&larr; Back</Text>
        </TouchableOpacity>

        <View style={styles.center}>
          <Text style={{ fontSize: 40 }}>✅</Text>
          <Text style={styles.heading}>Booking {booking.status === 'cancelled' ? 'Cancelled' : 'Requested'}</Text>
          <Text style={styles.reference}>Ref: {booking.booking_reference}</Text>
        </View>

        <Card style={{ marginTop: 20 }}>
          <View style={styles.row}>
            <View>
              <Text style={styles.listingName}>{booking.listing_name}</Text>
              <Text style={styles.sub}>{booking.room_type_name}</Text>
            </View>
            <Badge label={booking.status.replace('_', ' ')} color={s.color} bg={s.bg} />
          </View>

          <View style={styles.grid}>
            <View style={styles.gridItem}><Text style={styles.gridLabel}>Check-in</Text><Text style={styles.gridValue}>{formatDate(booking.check_in_date)}</Text></View>
            <View style={styles.gridItem}><Text style={styles.gridLabel}>Check-out</Text><Text style={styles.gridValue}>{formatDate(booking.check_out_date)}</Text></View>
            <View style={styles.gridItem}><Text style={styles.gridLabel}>Guests</Text><Text style={styles.gridValue}>{booking.num_guests}</Text></View>
            <View style={styles.gridItem}><Text style={styles.gridLabel}>Nights</Text><Text style={styles.gridValue}>{booking.nights}</Text></View>
          </View>

          <View style={styles.totalRow}>
            <Text style={styles.totalLabel}>Total amount</Text>
            <Text style={styles.totalValue}>{formatKES(booking.total_amount)}</Text>
          </View>

          {booking.status === 'pending_payment' && (
            <Text style={styles.notice}>Your booking is reserved pending payment. Complete payment from your dashboard to confirm it.</Text>
          )}
        </Card>

        {(booking.status === 'confirmed' || booking.status === 'checked_in') && (
          <Button label="Cancel Booking" onPress={cancel} loading={cancelling} variant="outline" color="#dc2626" style={{ marginTop: 16 }} />
        )}
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.gray50 },
  content: { padding: spacing.lg, paddingBottom: 40 },
  heading: { fontSize: typography.lg, fontWeight: '700', color: colors.gray900, marginTop: 10 },
  reference: { fontSize: typography.sm, color: colors.gray500, marginTop: 4, fontVariant: ['tabular-nums'] },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  listingName: { fontSize: typography.base, fontWeight: '700', color: colors.gray900 },
  sub: { fontSize: typography.sm, color: colors.gray500, marginTop: 2 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12, marginTop: 16 },
  gridItem: { width: '45%' },
  gridLabel: { fontSize: 10, color: colors.gray400 },
  gridValue: { fontSize: typography.sm, fontWeight: '700', color: colors.gray900, marginTop: 2 },
  totalRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 18, paddingTop: 14, borderTopWidth: 1, borderTopColor: colors.gray100 },
  totalLabel: { fontSize: typography.sm, color: colors.gray500 },
  totalValue: { fontSize: typography.lg, fontWeight: '800', color: colors.gray900 },
  notice: { fontSize: typography.xs, color: '#b45309', backgroundColor: '#fffbeb', padding: 10, borderRadius: 10, marginTop: 14 },
})
