import React, { useCallback, useEffect, useState } from 'react'
import { View, Text, FlatList, StyleSheet, RefreshControl } from 'react-native'
import { taxApi } from '@/api/services'
import { Card, StatusBadge, EmptyState, Skeleton, FadeIn } from '@/components/common/Cards'
import { colors, spacing, typography, getTheme } from '@/theme'
import { formatKES, formatDate } from '@/utils/formatters'

export const LandlordTaxScreen: React.FC = () => {
  const theme = getTheme('landlord')
  const [records, setRecords] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setError('')
    try {
      const { data } = await taxApi.records({ year: new Date().getFullYear() })
      setRecords((data as any).data?.results || (data as any).results || [])
    } catch {
      setError('Could not load tax records. Pull down to retry.')
    } finally {
      setLoading(false); setRefreshing(false)
    }
  }, [])
  useEffect(() => { load() }, [load])

  if (loading) return <View style={{ padding: spacing.lg, gap: spacing.md }}><Skeleton height={120} /><Skeleton height={120} /></View>

  return (
    <FlatList
      style={{ backgroundColor: colors.gray50 }}
      data={records}
      keyExtractor={(r) => r.id}
      contentContainerStyle={{ padding: spacing.lg, gap: spacing.md, flexGrow: 1 }}
      refreshControl={<RefreshControl refreshing={refreshing} tintColor={theme.primary} onRefresh={() => { setRefreshing(true); load() }} />}
      ListHeaderComponent={
        <View>
          <View style={styles.note} accessibilityRole="summary">
            <Text style={styles.noteText}>
              <Text style={{ fontWeight: '700' }}>Estimates only. </Text>
              Figures marked “Estimate” are not official KRA assessments. Confirm your actual liability with KRA or a qualified tax adviser.
            </Text>
          </View>
          {error ? <Text style={styles.error} accessibilityRole="alert">{error}</Text> : null}
        </View>
      }
      ListEmptyComponent={<EmptyState emoji="🧾" message="No tax records yet. Create estimates from the web portal." />}
      renderItem={({ item: r, index }) => (
        <FadeIn index={index}>
          <Card>
            <View style={styles.rowBetween}>
              <Text style={styles.name}>{r.property_name} · {r.tax_type_name}</Text>
              <StatusBadge status={r.status} />
            </View>
            <Text style={styles.meta}>{formatDate(r.period_start)} – {formatDate(r.period_end)}{r.reference ? ` · Ref ${r.reference}` : ''}</Text>
            <View style={styles.figures}>
              <Fig label="Gross" value={formatKES(r.gross_income)} />
              <Fig label="Calculated" value={formatKES(r.calculated_amount)} />
              <Fig label="Paid" value={formatKES(r.amount_paid)} />
              <Fig label="Balance" value={formatKES(r.balance_due)} bold />
            </View>
            {r.is_estimate && <Text style={styles.estimate}>{r.label}</Text>}
          </Card>
        </FadeIn>
      )}
    />
  )
}

const Fig: React.FC<{ label: string; value: string; bold?: boolean }> = ({ label, value, bold }) => (
  <View style={{ flex: 1 }}>
    <Text style={styles.figLabel}>{label}</Text>
    <Text style={[styles.figValue, bold && { fontWeight: '800' }]}>{value}</Text>
  </View>
)

const styles = StyleSheet.create({
  note: { backgroundColor: '#fffbeb', borderColor: '#fde68a', borderWidth: 1, borderRadius: 12, padding: spacing.md, marginBottom: spacing.md },
  noteText: { color: '#78350f', fontSize: typography.sm },
  error: { color: '#dc2626', marginBottom: spacing.sm, fontSize: typography.sm },
  rowBetween: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: spacing.sm },
  name: { fontSize: typography.base, fontWeight: '700', color: colors.gray900, flex: 1 },
  meta: { fontSize: typography.xs, color: colors.gray500, marginTop: 2 },
  figures: { flexDirection: 'row', marginTop: spacing.md, gap: spacing.sm },
  figLabel: { fontSize: typography.xs, color: colors.gray400 },
  figValue: { fontSize: typography.sm, fontWeight: '600', color: colors.gray900 },
  estimate: { marginTop: spacing.sm, fontSize: typography.xs, color: '#b45309', fontWeight: '600' },
})
