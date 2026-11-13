import React, { useState, useEffect } from 'react'
import { View, Text, FlatList, TouchableOpacity, StyleSheet, RefreshControl, TextInput, Alert } from 'react-native'
import { useAuthStore } from '@/stores/authStore'
import { agencyApi } from '@/api/services'
import { Card, StatusBadge, EmptyState } from '@/components/common/Cards'
import { Button } from '@/components/common/Button'
import { agencyTheme, colors, spacing, typography, radius } from '@/theme'
import { formatDate } from '@/utils/formatters'
import type { PropertyManagementAssignment } from '@/types'

export const AgencyPropertiesScreen: React.FC = () => {
  const { agencies } = useAuthStore()
  const agency = agencies[0]
  const [assignments, setAssignments] = useState<PropertyManagementAssignment[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({ property_id: '', management_fee_percent: '5', payout_rule: 'owner_direct' as 'owner_direct' | 'agency_collects' })
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }))

  const load = async () => {
    try {
      if (!agency) { setAssignments([]); return }
      const { data } = await agencyApi.assignments({ agency: agency.id })
      setAssignments((data as any).data?.results || (data as any).data || [])
    } catch {
      setAssignments([])
    } finally {
      setLoading(false); setRefreshing(false)
    }
  }
  useEffect(() => { load() }, [agency])

  const assign = async () => {
    if (!agency) return
    if (!form.property_id.trim()) { Alert.alert('Error', 'Enter the property ID (ask the owner for it).'); return }
    setSaving(true)
    try {
      await agencyApi.assignProperty({
        property_id: form.property_id.trim(), agency_id: agency.id,
        start_date: new Date().toISOString().slice(0, 10),
        management_fee_percent: parseFloat(form.management_fee_percent) || 5,
        payout_rule: form.payout_rule,
      })
      setShowForm(false)
      setForm({ property_id: '', management_fee_percent: '5', payout_rule: 'owner_direct' })
      load()
    } catch (e: any) {
      Alert.alert('Error', e?.response?.data?.error?.message || 'Failed to assign property.')
    } finally {
      setSaving(false)
    }
  }

  const endAssignment = (id: string) => {
    Alert.alert('End Management', 'End this management assignment?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'End', style: 'destructive', onPress: async () => { await agencyApi.endAssignment(id, 'Ended from mobile app'); load() } },
    ])
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
      <View style={styles.headerRow}>
        <Button label={showForm ? 'Cancel' : '+ Assign Property'} onPress={() => setShowForm(!showForm)} color={agencyTheme.primary} size="sm" />
      </View>

      {showForm && (
        <Card style={styles.formCard}>
          <Text style={styles.formHint}>Ask the property owner for their Property ID to link it here.</Text>
          <TextInput style={styles.input} placeholder="Property ID" value={form.property_id} onChangeText={(v) => set('property_id', v)} />
          <TextInput style={styles.input} placeholder="Management Fee %" value={form.management_fee_percent} onChangeText={(v) => set('management_fee_percent', v)} keyboardType="numeric" />
          <View style={styles.payoutRow}>
            {(['owner_direct', 'agency_collects'] as const).map((rule) => (
              <TouchableOpacity key={rule} style={[styles.payoutOption, form.payout_rule === rule && { borderColor: agencyTheme.primary, backgroundColor: agencyTheme.primaryBg }]} onPress={() => setForm((f) => ({ ...f, payout_rule: rule }))}>
                <Text style={[styles.payoutOptionText, form.payout_rule === rule && { color: agencyTheme.primaryDark, fontWeight: '700' }]}>
                  {rule === 'owner_direct' ? 'Owner receives directly' : 'Agency collects & remits'}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
          <Button label="Assign" onPress={assign} loading={saving} color={agencyTheme.primary} fullWidth />
        </Card>
      )}

      <FlatList
        data={assignments}
        keyExtractor={(a) => a.id}
        contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} tintColor={agencyTheme.primary} />}
        renderItem={({ item: a }) => (
          <Card>
            <View style={styles.rowBetween}>
              <Text style={styles.propertyName}>{a.property_name}</Text>
              <StatusBadge status={a.status} />
            </View>
            <Text style={styles.meta}>Owner: {a.owner_name} · Fee: {a.management_fee_percent}% · Since {formatDate(a.start_date)}</Text>
            {a.status === 'active' && (
              <TouchableOpacity onPress={() => endAssignment(a.id)} style={{ marginTop: spacing.sm }}>
                <Text style={styles.endLink}>End Management</Text>
              </TouchableOpacity>
            )}
          </Card>
        )}
        ListEmptyComponent={!loading ? <EmptyState emoji="🏠" message="No properties assigned yet." /> : null}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  headerRow: { flexDirection: 'row', justifyContent: 'flex-end', padding: spacing.lg, paddingBottom: 4 },
  formCard: { marginHorizontal: spacing.lg, marginBottom: spacing.sm },
  formHint: { fontSize: typography.xs, color: colors.gray400, marginBottom: spacing.sm },
  input: { borderWidth: 1, borderColor: colors.gray200, borderRadius: radius.md, paddingHorizontal: 12, paddingVertical: 10, fontSize: typography.sm, marginBottom: spacing.sm, color: colors.gray900 },
  payoutRow: { gap: 8, marginBottom: spacing.md },
  payoutOption: { borderWidth: 1, borderColor: colors.gray200, borderRadius: radius.md, padding: 10 },
  payoutOptionText: { fontSize: typography.sm, color: colors.gray600 },
  rowBetween: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 },
  propertyName: { fontSize: typography.base, fontWeight: '700', color: colors.gray900, flex: 1 },
  meta: { fontSize: typography.xs, color: colors.gray500, marginTop: 4 },
  endLink: { fontSize: typography.xs, color: colors.red600, fontWeight: '600' },
})
