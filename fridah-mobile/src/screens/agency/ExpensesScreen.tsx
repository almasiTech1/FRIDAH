import React, { useState, useEffect } from 'react'
import { View, Text, FlatList, TouchableOpacity, StyleSheet, RefreshControl, TextInput, Alert, Switch } from 'react-native'
import { useAuthStore } from '@/stores/authStore'
import { agencyApi } from '@/api/services'
import { Card, EmptyState } from '@/components/common/Cards'
import { Button } from '@/components/common/Button'
import { agencyTheme, colors, spacing, typography, radius } from '@/theme'
import { formatKES, formatDate } from '@/utils/formatters'
import type { AgencyExpense } from '@/types'

const CATEGORIES: { value: AgencyExpense['category']; label: string }[] = [
  { value: 'maintenance', label: 'Maintenance' },
  { value: 'utilities', label: 'Utilities' },
  { value: 'compliance', label: 'Compliance' },
  { value: 'security', label: 'Security' },
  { value: 'cleaning', label: 'Cleaning' },
  { value: 'other', label: 'Other' },
]

export const AgencyExpensesScreen: React.FC = () => {
  const { agencies } = useAuthStore()
  const agency = agencies[0]
  const [expenses, setExpenses] = useState<AgencyExpense[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    property: '', category: 'maintenance' as AgencyExpense['category'], amount: '',
    incurred_on: new Date().toISOString().slice(0, 10), description: '', is_deductible_from_owner: true,
  })
  const set = (k: string, v: string | boolean) => setForm((f) => ({ ...f, [k]: v }))

  const load = async () => {
    try {
      if (!agency) { setExpenses([]); return }
      const { data } = await agencyApi.expenses(agency.id)
      setExpenses((data as any).data?.results || (data as any).data || [])
    } catch {
      setExpenses([])
    } finally {
      setLoading(false); setRefreshing(false)
    }
  }
  useEffect(() => { load() }, [agency])

  const save = async () => {
    if (!agency) return
    if (!form.property.trim() || !form.amount.trim() || !form.description.trim()) {
      Alert.alert('Error', 'Property ID, amount, and description are required.')
      return
    }
    setSaving(true)
    try {
      await agencyApi.createExpense(agency.id, {
        property: form.property.trim(), category: form.category, amount: parseFloat(form.amount) || 0,
        incurred_on: form.incurred_on, description: form.description.trim(),
        is_deductible_from_owner: form.is_deductible_from_owner,
      })
      setShowForm(false)
      setForm({ property: '', category: 'maintenance', amount: '', incurred_on: new Date().toISOString().slice(0, 10), description: '', is_deductible_from_owner: true })
      load()
    } catch (e: any) {
      Alert.alert('Error', e?.response?.data?.error?.message || 'Failed to save expense.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
      <View style={styles.headerRow}>
        <Button label={showForm ? 'Cancel' : '+ Record Expense'} onPress={() => setShowForm(!showForm)} color={agencyTheme.primary} size="sm" />
      </View>

      {showForm && (
        <Card style={styles.formCard}>
          <TextInput style={styles.input} placeholder="Property ID" value={form.property} onChangeText={(v) => set('property', v)} />
          <View style={styles.categoryRow}>
            {CATEGORIES.map((c) => (
              <TouchableOpacity key={c.value} style={[styles.categoryChip, form.category === c.value && { borderColor: agencyTheme.primary, backgroundColor: agencyTheme.primaryBg }]} onPress={() => set('category', c.value)}>
                <Text style={[styles.categoryChipText, form.category === c.value && { color: agencyTheme.primaryDark, fontWeight: '700' }]}>{c.label}</Text>
              </TouchableOpacity>
            ))}
          </View>
          <TextInput style={styles.input} placeholder="Amount (KES)" value={form.amount} onChangeText={(v) => set('amount', v)} keyboardType="numeric" />
          <TextInput style={styles.input} placeholder="Date Incurred (YYYY-MM-DD)" value={form.incurred_on} onChangeText={(v) => set('incurred_on', v)} />
          <TextInput style={styles.input} placeholder="Description" value={form.description} onChangeText={(v) => set('description', v)} />
          <View style={styles.switchRow}>
            <Text style={styles.switchLabel}>Deduct from owner's next statement</Text>
            <Switch value={form.is_deductible_from_owner} onValueChange={(v) => set('is_deductible_from_owner', v)} trackColor={{ true: agencyTheme.primary }} />
          </View>
          <Button label="Save Expense" onPress={save} loading={saving} color={agencyTheme.primary} fullWidth />
        </Card>
      )}

      <FlatList
        data={expenses}
        keyExtractor={(e) => e.id}
        contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} tintColor={agencyTheme.primary} />}
        renderItem={({ item: e }) => (
          <Card>
            <View style={styles.rowBetween}>
              <View style={{ flex: 1 }}>
                <Text style={styles.description}>{e.description}</Text>
                <Text style={styles.meta}>{e.property_name} · {formatDate(e.incurred_on)}{e.is_deductible_from_owner ? ' · Deductible' : ''}</Text>
              </View>
              <Text style={styles.amount}>{formatKES(e.amount)}</Text>
            </View>
            <View style={[styles.categoryBadge, { backgroundColor: colors.gray100 }]}>
              <Text style={styles.categoryBadgeText}>{e.category}</Text>
            </View>
          </Card>
        )}
        ListEmptyComponent={!loading ? <EmptyState emoji="🧾" message="No expenses recorded yet." /> : null}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  headerRow: { flexDirection: 'row', justifyContent: 'flex-end', padding: spacing.lg, paddingBottom: 4 },
  formCard: { marginHorizontal: spacing.lg, marginBottom: spacing.sm },
  input: { borderWidth: 1, borderColor: colors.gray200, borderRadius: radius.md, paddingHorizontal: 12, paddingVertical: 10, fontSize: typography.sm, marginBottom: spacing.sm, color: colors.gray900 },
  categoryRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: spacing.sm },
  categoryChip: { borderWidth: 1, borderColor: colors.gray200, borderRadius: radius.full, paddingHorizontal: 12, paddingVertical: 6 },
  categoryChipText: { fontSize: typography.xs, color: colors.gray600 },
  switchRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: spacing.md },
  switchLabel: { fontSize: typography.sm, color: colors.gray600, flex: 1, marginRight: spacing.sm },
  rowBetween: { flexDirection: 'row', alignItems: 'flex-start', gap: 8 },
  description: { fontSize: typography.sm, fontWeight: '700', color: colors.gray900 },
  meta: { fontSize: typography.xs, color: colors.gray500, marginTop: 2 },
  amount: { fontSize: typography.base, fontWeight: '700', color: '#d97706' },
  categoryBadge: { alignSelf: 'flex-start', borderRadius: radius.full, paddingHorizontal: 10, paddingVertical: 3, marginTop: spacing.sm },
  categoryBadgeText: { fontSize: 11, color: colors.gray600, textTransform: 'capitalize' },
})
