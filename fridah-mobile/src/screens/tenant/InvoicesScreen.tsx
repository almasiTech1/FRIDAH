import React, { useState, useEffect, useCallback } from 'react'
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet,
  RefreshControl, ActivityIndicator,
} from 'react-native'
import { rentalsApi } from '@/api/services'
import { MpesaPayModal } from '@/components/common/MpesaPayModal'
import { Card, StatusBadge, EmptyState } from '@/components/common/Cards'
import { getTheme, colors, spacing, typography, radius } from '@/theme'
import { formatKES, formatDate } from '@/utils/formatters'
import type { Invoice } from '@/types'

export const TenantInvoicesScreen: React.FC = () => {
  const theme = getTheme('tenant')
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [filter, setFilter] = useState('')
  const [payVisible, setPayVisible] = useState(false)
  const [selected, setSelected] = useState<Invoice | null>(null)

  const load = useCallback(async () => {
    try {
      const { data } = await rentalsApi.invoices()
      setInvoices(data.data?.results || [])
    } catch {
      setInvoices([
        { id: '1', invoice_number: 'INV-DEMO001', lease: '', tenant: '', tenant_name: '', invoice_type: 'rent', amount: 25000, amount_paid: 0, balance: 25000, period_start: '2026-07-01', period_end: '2026-07-31', due_date: '2026-07-05', status: 'pending', is_overdue: false, created_at: new Date().toISOString() },
        { id: '2', invoice_number: 'INV-DEMO002', lease: '', tenant: '', tenant_name: '', invoice_type: 'rent', amount: 25000, amount_paid: 25000, balance: 0, period_start: '2026-06-01', period_end: '2026-06-30', due_date: '2026-06-05', status: 'paid', is_overdue: false, created_at: new Date().toISOString() },
      ])
    } finally { setLoading(false); setRefreshing(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const filtered = filter ? invoices.filter(i => i.status === filter) : invoices

  const filters = [
    { key: '', label: 'All' },
    { key: 'pending', label: 'Pending' },
    { key: 'overdue', label: 'Overdue' },
    { key: 'paid', label: 'Paid' },
  ]

  return (
    <View style={styles.container}>
      {/* Filter tabs */}
      <View style={styles.filterRow}>
        {filters.map(f => (
          <TouchableOpacity
            key={f.key}
            style={[styles.filterBtn, filter === f.key && { backgroundColor: theme.primary }]}
            onPress={() => setFilter(f.key)}
          >
            <Text style={[styles.filterText, filter === f.key && { color: colors.white }]}>
              {f.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {loading ? (
        <ActivityIndicator size="large" color={theme.primary} style={{ marginTop: 40 }} />
      ) : (
        <FlatList
          data={filtered}
          keyExtractor={item => item.id}
          contentContainerStyle={styles.list}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} tintColor={theme.primary} />}
          ListEmptyComponent={<EmptyState emoji="🧾" message="No invoices found" />}
          renderItem={({ item }) => (
            <Card style={styles.card}>
              <View style={styles.cardTop}>
                <View>
                  <Text style={styles.invoiceNum}>{item.invoice_number}</Text>
                  <Text style={styles.period}>{formatDate(item.period_start)} — {formatDate(item.period_end)}</Text>
                </View>
                <StatusBadge status={item.status} />
              </View>
              <View style={styles.cardMid}>
                <View>
                  <Text style={styles.metaLabel}>Amount</Text>
                  <Text style={styles.amount}>{formatKES(item.amount)}</Text>
                </View>
                <View>
                  <Text style={styles.metaLabel}>Balance Due</Text>
                  <Text style={[styles.balance, { color: item.balance > 0 ? colors.red600 : colors.green600 }]}>
                    {formatKES(item.balance)}
                  </Text>
                </View>
                <View>
                  <Text style={styles.metaLabel}>Due Date</Text>
                  <Text style={styles.dueDate}>{formatDate(item.due_date)}</Text>
                </View>
              </View>
              {item.status !== 'paid' && item.status !== 'cancelled' && (
                <TouchableOpacity
                  style={[styles.payBtn, { backgroundColor: theme.primary }]}
                  onPress={() => { setSelected(item); setPayVisible(true) }}
                >
                  <Text style={styles.payBtnText}>Pay {formatKES(item.balance)} via M-Pesa</Text>
                </TouchableOpacity>
              )}
            </Card>
          )}
        />
      )}

      <MpesaPayModal
        visible={payVisible}
        amount={selected?.balance || 0}
        invoiceId={selected?.id}
        accentColor={theme.primary}
        description="Rent payment"
        onClose={() => setPayVisible(false)}
        onSuccess={() => { setPayVisible(false); load() }}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.gray50 },
  filterRow: { flexDirection: 'row', gap: 8, padding: spacing.lg, paddingBottom: 0 },
  filterBtn: {
    paddingHorizontal: 14, paddingVertical: 7, borderRadius: radius.full,
    backgroundColor: colors.gray100, borderWidth: 1, borderColor: colors.gray200,
  },
  filterText: { fontSize: typography.xs, fontWeight: '600', color: colors.gray600 },
  list: { padding: spacing.lg, gap: 12 },
  card: { padding: spacing.lg },
  cardTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 },
  invoiceNum: { fontSize: typography.xs, fontFamily: 'monospace', fontWeight: '700', color: colors.gray700 },
  period: { fontSize: typography.xs, color: colors.gray400, marginTop: 2 },
  cardMid: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 14 },
  metaLabel: { fontSize: typography.xs, color: colors.gray400, fontWeight: '500', marginBottom: 2 },
  amount: { fontSize: typography.base, fontWeight: '700', color: colors.gray900 },
  balance: { fontSize: typography.base, fontWeight: '700' },
  dueDate: { fontSize: typography.sm, fontWeight: '600', color: colors.gray700 },
  payBtn: { borderRadius: radius.lg, paddingVertical: 12, alignItems: 'center' },
  payBtnText: { color: colors.white, fontSize: typography.sm, fontWeight: '700' },
})
