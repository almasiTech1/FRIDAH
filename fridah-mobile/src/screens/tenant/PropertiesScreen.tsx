import React, { useState, useEffect, useCallback } from 'react'
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet,
  TextInput, RefreshControl, ActivityIndicator,
} from 'react-native'
import { useNavigation } from '@react-navigation/native'
import { propertiesApi, aiApi } from '@/api/services'
import { Card, EmptyState, Badge } from '@/components/common/Cards'
import { getTheme, colors, spacing, typography, radius } from '@/theme'
import { formatKES } from '@/utils/formatters'
import type { Property } from '@/types'

export const TenantPropertiesScreen: React.FC = () => {
  const theme = getTheme('tenant')
  const nav = useNavigation<any>()
  const [properties, setProperties] = useState<Property[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [search, setSearch] = useState('')

  const [aiQuery, setAiQuery] = useState('')
  const [aiResults, setAiResults] = useState<{ property: Property; explanation: string }[] | null>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiError, setAiError] = useState('')

  const [recommendations, setRecommendations] = useState<{ property: Property; score: number | null; reasons: string[] }[]>([])
  const [recsPersonalized, setRecsPersonalized] = useState(false)

  const loadRecommendations = useCallback(async () => {
    try {
      const { data } = await propertiesApi.recommendations(8)
      setRecommendations((data as any).data?.results || [])
      setRecsPersonalized((data as any).data?.is_personalized || false)
    } catch {
      setRecommendations([])
    }
  }, [])

  useEffect(() => { loadRecommendations() }, [loadRecommendations])

  const load = useCallback(async () => {
    try {
      const { data } = await propertiesApi.list({ search: search || undefined })
      setProperties(data.data?.results || [])
    } catch {
      setProperties([
        { id:'1', landlord:'', landlord_name:'John Doe', name:'Westlands Heights', description:'Modern apartments', property_type:'apartment', status:'active', county:'Nairobi', town:'Westlands', total_units:24, vacant_units_count:6, amenities:['Water','Parking','Gym'], min_rent:25000, created_at:'' },
        { id:'2', landlord:'', landlord_name:'Mary Wanjiku', name:'Kilimani Gardens', description:'', property_type:'bungalow', status:'active', county:'Nairobi', town:'Kilimani', total_units:8, vacant_units_count:2, amenities:['Water','Security'], min_rent:35000, created_at:'' },
      ])
    } finally { setLoading(false); setRefreshing(false) }
  }, [search])

  useEffect(() => { const t = setTimeout(load, 400); return () => clearTimeout(t) }, [search, load])

  const runAiSearch = async () => {
    if (!aiQuery.trim()) return
    setAiLoading(true)
    setAiError('')
    try {
      const { data } = await aiApi.propertySearch(aiQuery)
      const results = (data as any).data?.results || []
      const hydrated = await Promise.all(
        results.map(async (r: { property_id: string; explanation: string }) => {
          try {
            const { data: propData } = await propertiesApi.get(r.property_id)
            return { property: (propData as any).data, explanation: r.explanation }
          } catch { return null }
        })
      )
      setAiResults(hydrated.filter((h): h is { property: Property; explanation: string } => h !== null))
    } catch (e: any) {
      setAiError(e?.response?.status === 503
        ? 'AI search is not available right now. Try the search box below instead.'
        : 'Search failed. Please try again.')
    } finally {
      setAiLoading(false)
    }
  }

  const clearAiSearch = () => { setAiResults(null); setAiQuery(''); setAiError('') }

  const propType = (t: string) => ({ apartment:'🏢', bungalow:'🏠', maisonette:'🏡', townhouse:'🏘️', hostel:'🛏️', bedsitter:'🚪' }[t] || '🏠')

  return (
    <View style={styles.container}>
      {/* AI search */}
      <View style={styles.aiWrap}>
        <View style={styles.aiBox}>
          <Text style={styles.aiIcon}>✨</Text>
          <TextInput
            style={styles.aiInput}
            placeholder="Ask AI: '2 bedroom under 30k near Kilimani'"
            placeholderTextColor={colors.gray400}
            value={aiQuery}
            onChangeText={setAiQuery}
            onSubmitEditing={runAiSearch}
            returnKeyType="search"
          />
          <TouchableOpacity onPress={runAiSearch} disabled={aiLoading}>
            {aiLoading ? <ActivityIndicator size="small" color={theme.primary} /> : <Text style={{ color: theme.primary, fontWeight: '700', fontSize: typography.sm }}>Search</Text>}
          </TouchableOpacity>
        </View>
        {!!aiError && <Text style={styles.aiErrorText}>{aiError}</Text>}
      </View>

      {/* Recommended for You */}
      {!aiResults && recommendations.length > 0 && (
        <View style={styles.recsWrap}>
          <Text style={styles.recsTitle}>{recsPersonalized ? '✨ Recommended for You' : '🆕 Recently Listed'}</Text>
          <FlatList
            horizontal
            showsHorizontalScrollIndicator={false}
            data={recommendations}
            keyExtractor={(r) => r.property.id}
            contentContainerStyle={{ gap: 10 }}
            renderItem={({ item }) => (
              <TouchableOpacity
                style={styles.recCard}
                activeOpacity={0.85}
                onPress={() => nav.navigate('PropertyDetail', { propertyId: item.property.id })}
              >
                <View style={[styles.recImgBox, { backgroundColor: theme.primaryLight }]}>
                  <Text style={{ fontSize: 24 }}>🏠</Text>
                </View>
                <Text style={styles.recName} numberOfLines={1}>{item.property.name}</Text>
                <Text style={[styles.recPrice, { color: theme.primary }]}>
                  {item.property.min_rent ? formatKES(item.property.min_rent) + '/mo' : 'Contact'}
                </Text>
                {item.reasons?.[0] && <Text style={styles.recReason} numberOfLines={1}>{item.reasons[0]}</Text>}
              </TouchableOpacity>
            )}
          />
        </View>
      )}

      {/* Search bar */}
      {!aiResults && (
      <View style={styles.searchWrap}>
        <View style={styles.searchBox}>
          <Text style={styles.searchIcon}>🔍</Text>
          <TextInput
            style={styles.searchInput}
            placeholder="Search town, estate, property name…"
            placeholderTextColor={colors.gray400}
            value={search}
            onChangeText={setSearch}
          />
          {search ? <TouchableOpacity onPress={() => setSearch('')}><Text style={{ color: colors.gray400, fontSize: 16 }}>✕</Text></TouchableOpacity> : null}
        </View>
        <TouchableOpacity style={styles.staysPill} onPress={() => nav.navigate('BrowseStays')}>
          <Text style={styles.staysPillText}>🏨 Looking for a short stay instead? Browse hotels & BnBs</Text>
        </TouchableOpacity>
      </View>
      )}

      {aiResults && (
        <View style={styles.aiResultsHeader}>
          <Text style={styles.aiResultsCount}>{aiResults.length} AI-matched {aiResults.length === 1 ? 'result' : 'results'}</Text>
          <TouchableOpacity onPress={clearAiSearch}><Text style={{ color: theme.primary, fontWeight: '700', fontSize: typography.xs }}>Clear</Text></TouchableOpacity>
        </View>
      )}

      {loading && !aiResults ? (
        <ActivityIndicator size="large" color={theme.primary} style={{ marginTop: 40 }} />
      ) : aiResults ? (
        <FlatList
          data={aiResults}
          keyExtractor={(r) => r.property.id}
          contentContainerStyle={styles.list}
          ListEmptyComponent={<EmptyState emoji="✨" message="No AI matches found" />}
          renderItem={({ item }) => (
            <TouchableOpacity activeOpacity={0.85} onPress={() => nav.navigate('PropertyDetail', { propertyId: item.property.id })}>
              <Card style={styles.card}>
                <View style={styles.cardBody}>
                  <View style={styles.cardTop}>
                    <Text style={styles.propName}>{item.property.name}</Text>
                    <Badge label={item.property.property_type} color={theme.primary} bg={theme.primaryLight} />
                  </View>
                  <Text style={styles.location}>📍 {item.property.town}, {item.property.county}</Text>
                  <View style={styles.aiExplanationBox}>
                    <Text style={styles.aiExplanationText}>✨ {item.explanation}</Text>
                  </View>
                  <View style={styles.cardFooter}>
                    <View>
                      <Text style={styles.fromText}>From</Text>
                      <Text style={[styles.price, { color: theme.primary }]}>
                        {item.property.min_rent ? formatKES(item.property.min_rent) + '/mo' : 'Contact'}
                      </Text>
                    </View>
                    <Text style={styles.aiVacantText}>{item.property.vacant_units_count} vacant</Text>
                  </View>
                </View>
              </Card>
            </TouchableOpacity>
          )}
        />
      ) : (
        <FlatList
          data={properties}
          keyExtractor={i => i.id}
          contentContainerStyle={styles.list}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} tintColor={theme.primary} />}
          ListEmptyComponent={<EmptyState emoji="🏠" message="No properties found" />}
          renderItem={({ item }) => (
            <TouchableOpacity activeOpacity={0.85} onPress={() => nav.navigate('PropertyDetail', { propertyId: item.id })}>
            <Card style={styles.card}>
              {/* Image placeholder */}
              <View style={[styles.imgBox, { backgroundColor: theme.primaryLight }]}>
                <Text style={styles.propEmoji}>{propType(item.property_type)}</Text>
                <View style={styles.vacantBadge}>
                  <Text style={styles.vacantText}>{item.vacant_units_count} vacant</Text>
                </View>
              </View>
              <View style={styles.cardBody}>
                <View style={styles.cardTop}>
                  <Text style={styles.propName}>{item.name}</Text>
                  <Badge label={item.property_type} color={theme.primary} bg={theme.primaryLight} />
                </View>
                <Text style={styles.location}>📍 {item.estate ? item.estate + ', ' : ''}{item.town}, {item.county}</Text>
                <View style={styles.amenities}>
                  {item.amenities.slice(0, 3).map(a => (
                    <View key={a} style={styles.amenityChip}>
                      <Text style={styles.amenityText}>{a}</Text>
                    </View>
                  ))}
                  {item.amenities.length > 3 && (
                    <Text style={styles.moreAmenities}>+{item.amenities.length - 3} more</Text>
                  )}
                </View>
                <View style={styles.cardFooter}>
                  <View>
                    <Text style={styles.fromText}>From</Text>
                    <Text style={[styles.price, { color: theme.primary }]}>
                      {item.min_rent ? formatKES(item.min_rent) + '/mo' : 'Contact'}
                    </Text>
                  </View>
                  <Text style={styles.landlordName}>by {item.landlord_name}</Text>
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
  aiWrap: { paddingHorizontal: spacing.lg, paddingTop: spacing.lg, paddingBottom: 4 },
  aiBox: { flexDirection: 'row', alignItems: 'center', backgroundColor: colors.white, borderRadius: radius.lg, paddingHorizontal: 14, borderWidth: 1.5, borderColor: '#c7d2fe' },
  aiIcon: { marginRight: 8, fontSize: 15 },
  aiInput: { flex: 1, paddingVertical: 12, fontSize: typography.sm, color: colors.gray900 },
  aiErrorText: { fontSize: typography.xs, color: '#dc2626', marginTop: 6 },
  recsWrap: { paddingLeft: spacing.lg, paddingTop: spacing.md },
  recsTitle: { fontSize: typography.sm, fontWeight: '700', color: colors.gray900, marginBottom: 10 },
  recCard: { width: 130, backgroundColor: colors.white, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.gray100, padding: 8, marginRight: 4 },
  recImgBox: { height: 60, borderRadius: radius.md, alignItems: 'center', justifyContent: 'center', marginBottom: 6 },
  recName: { fontSize: typography.xs, fontWeight: '700', color: colors.gray900 },
  recPrice: { fontSize: typography.xs, fontWeight: '700', marginTop: 2 },
  recReason: { fontSize: 10, color: colors.gray400, marginTop: 2 },
  aiResultsHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: spacing.lg, paddingTop: 12, paddingBottom: 4 },
  aiResultsCount: { fontSize: typography.xs, fontWeight: '700', color: colors.gray600 },
  aiExplanationBox: { backgroundColor: '#eff6ff', borderRadius: radius.md, padding: 8, marginTop: 8 },
  aiExplanationText: { fontSize: typography.xs, color: '#1d4ed8', fontWeight: '500' },
  aiVacantText: { fontSize: typography.xs, color: colors.gray400 },
  searchWrap: { padding: spacing.lg, paddingBottom: 4 },
  staysPill: { marginTop: 10, backgroundColor: colors.gray50, borderRadius: radius.lg, padding: 10, borderWidth: 1, borderColor: colors.gray100 },
  staysPillText: { fontSize: typography.xs, fontWeight: '600', color: colors.gray600, textAlign: 'center' },
  searchBox: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    backgroundColor: colors.white, borderRadius: radius.xl,
    borderWidth: 1.5, borderColor: colors.gray200,
    paddingHorizontal: 14, paddingVertical: 11,
  },
  searchIcon: { fontSize: 16 },
  searchInput: { flex: 1, fontSize: typography.sm, color: colors.gray900 },
  list: { padding: spacing.lg, gap: 14 },
  card: { overflow: 'hidden', padding: 0 },
  imgBox: {
    height: 140, alignItems: 'center', justifyContent: 'center',
    position: 'relative',
  },
  propEmoji: { fontSize: 52 },
  vacantBadge: {
    position: 'absolute', top: 10, right: 10,
    backgroundColor: 'rgba(16,185,129,0.9)', borderRadius: radius.full,
    paddingHorizontal: 10, paddingVertical: 4,
  },
  vacantText: { color: colors.white, fontSize: typography.xs, fontWeight: '700' },
  cardBody: { padding: spacing.lg },
  cardTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 },
  propName: { fontSize: typography.base, fontWeight: '700', color: colors.gray900, flex: 1, marginRight: 8 },
  location: { fontSize: typography.xs, color: colors.gray500, marginBottom: 10 },
  amenities: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 12 },
  amenityChip: { backgroundColor: colors.gray100, borderRadius: radius.full, paddingHorizontal: 10, paddingVertical: 3 },
  amenityText: { fontSize: typography.xs, color: colors.gray600, fontWeight: '500' },
  moreAmenities: { fontSize: typography.xs, color: colors.gray400, alignSelf: 'center' },
  cardFooter: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end' },
  fromText: { fontSize: typography.xs, color: colors.gray400 },
  price: { fontSize: typography.lg, fontWeight: '800' },
  landlordName: { fontSize: typography.xs, color: colors.gray400 },
})
