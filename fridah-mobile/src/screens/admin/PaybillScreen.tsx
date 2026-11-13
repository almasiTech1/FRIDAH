import React, { useState, useEffect, useCallback } from 'react'
import { View, Text, FlatList, RefreshControl, TextInput, StyleSheet, TouchableOpacity } from 'react-native'
import { paymentsApi } from '@/api/services'
import { Card, StatusBadge, EmptyState } from '@/components/common/Cards'
import { Button } from '@/components/common/Button'
import { getTheme, colors, spacing, typography, radius } from '@/theme'
import { formatKES } from '@/utils/formatters'

export const AdminPaybillScreen: React.FC = () => {
  const theme = getTheme('admin')
  const [transactions, setTransactions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [invoiceInputs, setInvoiceInputs] = useState<Record<string, string>>({})
  const [reconciling, setReconciling] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const { data } = await paymentsApi.paybillTransactions({ match_status: 'unmatched' })
      setTransactions((data as any).data?.results || (data as any).data || [])
    } catch { setTransactions([]) } finally { setLoading(false); setRefreshing(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const reconcile = async (transactionId: string) => {
    const invoiceId = invoiceInputs[transactionId]
    if (!invoiceId) return
    setReconciling(transactionId)
    try { await paymentsApi.reconcilePaybillTransaction(transactionId, invoiceId); load() }
    finally { setReconciling(null) }
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
      <FlatList
        data={transactions} keyExtractor={i => i.id}
        contentContainerStyle={{ padding: spacing.lg, gap: 12 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} tintColor={theme.primary} />}
        ListEmptyComponent={!loading ? <EmptyState emoji="✅" message="No unmatched paybill payments." /> : null}
        renderItem={({ item }) => (
          <Card style={{ padding: spacing.lg }}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 }}>
              <Text style={styles.receipt}>{item.mpesa_receipt_number}</Text>
              <Text style={styles.amount}>{formatKES(item.amount)}</Text>
            </View>
            <Text style={styles.meta}>Account ref: {item.bill_ref_number || '—'}</Text>
            <Text style={styles.meta}>{item.payer_name} ({item.msisdn})</Text>
            <View style={{ flexDirection: 'row', gap: 8, marginTop: 10 }}>
              <TextInput
                style={styles.input}
                placeholder="Invoice ID"
                placeholderTextColor={colors.gray400}
                value={invoiceInputs[item.id] || ''}
                onChangeText={(v) => setInvoiceInputs((s) => ({ ...s, [item.id]: v }))}
              />
              <Button label="Match" onPress={() => reconcile(item.id)} loading={reconciling === item.id} color={theme.primary} size="sm" />
            </View>
          </Card>
        )}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  receipt: { fontSize: typography.sm, fontWeight: '700', color: colors.gray900 },
  amount: { fontSize: typography.base, fontWeight: '800', color: colors.gray900 },
  meta: { fontSize: typography.xs, color: colors.gray500, marginTop: 2 },
  input: { flex: 1, borderWidth: 1.5, borderColor: colors.gray200, borderRadius: radius.md, paddingHorizontal: 12, fontSize: typography.sm, color: colors.gray900 },
})
