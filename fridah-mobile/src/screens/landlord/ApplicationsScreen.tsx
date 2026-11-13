import React, { useState, useCallback } from 'react'
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet,
  TextInput, RefreshControl, ActivityIndicator, Alert,
} from 'react-native'
import { useFocusEffect } from '@react-navigation/native'
import { rentalsApi } from '@/api/services'
import { Card, EmptyState, Badge } from '@/components/common/Cards'
import { Button } from '@/components/common/Button'
import { getTheme, colors, spacing, typography, radius } from '@/theme'
import { formatKES, formatDate } from '@/utils/formatters'

const STATUS_STYLE: Record<string, { color: string; bg: string }> = {
  pending: { color: '#b45309', bg: '#fffbeb' },
  approved: { color: '#15803d', bg: '#f0fdf4' },
  rejected: { color: '#dc2626', bg: '#fef2f2' },
  withdrawn: { color: colors.gray600, bg: colors.gray100 },
}

const FILTERS = [
  { value: 'pending', label: 'Pending' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
  { value: '', label: 'All' },
]

export const LandlordApplicationsScreen: React.FC = () => {
  const theme = getTheme('landlord')
  const [applications, setApplications] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [filter, setFilter] = useState('pending')
  const [reviewing, setReviewing] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [approveForm, setApproveForm] = useState({ rent_amount: '', deposit_amount: '', start_date: '' })

  const load = useCallback(async () => {
    try {
      const { data } = await rentalsApi.applications()
      setApplications((data as any).results || (data as any).data || [])
    } catch { setApplications([]) } finally { setLoading(false); setRefreshing(false) }
  }, [])

  useFocusEffect(useCallback(() => { load() }, [load]))

  const filtered = filter ? applications.filter((a) => a.status === filter) : applications

  const startReview = (a: any) => {
    setReviewing(a.id)
    setApproveForm({
      rent_amount: String(a.rent_amount), deposit_amount: String(a.rent_amount),
      start_date: new Date().toISOString().slice(0, 10),
    })
  }

  const approve = async (a: any) => {
    setSubmitting(true)
    try {
      await rentalsApi.approveApplication(a.id, {
        rent_amount: Number(approveForm.rent_amount),
        deposit_amount: Number(approveForm.deposit_amount),
        start_date: approveForm.start_date,
      })
      setReviewing('')
      await load()
      Alert.alert('Approved', 'Lease created for this tenant.')
    } catch (e: any) {
      Alert.alert('Could not approve', e?.response?.data?.error?.message || 'Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const reject = (a: any) => {
    Alert.alert('Reject application?', 'You can add a reason for the tenant.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Reject', style: 'destructive', onPress: async () => {
          try { await rentalsApi.rejectApplication(a.id, ''); await load() }
          catch { Alert.alert('Error', 'Failed to reject application.') }
        },
      },
    ])
  }

  if (loading) return <View style={styles.center}><ActivityIndicator size="large" color={theme.primary} /></View>

  return (
    <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
      <View style={styles.filterRow}>
        {FILTERS.map((f) => (
          <TouchableOpacity
            key={f.value}
            style={[styles.filterChip, filter === f.value && { backgroundColor: theme.primary }]}
            onPress={() => setFilter(f.value)}
          >
            <Text style={[styles.filterText, filter === f.value && { color: colors.white }]}>{f.label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <FlatList
        data={filtered}
        keyExtractor={(a) => a.id}
        contentContainerStyle={styles.list}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} tintColor={theme.primary} />}
        ListEmptyComponent={<EmptyState emoji="📋" message="No applications here" />}
        renderItem={({ item }) => {
          const s = STATUS_STYLE[item.status] || STATUS_STYLE.withdrawn
          return (
            <Card style={styles.card}>
              <View style={styles.row}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.title}>{item.tenant_name}</Text>
                  <Text style={styles.sub}>{item.property_name} · Unit {item.unit_number} · {formatKES(item.rent_amount)}/mo</Text>
                  {!!item.preferred_move_in_date && <Text style={styles.sub}>Preferred move-in: {formatDate(item.preferred_move_in_date)}</Text>}
                  {!!item.message && <Text style={styles.message}>"{item.message}"</Text>}
                </View>
                <Badge label={item.status} color={s.color} bg={s.bg} />
              </View>

              {item.status === 'pending' && (
                reviewing === item.id ? (
                  <View style={styles.reviewForm}>
                    <View style={styles.formRow}>
                      <TextInput style={styles.formInput} placeholder="Rent" keyboardType="number-pad" value={approveForm.rent_amount} onChangeText={(v) => setApproveForm(f => ({ ...f, rent_amount: v }))} />
                      <TextInput style={styles.formInput} placeholder="Deposit" keyboardType="number-pad" value={approveForm.deposit_amount} onChangeText={(v) => setApproveForm(f => ({ ...f, deposit_amount: v }))} />
                    </View>
                    <TextInput style={styles.input} placeholder="Start date YYYY-MM-DD" value={approveForm.start_date} onChangeText={(v) => setApproveForm(f => ({ ...f, start_date: v }))} />
                    <View style={{ flexDirection: 'row', gap: 10, marginTop: 6 }}>
                      <Button label="Cancel" onPress={() => setReviewing('')} variant="outline" style={{ flex: 1 }} />
                      <Button label="Confirm" onPress={() => approve(item)} loading={submitting} color="#16a34a" style={{ flex: 1 }} />
                    </View>
                  </View>
                ) : (
                  <View style={styles.actionRow}>
                    <TouchableOpacity style={styles.rejectBtn} onPress={() => reject(item)}><Text style={styles.rejectText}>Reject</Text></TouchableOpacity>
                    <TouchableOpacity style={[styles.approveBtn, { backgroundColor: theme.primary }]} onPress={() => startReview(item)}>
                      <Text style={styles.approveText}>Approve & Create Lease</Text>
                    </TouchableOpacity>
                  </View>
                )
              )}
            </Card>
          )
        }}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.gray50 },
  filterRow: { flexDirection: 'row', gap: 8, paddingHorizontal: spacing.lg, paddingTop: spacing.md, paddingBottom: 4 },
  filterChip: { paddingHorizontal: 14, paddingVertical: 7, borderRadius: 999, backgroundColor: colors.gray100 },
  filterText: { fontSize: typography.xs, fontWeight: '700', color: colors.gray600 },
  list: { padding: spacing.lg },
  card: { marginBottom: 10 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  title: { fontSize: typography.sm, fontWeight: '700', color: colors.gray900 },
  sub: { fontSize: typography.xs, color: colors.gray500, marginTop: 2 },
  message: { fontSize: typography.xs, color: colors.gray600, marginTop: 6, fontStyle: 'italic' },
  actionRow: { flexDirection: 'row', gap: 10, marginTop: 12, paddingTop: 12, borderTopWidth: 1, borderTopColor: colors.gray50 },
  rejectBtn: { flex: 1, paddingVertical: 10, borderRadius: radius.md, borderWidth: 1.5, borderColor: colors.gray200, alignItems: 'center' },
  rejectText: { color: '#dc2626', fontWeight: '700', fontSize: typography.xs },
  approveBtn: { flex: 1, paddingVertical: 10, borderRadius: radius.md, alignItems: 'center' },
  approveText: { color: colors.white, fontWeight: '700', fontSize: typography.xs },
  reviewForm: { marginTop: 12, paddingTop: 12, borderTopWidth: 1, borderTopColor: colors.gray50 },
  formRow: { flexDirection: 'row', gap: 8 },
  formInput: { flex: 1, borderWidth: 1.5, borderColor: colors.gray200, borderRadius: radius.md, paddingHorizontal: 10, paddingVertical: 9, fontSize: typography.xs, color: colors.gray900, backgroundColor: colors.white, marginBottom: 8 },
  input: { borderWidth: 1.5, borderColor: colors.gray200, borderRadius: radius.md, paddingHorizontal: 10, paddingVertical: 9, fontSize: typography.xs, color: colors.gray900, backgroundColor: colors.white },
})
