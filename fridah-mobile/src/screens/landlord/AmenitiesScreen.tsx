import React, { useCallback, useEffect, useState } from 'react'
import { View, Text, FlatList, StyleSheet, RefreshControl } from 'react-native'
import { amenityApi } from '@/api/services'
import { Card, Badge, EmptyState, Skeleton, FadeIn } from '@/components/common/Cards'
import { Button } from '@/components/common/Button'
import { colors, spacing, typography, getTheme } from '@/theme'
import { formatKES } from '@/utils/formatters'

export const LandlordAmenitiesScreen: React.FC = () => {
  const theme = getTheme('landlord')
  const [charges, setCharges] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [busy, setBusy] = useState<string | null>(null)
  const [notice, setNotice] = useState<Record<string, string>>({})
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setError('')
    try {
      const { data } = await amenityApi.list()
      setCharges((data as any).data?.results || (data as any).results || [])
    } catch {
      setError('Could not load amenity charges. Pull down to retry.')
    } finally {
      setLoading(false); setRefreshing(false)
    }
  }, [])
  useEffect(() => { load() }, [load])

  const toggle = async (c: any) => {
    setBusy(c.id)
    try { await amenityApi.update(c.id, { is_active: !c.is_active }); await load() }
    catch { setError('Could not update the charge.') } finally { setBusy(null) }
  }
  const billNow = async (c: any) => {
    setBusy(c.id)
    try {
      const { data } = await amenityApi.billNow(c.id)
      const d = (data as any).data || {}
      setNotice((n) => ({ ...n, [c.id]: `Billed ${d.created ?? 0} tenant(s); ${d.skipped ?? 0} already billed or exempt.` }))
    } catch { setNotice((n) => ({ ...n, [c.id]: 'Billing failed.' })) } finally { setBusy(null) }
  }

  if (loading) return <View style={{ padding: spacing.lg, gap: spacing.md }}><Skeleton height={90} /><Skeleton height={90} /></View>

  return (
    <FlatList
      style={{ backgroundColor: colors.gray50 }}
      data={charges}
      keyExtractor={(c) => c.id}
      contentContainerStyle={{ padding: spacing.lg, gap: spacing.md, flexGrow: 1 }}
      refreshControl={<RefreshControl refreshing={refreshing} tintColor={theme.primary} onRefresh={() => { setRefreshing(true); load() }} />}
      ListHeaderComponent={error ? <Text style={styles.error} accessibilityRole="alert">{error}</Text> : null}
      ListEmptyComponent={<EmptyState emoji="✨" message="No amenity charges yet. Add them from the web portal." />}
      renderItem={({ item: c, index }) => (
        <FadeIn index={index}>
          <Card>
            <View style={styles.rowBetween}>
              <Text style={styles.name}>{c.name}</Text>
              <Badge label={c.is_active ? 'Active' : 'Paused'} color={c.is_active ? '#16a34a' : '#6b7280'} bg={c.is_active ? '#dcfce7' : '#f3f4f6'} />
            </View>
            <Text style={styles.meta}>{formatKES(c.amount)} · {c.frequency === 'monthly' ? 'Monthly' : 'One-off'} · {c.applies_to_all_units ? 'All units' : `${c.units.length} units`}</Text>
            {notice[c.id] ? <Text style={styles.notice} accessibilityRole="alert">{notice[c.id]}</Text> : null}
            <View style={styles.row}>
              <Button label="Bill now" size="sm" variant="outline" color={theme.primary} disabled={busy === c.id} onPress={() => billNow(c)} />
              <Button label={c.is_active ? 'Pause' : 'Resume'} size="sm" variant="outline" color={colors.gray600} disabled={busy === c.id} onPress={() => toggle(c)} />
            </View>
          </Card>
        </FadeIn>
      )}
    />
  )
}

const styles = StyleSheet.create({
  error: { color: '#dc2626', marginBottom: spacing.sm, fontSize: typography.sm },
  rowBetween: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: spacing.sm },
  row: { flexDirection: 'row', gap: spacing.sm, marginTop: spacing.md },
  name: { fontSize: typography.base, fontWeight: '700', color: colors.gray900, flex: 1 },
  meta: { fontSize: typography.xs, color: colors.gray500, marginTop: 2 },
  notice: { fontSize: typography.xs, color: '#047857', marginTop: spacing.sm },
})
