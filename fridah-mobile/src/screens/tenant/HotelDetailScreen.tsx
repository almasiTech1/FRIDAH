import React, { useState, useEffect, useCallback } from 'react'
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet,
  TextInput, ActivityIndicator, Image, Dimensions, Alert,
} from 'react-native'
import { useRoute, useNavigation } from '@react-navigation/native'
import { bookingsApi } from '@/api/services'
import { Card, Badge } from '@/components/common/Cards'
import { Button } from '@/components/common/Button'
import { getTheme, colors, spacing, typography, radius } from '@/theme'
import { formatKES } from '@/utils/formatters'
import type { Listing, RoomType } from '@/types'

const SCREEN_WIDTH = Dimensions.get('window').width

export const HotelDetailScreen: React.FC = () => {
  const theme = getTheme('tenant')
  const route = useRoute<any>()
  const nav = useNavigation<any>()
  const { listingId } = route.params || {}

  const [listing, setListing] = useState<Listing | null>(null)
  const [loading, setLoading] = useState(true)
  const [galleryIndex, setGalleryIndex] = useState(0)

  const [checkIn, setCheckIn] = useState('')
  const [checkOut, setCheckOut] = useState('')
  const [guests, setGuests] = useState('1')
  const [selectedRoomType, setSelectedRoomType] = useState<RoomType | null>(null)
  const [availability, setAvailability] = useState<Record<string, number>>({})
  const [booking, setBooking] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await bookingsApi.getListing(listingId)
      setListing((data as any).data || data)
    } catch {
      setListing(null)
    } finally {
      setLoading(false)
    }
  }, [listingId])

  useEffect(() => { load() }, [load])

  const gallery = (listing?.images?.map((i) => i.image) || (listing?.primary_image ? [listing.primary_image] : []))

  const nights = (() => {
    if (!checkIn || !checkOut) return 0
    const diff = (new Date(checkOut).getTime() - new Date(checkIn).getTime()) / 86400000
    return diff > 0 ? Math.round(diff) : 0
  })()

  const checkAvailability = async () => {
    if (!checkIn || !checkOut || !listing?.room_types?.length) return
    const results: Record<string, number> = {}
    for (const rt of listing.room_types) {
      try {
        const { data } = await bookingsApi.checkAvailability(rt.id, checkIn, checkOut)
        results[rt.id] = (data as any).data?.available_rooms ?? (data as any).available_rooms ?? 0
      } catch { /* leave unset */ }
    }
    setAvailability(results)
  }

  const canBook = !!selectedRoomType && nights > 0 &&
    (availability[selectedRoomType.id] === undefined || availability[selectedRoomType.id] > 0)

  const book = async () => {
    if (!selectedRoomType || !listing) return
    setBooking(true)
    try {
      const { data } = await bookingsApi.createBooking({
        listing: listing.id,
        room_type: selectedRoomType.id,
        check_in_date: checkIn,
        check_out_date: checkOut,
        num_guests: Number(guests) || 1,
        num_rooms: 1,
      })
      const created = (data as any).data || data
      nav.replace('BookingConfirmation', { bookingId: created.id })
    } catch (e: any) {
      Alert.alert('Could not book', e?.response?.data?.error?.message || 'Please try again.')
    } finally {
      setBooking(false)
    }
  }

  if (loading) return <View style={styles.center}><ActivityIndicator size="large" color={theme.primary} /></View>
  if (!listing) return <View style={styles.center}><Text style={{ color: colors.gray400 }}>Listing not found.</Text></View>

  return (
    <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
      <ScrollView contentContainerStyle={{ paddingBottom: 40 }}>
        <TouchableOpacity onPress={() => nav.goBack()} style={styles.backBtn}>
          <Text style={{ color: colors.white, fontWeight: '700' }}>&larr; Back</Text>
        </TouchableOpacity>

        {gallery.length ? (
          <View>
            <ScrollView
              horizontal pagingEnabled showsHorizontalScrollIndicator={false}
              onMomentumScrollEnd={(e) => setGalleryIndex(Math.round(e.nativeEvent.contentOffset.x / SCREEN_WIDTH))}
            >
              {gallery.map((img, i) => (
                <Image key={i} source={{ uri: img }} style={{ width: SCREEN_WIDTH, height: 260 }} resizeMode="cover" />
              ))}
            </ScrollView>
            {gallery.length > 1 && (
              <View style={styles.dots}>
                {gallery.map((_, i) => (
                  <View key={i} style={[styles.dot, i === galleryIndex && styles.dotActive]} />
                ))}
              </View>
            )}
          </View>
        ) : (
          <View style={[styles.imgPlaceholder, { backgroundColor: theme.primaryLight }]}>
            <Text style={{ fontSize: 48 }}>🏨</Text>
          </View>
        )}

        <View style={styles.content}>
          <View style={styles.row}>
            <Text style={styles.name}>{listing.name}</Text>
            <Badge label={listing.listing_type.replace('_', ' ')} color={theme.primary} bg={theme.primaryLight} />
          </View>
          <Text style={styles.location}>📍 {listing.address_detail ? listing.address_detail + ', ' : ''}{listing.town}, {listing.county}</Text>

          {!!listing.description && <Text style={styles.description}>{listing.description}</Text>}

          <Text style={styles.sectionTitle}>Amenities</Text>
          {listing.amenities?.length ? (
            <View style={styles.amenities}>
              {listing.amenities.map((a) => (
                <View key={a} style={styles.amenityRow}>
                  <Text style={{ color: theme.primary }}>✓</Text>
                  <Text style={styles.amenityText}>{a}</Text>
                </View>
              ))}
            </View>
          ) : (
            <Text style={{ color: colors.gray400, fontSize: typography.sm }}>No amenities listed.</Text>
          )}

          <View style={styles.timesRow}>
            <View style={styles.timeBox}>
              <Text style={styles.timeLabel}>Check-in</Text>
              <Text style={styles.timeValue}>{listing.check_in_time}</Text>
            </View>
            <View style={styles.timeBox}>
              <Text style={styles.timeLabel}>Check-out</Text>
              <Text style={styles.timeValue}>{listing.check_out_time}</Text>
            </View>
          </View>

          {!!listing.cancellation_policy && (
            <>
              <Text style={styles.sectionTitle}>Cancellation Policy</Text>
              <Text style={styles.description}>{listing.cancellation_policy}</Text>
            </>
          )}

          {/* Booking widget */}
          <Card style={{ marginTop: 20 }}>
            <Text style={styles.sectionTitle}>Select dates</Text>
            <View style={{ flexDirection: 'row', gap: 10 }}>
              <View style={{ flex: 1 }}>
                <Text style={styles.fieldLabel}>Check-in</Text>
                <TextInput style={styles.input} placeholder="YYYY-MM-DD" placeholderTextColor={colors.gray400} value={checkIn} onChangeText={setCheckIn} onBlur={checkAvailability} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.fieldLabel}>Check-out</Text>
                <TextInput style={styles.input} placeholder="YYYY-MM-DD" placeholderTextColor={colors.gray400} value={checkOut} onChangeText={setCheckOut} onBlur={checkAvailability} />
              </View>
            </View>
            <Text style={styles.fieldLabel}>Guests</Text>
            <TextInput style={styles.input} keyboardType="number-pad" value={guests} onChangeText={setGuests} />

            {!listing.room_types?.length ? (
              <Text style={{ color: colors.gray400, textAlign: 'center', paddingVertical: 12 }}>No room types listed yet.</Text>
            ) : (
              listing.room_types.map((rt) => {
                const avail = availability[rt.id]
                const selected = selectedRoomType?.id === rt.id
                return (
                  <TouchableOpacity
                    key={rt.id}
                    style={[styles.roomType, selected && { borderColor: theme.primary, backgroundColor: theme.primaryLight }]}
                    onPress={() => setSelectedRoomType(rt)}
                  >
                    <View style={styles.row}>
                      <Text style={styles.roomName}>{rt.name}</Text>
                      <Text style={[styles.roomPrice, { color: theme.primary }]}>{formatKES(rt.price_per_night)}/night</Text>
                    </View>
                    <Text style={styles.roomSub}>Sleeps {rt.max_occupancy}</Text>
                    {avail !== undefined && (
                      <Text style={[styles.roomAvail, { color: avail > 0 ? '#15803d' : '#dc2626' }]}>
                        {avail > 0 ? `${avail} room(s) available` : 'Fully booked for these dates'}
                      </Text>
                    )}
                  </TouchableOpacity>
                )
              })
            )}

            {nights > 0 && selectedRoomType && (
              <View style={styles.totalRow}>
                <Text style={styles.totalLabel}>{formatKES(selectedRoomType.price_per_night)} × {nights} night(s)</Text>
                <Text style={styles.totalValue}>{formatKES(selectedRoomType.price_per_night * nights)}</Text>
              </View>
            )}

            <Button
              label="Book Now" onPress={book} loading={booking} disabled={!canBook}
              color={theme.primary} fullWidth style={{ marginTop: 14 }}
            />
          </Card>
        </View>
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.gray50 },
  backBtn: { position: 'absolute', top: 44, left: 16, zIndex: 10, backgroundColor: 'rgba(0,0,0,0.4)', paddingHorizontal: 12, paddingVertical: 6, borderRadius: radius.full },
  imgPlaceholder: { height: 260, alignItems: 'center', justifyContent: 'center' },
  dots: { position: 'absolute', bottom: 12, left: 0, right: 0, flexDirection: 'row', justifyContent: 'center', gap: 6 },
  dot: { width: 6, height: 6, borderRadius: 3, backgroundColor: 'rgba(255,255,255,0.5)' },
  dotActive: { backgroundColor: colors.white, width: 18 },
  content: { padding: spacing.lg },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  name: { fontSize: typography.lg, fontWeight: '700', color: colors.gray900, flex: 1, marginRight: 8 },
  location: { fontSize: typography.sm, color: colors.gray500, marginTop: 4 },
  description: { fontSize: typography.sm, color: colors.gray600, marginTop: 10, lineHeight: 20 },
  sectionTitle: { fontSize: typography.sm, fontWeight: '700', color: colors.gray900, marginTop: 18, marginBottom: 8 },
  amenities: { gap: 6 },
  amenityRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  amenityText: { fontSize: typography.sm, color: colors.gray600 },
  timesRow: { flexDirection: 'row', gap: 10, marginTop: 16 },
  timeBox: { flex: 1, backgroundColor: colors.gray100, borderRadius: radius.lg, padding: 12 },
  timeLabel: { fontSize: 10, color: colors.gray400 },
  timeValue: { fontSize: typography.sm, fontWeight: '700', color: colors.gray900, marginTop: 2 },
  fieldLabel: { fontSize: typography.xs, fontWeight: '600', color: colors.gray700, marginBottom: 6, marginTop: 10 },
  input: { borderWidth: 1.5, borderColor: colors.gray200, borderRadius: radius.md, paddingHorizontal: 12, paddingVertical: 10, fontSize: typography.sm, color: colors.gray900, backgroundColor: colors.white },
  roomType: { borderWidth: 1.5, borderColor: colors.gray100, borderRadius: radius.lg, padding: 12, marginTop: 10 },
  roomName: { fontSize: typography.sm, fontWeight: '700', color: colors.gray900 },
  roomPrice: { fontSize: typography.sm, fontWeight: '700' },
  roomSub: { fontSize: typography.xs, color: colors.gray500, marginTop: 2 },
  roomAvail: { fontSize: typography.xs, fontWeight: '600', marginTop: 4 },
  totalRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 16, paddingTop: 14, borderTopWidth: 1, borderTopColor: colors.gray100 },
  totalLabel: { fontSize: typography.sm, color: colors.gray500 },
  totalValue: { fontSize: typography.base, fontWeight: '700', color: colors.gray900 },
})
