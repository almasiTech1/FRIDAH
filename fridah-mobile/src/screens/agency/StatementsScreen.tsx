import React, { useState, useEffect } from 'react'
import { View, Text, FlatList, TouchableOpacity, StyleSheet, RefreshControl, TextInput, Alert } from 'react-native'
import { agencyApi } from '@/api/services'
import { Card, StatusBadge, EmptyState } from '@/components/common/Cards'
import { Button } from '@/components/common/Button'
import { agencyTheme, colors, spacing, typography, radius } from '@/theme'
import { formatKES, formatDate } from '@/utils/formatters'
import type { OwnerStatement } from '@/types'

function firstOfMonth() { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().slice(0, 10) }
function lastOfMonth() { const d = new Date(); return new Date(d.getFullYear(), d.getMonth() + 1, 0).toISOString().slice(0, 10) }

export const AgencyStatementsScreen: React.FC = () => {
  const [statements, setStatements] = useState<OwnerStatement[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({ property_id: '', period_start: firstOfMonth(), period_end: lastOfMonth() })
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }))

  const load = async () => {
    try {
      const { data } = await agencyApi.statements()
      setStatements((data as any).data?.results || (data as any).data || [])
    } catch {
      setStatements([])
    } finally {
      setLoading(false); setRefreshing(false)
    }
  }
  useEffect(() => { load() }, [])

  const generate = async () => {
    if (!form.property_id.trim()) { Alert.alert('Error', 'Enter a property ID.'); return }
    setSaving(true)
    try {
      await agencyApi.generateStatement(form.property_id.trim(), form.period_start, form.period_end)
      setShowForm(false)
      load()
    } catch (e: any) {
      Alert.alert('Error', e?.response?.data?.error?.message || 'Failed to generate statement.')
    } finally {
      setSaving(false)
    }
  }

  const issue = async (id: string) => { await agencyApi.issueStatement(id); load() }
  const payout = (id: string) => {
    Alert.alert('Pay Owner', 'Send M-Pesa payout for the net payable amount to the owner?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Pay', onPress: async () => {
          try { await agencyApi.executePayout(id); load() }
          catch (e: any) { Alert.alert('Error', e?.response?.data?.error?.message || 'Payout failed to initiate.') }
        },
      },
    ])
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
      <View style={styles.headerRow}>
        <Button label={showForm ? 'Cancel' : '+ Generate Statement'} onPress={() => setShowForm(!showForm)} color={agencyTheme.primary} size="sm" />
      </View>

      {showForm && (
        <Card style={styles.formCard}>
          <TextInput style={styles.input} placeholder="Property ID" value={form.property_id} onChangeText={(v) => set('property_id', v)} />
          <TextInput style={styles.input} placeholder="Period Start (YYYY-MM-DD)" value={form.period_start} onChangeText={(v) => set('period_start', v)} />
          <TextInput style={styles.input} placeholder="Period End (YYYY-MM-DD)" value={form.period_end} onChangeText={(v) => set('period_end', v)} />
          <Button label="Generate" onPress={generate} loading={saving} color={agencyTheme.primary} fullWidth />
        </Card>
      )}

      <FlatList
        data={statements}
        keyExtractor={(s) => s.id}
        contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} tintColor={agencyTheme.primary} />}
        renderItem={({ item: s }) => (
          <Card>
            <View style={styles.rowBetween}>
              <Text style={styles.propertyName}>{s.property_name}</Text>
              <StatusBadge status={s.status} />
            </View>
            <Text style={styles.meta}>{formatDate(s.period_start)} – {formatDate(s.period_end)} · {s.owner_name}</Text>

            <View style={styles.figuresGrid}>
              <View style={styles.figureCell}><Text style={styles.figureLabel}>Gross</Text><Text style={styles.figureValue}>{formatKES(s.gross_rent_collected)}</Text></View>
              <View style={styles.figureCell}><Text style={styles.figureLabel}>Commission</Text><Text style={[styles.figureValue, { color: agencyTheme.primaryDark }]}>{formatKES(s.agency_commission)}</Text></View>
              <View style={styles.figureCell}><Text style={styles.figureLabel}>Expenses</Text><Text style={[styles.figureValue, { color: '#d97706' }]}>{formatKES(s.approved_expenses)}</Text></View>
              <View style={styles.figureCell}><Text style={styles.figureLabel}>Net Payable</Text><Text style={[styles.figureValue, { color: '#16a34a', fontSize: typography.base }]}>{formatKES(s.net_payable)}</Text></View>
            </View>

            <View style={styles.actionsRow}>
              {s.status === 'draft' && <Button label="Issue" onPress={() => issue(s.id)} variant="outline" color={agencyTheme.primary} size="sm" />}
              {s.status === 'issued' && <Button label="Pay Owner" onPress={() => payout(s.id)} color="#16a34a" size="sm" />}
            </View>
          </Card>
        )}
        ListEmptyComponent={!loading ? <EmptyState emoji="🧾" message="No statements yet." /> : null}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  headerRow: { flexDirection: 'row', justifyContent: 'flex-end', padding: spacing.lg, paddingBottom: 4 },
  formCard: { marginHorizontal: spacing.lg, marginBottom: spacing.sm },
  input: { borderWidth: 1, borderColor: colors.gray200, borderRadius: radius.md, paddingHorizontal: 12, paddingVertical: 10, fontSize: typography.sm, marginBottom: spacing.sm, color: colors.gray900 },
  rowBetween: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 },
  propertyName: { fontSize: typography.base, fontWeight: '700', color: colors.gray900, flex: 1 },
  meta: { fontSize: typography.xs, color: colors.gray500, marginTop: 4 },
  figuresGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm, marginTop: spacing.md },
  figureCell: { minWidth: '45%' },
  figureLabel: { fontSize: 10, color: colors.gray400 },
  figureValue: { fontSize: typography.sm, fontWeight: '700', color: colors.gray800, marginTop: 1 },
  actionsRow: { flexDirection: 'row', gap: 8, marginTop: spacing.md },
})
