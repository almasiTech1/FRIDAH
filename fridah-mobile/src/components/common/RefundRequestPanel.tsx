import React, { useEffect, useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, StyleSheet } from 'react-native'
import { paymentsApi, refundApi } from '@/api/services'
import { Card, Skeleton } from '@/components/common/Cards'
import { Button } from '@/components/common/Button'
import { colors, spacing, typography, radius } from '@/theme'
import { formatKES, formatDate } from '@/utils/formatters'

/** Pick one of your completed payments and ask for (part of) it back. Approval limits are enforced by the server. */
export const RefundRequestPanel: React.FC<{ color: string; onDone: () => void }> = ({ color, onDone }) => {
  const [payments, setPayments] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [picked, setPicked] = useState<any | null>(null)
  const [amount, setAmount] = useState('')
  const [reason, setReason] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    (async () => {
      try {
        const { data } = await paymentsApi.list()
        const rows = (data as any).data?.results || (data as any).results || []
        setPayments(rows.filter((p: any) => p.status === 'completed' && Number(p.amount) - Number(p.refunded_amount || 0) > 0))
      } catch { setError('Could not load your payments.') } finally { setLoading(false) }
    })()
  }, [])

  const remaining = (p: any) => Number(p.amount) - Number(p.refunded_amount || 0)
  const submit = async () => {
    if (!picked) return
    setSaving(true); setError('')
    try {
      await refundApi.request(picked.id, { amount, reason: reason.trim() })
      onDone()
    } catch (e: any) {
      setError(e?.response?.data?.error?.message || e?.response?.data?.detail || 'Could not submit the request.')
    } finally { setSaving(false) }
  }

  if (loading) return <Skeleton height={90} />
  return (
    <Card>
      <Text style={styles.title}>Request a refund</Text>
      {error ? <Text style={styles.error} accessibilityRole="alert">{error}</Text> : null}
      {!picked ? (
        payments.length ? payments.map((p) => (
          <TouchableOpacity key={p.id} style={styles.pay} accessibilityRole="button" onPress={() => { setPicked(p); setAmount(String(remaining(p))) }}>
            <Text style={styles.payRef}>{p.reference}</Text>
            <Text style={styles.meta}>{formatKES(p.amount)} · {formatDate(p.created_at)} · up to {formatKES(remaining(p))} refundable</Text>
          </TouchableOpacity>
        )) : <Text style={styles.meta}>You have no completed payments that can be refunded.</Text>
      ) : (
        <View style={{ gap: spacing.sm }}>
          <Text style={styles.meta}>{picked.reference} · up to {formatKES(remaining(picked))}</Text>
          <TextInput style={styles.input} value={amount} onChangeText={setAmount} keyboardType="numeric" placeholder="Amount (KES)" accessibilityLabel="Refund amount" />
          <TextInput style={styles.input} value={reason} onChangeText={setReason} placeholder="Why should this be refunded?" accessibilityLabel="Refund reason" />
          <Text style={styles.meta}>Larger refunds need a FRIDAH administrator. You cannot approve your own request.</Text>
          <View style={styles.row}>
            <Button label="Submit request" size="sm" color={color} loading={saving} disabled={!amount || !reason.trim()} onPress={submit} />
            <Button label="Back" size="sm" variant="outline" color={colors.gray600} onPress={() => { setPicked(null); setError('') }} />
          </View>
        </View>
      )}
    </Card>
  )
}

const styles = StyleSheet.create({
  title: { fontSize: typography.base, fontWeight: '700', color: colors.gray900, marginBottom: spacing.sm },
  pay: { paddingVertical: spacing.sm, borderTopWidth: 1, borderTopColor: colors.gray100 },
  payRef: { fontSize: typography.sm, fontWeight: '600', color: colors.gray900 },
  meta: { fontSize: typography.xs, color: colors.gray500 },
  input: { borderWidth: 1, borderColor: colors.gray200, borderRadius: radius.md, padding: spacing.md, backgroundColor: colors.white },
  row: { flexDirection: 'row', gap: spacing.sm },
  error: { color: '#dc2626', fontSize: typography.sm, marginBottom: spacing.sm },
})
