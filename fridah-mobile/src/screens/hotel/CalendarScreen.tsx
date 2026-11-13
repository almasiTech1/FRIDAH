import React, { useState, useEffect, useCallback } from 'react'
import { View, Text, ScrollView, TouchableOpacity, StyleSheet } from 'react-native'
import { bookingsApi } from '@/api/services'
import { Card, EmptyState, Skeleton } from '@/components/common/Cards'
import { getTheme, colors, spacing, typography, radius } from '@/theme'
import type { Listing } from '@/types'

interface RoomTypeDay { room_type_name: string; total_rooms: number; booked_rooms: number; available_rooms: number }
interface CalendarDay { date: string; room_types: RoomTypeDay[] }

export const HotelCalendarScreen: React.FC = () => {
  const theme = getTheme('hotel_owner')
  const [listings, setListings] = useState<Listing[]>([])
  const [selectedListingId, setSelectedListingId] = useState<string | null>(null)
  const [days, setDays] = useState<CalendarDay[]>([])
  const [loading, setLoading] = useState(false)
  const [monthOffset, setMonthOffset] = useState(0)

  useEffect(() => {
    bookingsApi.listings().then(({ data }) => {
      const items = (data as any).data?.results || (data as any).data || []
      setListings(items)
      if (items.length && !selectedListingId) setSelectedListingId(items[0].id)
    }).catch(() => {})
  }, [])

  const load = useCallback(async () => {
    if (!selectedListingId) return
    setLoading(true)
    try {
      const start = new Date()
      start.setMonth(start.getMonth() + monthOffset, 1)
      const end = new Date(start)
      end.setMonth(end.getMonth() + 1)
      const fmt = (d: Date) => d.toISOString().slice(0, 10)
      const { data } = await bookingsApi.availabilityCalendar(selectedListingId, fmt(start), fmt(end))
      setDays((data as any).data?.days || [])
    } catch { setDays([]) } finally { setLoading(false) }
  }, [selectedListingId, monthOffset])

  useEffect(() => { load() }, [load])

  const roomTypeNames = days[0]?.room_types.map(rt => rt.room_type_name) || []

  const cellColor = (day: CalendarDay, name: string) => {
    const rt = day.room_types.find(r => r.room_type_name === name)
    if (!rt || rt.total_rooms === 0) return colors.gray100
    if (rt.available_rooms === 0) return '#fee2e2'
    if (rt.available_rooms <= rt.total_rooms * 0.3) return '#fef3c7'
    return '#d1fae5'
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.listingTabs} contentContainerStyle={{ gap: 8, paddingHorizontal: spacing.lg }}>
        {listings.map(l => (
          <TouchableOpacity
            key={l.id}
            style={[styles.listingChip, selectedListingId === l.id && { backgroundColor: theme.primary }]}
            onPress={() => setSelectedListingId(l.id)}
          >
            <Text style={[styles.listingChipText, selectedListingId === l.id && { color: colors.white }]}>{l.name}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <View style={styles.monthRow}>
        <TouchableOpacity onPress={() => setMonthOffset(m => m - 1)}><Text style={styles.monthNav}>‹</Text></TouchableOpacity>
        <Text style={styles.monthLabel}>
          {new Date(new Date().setMonth(new Date().getMonth() + monthOffset)).toLocaleDateString('en-KE', { month: 'long', year: 'numeric' })}
        </Text>
        <TouchableOpacity onPress={() => setMonthOffset(m => m + 1)}><Text style={styles.monthNav}>›</Text></TouchableOpacity>
      </View>

      {loading ? (
        <View style={{ padding: spacing.lg }}><Skeleton height={200} /></View>
      ) : days.length === 0 ? (
        <EmptyState emoji="📅" message="No calendar data - choose a listing above." />
      ) : (
        <ScrollView>
          <ScrollView horizontal contentContainerStyle={{ padding: spacing.lg }}>
            <View>
              <View style={styles.row}>
                <View style={styles.rowLabelCell} />
                {days.map(d => (
                  <View key={d.date} style={styles.dayCell}><Text style={styles.dayNum}>{new Date(d.date).getDate()}</Text></View>
                ))}
              </View>
              {roomTypeNames.map(name => (
                <View key={name} style={styles.row}>
                  <View style={styles.rowLabelCell}><Text style={styles.rowLabel} numberOfLines={1}>{name}</Text></View>
                  {days.map(d => {
                    const rt = d.room_types.find(r => r.room_type_name === name)
                    return (
                      <View key={d.date} style={[styles.availCell, { backgroundColor: cellColor(d, name) }]}>
                        <Text style={styles.availText}>{rt?.available_rooms ?? '—'}</Text>
                      </View>
                    )
                  })}
                </View>
              ))}
            </View>
          </ScrollView>
          <View style={styles.legend}>
            <View style={styles.legendItem}><View style={[styles.legendDot, { backgroundColor: '#d1fae5' }]} /><Text style={styles.legendText}>Available</Text></View>
            <View style={styles.legendItem}><View style={[styles.legendDot, { backgroundColor: '#fef3c7' }]} /><Text style={styles.legendText}>Limited</Text></View>
            <View style={styles.legendItem}><View style={[styles.legendDot, { backgroundColor: '#fee2e2' }]} /><Text style={styles.legendText}>Full</Text></View>
          </View>
        </ScrollView>
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  listingTabs: { paddingTop: spacing.lg, flexGrow: 0 },
  listingChip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: radius.full, backgroundColor: colors.white, borderWidth: 1, borderColor: colors.gray200 },
  listingChipText: { fontSize: typography.xs, fontWeight: '700', color: colors.gray600 },
  monthRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 20, paddingVertical: spacing.md },
  monthNav: { fontSize: 22, fontWeight: '700', color: colors.gray500, paddingHorizontal: 8 },
  monthLabel: { fontSize: typography.sm, fontWeight: '700', color: colors.gray900 },
  row: { flexDirection: 'row' },
  rowLabelCell: { width: 100, paddingVertical: 8, paddingRight: 8, justifyContent: 'center' },
  rowLabel: { fontSize: typography.xs, fontWeight: '600', color: colors.gray700 },
  dayCell: { width: 32, alignItems: 'center', paddingVertical: 6 },
  dayNum: { fontSize: 10, color: colors.gray400, fontWeight: '700' },
  availCell: { width: 32, height: 32, borderRadius: 6, alignItems: 'center', justifyContent: 'center', margin: 1 },
  availText: { fontSize: 11, fontWeight: '700', color: colors.gray700 },
  legend: { flexDirection: 'row', gap: 16, paddingHorizontal: spacing.lg, paddingBottom: spacing.lg },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  legendDot: { width: 10, height: 10, borderRadius: 3 },
  legendText: { fontSize: typography.xs, color: colors.gray500 },
})
