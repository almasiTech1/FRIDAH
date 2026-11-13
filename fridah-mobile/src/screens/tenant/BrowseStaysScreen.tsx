import React, { useState, useEffect, useCallback } from 'react'
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet,
  TextInput, RefreshControl, ActivityIndicator, Image,
} from 'react-native'
import { useNavigation } from '@react-navigation/native'
import { bookingsApi } from '@/api/services'
import { Card, EmptyState, Badge } from '@/components/common/Cards'
import { getTheme, colors, spacing, typography, radius } from '@/theme'
import { formatKES } from '@/utils/formatters'
import type { Listing } from '@/types'

const TYPE_EMOJI: Record<string, string> = { hotel: '🏨', bnb: '🏡', apartment_stay: '🏢', villa: '🏖️' }

export const BrowseStaysScreen: React.FC = () => {
  const theme = getTheme('tenant')
  const nav = useNavigation<any>()
  const [listings, setListings] = useState<Listing[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [search, setSearch] = useState('')

  const load = useCallback(async () => {
    try {
      const { data } = await bookingsApi.listings({ search: search || undefined })
      setListings((data as any).data?.results || (data as any).results || [])
    } catch {
      setListings([])
    } finally { setLoading(false); setRefreshing(false) }
  }, [search])

  useEffect(() => { const t = setTimeout(load, 400); return () => clearTimeout(t) }, [search, load])

  return (
    <View style={styles.container}>
      <View style={styles.searchWrap}>
        <View style={styles.searchBox}>
          <Text style={styles.searchIcon}>🔍</Text>
          <TextInput
            style={styles.searchInput}
            placeholder="Search town, hotel, BnB…"
            placeholderTextColor={colors.gray400}
            value={search}
            onChangeText={setSearch}
          />
          {search ? <TouchableOpacity onPress={() => setSearch('')}><Text style={{ color: colors.gray400, fontSize: 16 }}>✕</Text></TouchableOpacity> : null}
        </View>
      </View>

      {loading ? (
        <ActivityIndicator size="large" color={theme.primary} style={{ marginTop: 40 }} />
      ) : (
        <FlatList
          data={listings}
          keyExtractor={(i) => i.id}
          contentContainerStyle={styles.list}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} tintColor={theme.primary} />}
          ListEmptyComponent={<EmptyState emoji="🏨" message="No stays found" />}
          renderItem={({ item }) => (
            <TouchableOpacity activeOpacity={0.85} onPress={() => nav.navigate('HotelDetail', { listingId: item.id })}>
              <Card style={styles.card}>
                <View style={[styles.imgBox, { backgroundColor: theme.primaryLight }]}>
                  {item.primary_image ? (
                    <Image source={{ uri: item.primary_image }} style={{ width: '100%', height: '100%' }} resizeMode="cover" />
                  ) : (
                    <Text style={styles.propEmoji}>{TYPE_EMOJI[item.listing_type] || '🏨'}</Text>
                  )}
                </View>
                <View style={styles.cardBody}>
                  <View style={styles.cardTop}>
                    <Text style={styles.propName}>{item.name}</Text>
                    <Badge label={item.listing_type.replace('_', ' ')} color={theme.primary} bg={theme.primaryLight} />
                  </View>
                  <Text style={styles.location}>📍 {item.town}, {item.county}</Text>
                  <View style={styles.cardFooter}>
                    <View>
                      <Text style={styles.fromText}>From</Text>
                      <Text style={[styles.price, { color: theme.primary }]}>
                        {item.min_price ? formatKES(item.min_price) + '/night' : 'Contact'}
                      </Text>
                    </View>
                    <Text style={styles.hostName}>by {item.host_name}</Text>
                  </View>
                </View>
              </Card>
            </TouchableOpacity>
          )}
        />
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.gray50 },
  searchWrap: { padding: spacing.lg, paddingBottom: 4 },
  searchBox: { flexDirection: 'row', alignItems: 'center', backgroundColor: colors.white, borderRadius: radius.lg, paddingHorizontal: 14, borderWidth: 1, borderColor: colors.gray200 },
  searchIcon: { marginRight: 8, fontSize: 14 },
  searchInput: { flex: 1, paddingVertical: 12, fontSize: typography.sm, color: colors.gray900 },
  list: { padding: spacing.lg },
  card: { marginBottom: 14, padding: 0, overflow: 'hidden' },
  imgBox: { height: 140, alignItems: 'center', justifyContent: 'center' },
  propEmoji: { fontSize: 40 },
  cardBody: { padding: spacing.md },
  cardTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  propName: { fontSize: typography.sm, fontWeight: '700', color: colors.gray900, flex: 1, marginRight: 8 },
  location: { fontSize: typography.xs, color: colors.gray500, marginTop: 4 },
  cardFooter: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end', marginTop: 12 },
  fromText: { fontSize: 10, color: colors.gray400 },
  price: { fontSize: typography.sm, fontWeight: '700' },
  hostName: { fontSize: typography.xs, color: colors.gray400 },
})
