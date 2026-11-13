import React, { useCallback, useEffect, useState } from 'react'
import { View, Text, FlatList, TextInput, StyleSheet, RefreshControl } from 'react-native'
import { refundApi } from '@/api/services'
import { useAuthStore } from '@/stores/authStore'
import { Card, StatusBadge, EmptyState, Skeleton, FadeIn } from '@/components/common/Cards'
import { Button } from '@/components/common/Button'
import { RefundRequestPanel } from '@/components/common/RefundRequestPanel'
import { colors, spacing, typography, radius } from '@/theme'
import { formatKES, formatDate, refundStatusLabel } from '@/utils/formatters'

/** Refund and reversal requests visible to the signed-in user, with approve / reject / cancel. */
export const RefundsQueue: React.FC<{ color: string; admin?: boolean; canRequest?: boolean }> = ({ color, admin = false, canRequest = false }) => {
  const { user } = useAuthStore()
  const [items, setItems] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState<string | null>(null)
  const [rejecting, setRejecting] = useState<string | null>(null)
  const [comment, setComment] = useState('')
  const [rowError, setRowError] = useState<Record<string, string>>({})
  const [requesting, setRequesting] = useState(false)
  const [paying, setPaying] = useState<string | null>(null)
  const [ref, setRef] = useState('')

  const load = useCallback(async () => {
    setError('')
    try {
      const { data } = await refundApi.list()
      setItems((data as any).data?.results || (data as any).results || [])
    } catch { setError('Could not load refund requests. Pull down to retry.') }
    finally { setLoading(false); setRefreshing(false) }
  }, [])
  useEffect(() => { load() }, [load])

  const run = async (id: string, fn: () => Promise<unknown>) => {
    setBusy(id); setRowError((e) => ({ ...e, [id]: '' }))
    try { await fn(); setRejecting(null); setComment(''); await load() }
    catch (e: any) {
      setRowError((r) => ({ ...r, [id]: e?.response?.data?.error?.message || e?.response?.data?.detail || 'That action failed.' }))
    } finally { setBusy(null) }
  }

  if (loading) return <View style={{ padding: spacing.lg, gap: spacing.md }}><Skeleton height={110} /><Skeleton height={110} /></View>

  return (
    <FlatList
      data={items}
      keyExtractor={(r) => r.id}
      contentContainerStyle={{ padding: spacing.lg, gap: spacing.md, flexGrow: 1 }}
      refreshControl={<RefreshControl refreshing={refreshing} tintColor={color} onRefresh={() => { setRefreshing(true); load() }} />}
      ListHeaderComponent={
        <View style={{ gap: spacing.md }}>
          {error ? <Text style={styles.error} accessibilityRole="alert">{error}</Text> : null}
          {canRequest ? (requesting
            ? <RefundRequestPanel color={color} onDone={() => { setRequesting(false); load() }} />
            : <Button label="Request a refund" variant="outline" color={color} onPress={() => setRequesting(true)} />) : null}
        </View>
      }
      ListEmptyComponent={<EmptyState emoji="↩️" message="No refund requests." />}
      renderItem={({ item: r, index }) => (
        <FadeIn index={index}>
          <Card>
            <View style={styles.rowBetween}>
              <Text style={styles.amount}>{formatKES(r.amount)} · {r.kind === 'reversal' ? 'Reversal' : 'Refund'}</Text>
              <StatusBadge status={r.status} />
            </View>
            <Text style={styles.meta}>{refundStatusLabel(r.status)} · {r.payment_reference} ({formatKES(r.payment_amount)})</Text>
            <Text style={styles.meta}>Requested by {r.requested_by_name || '—'} · {formatDate(r.created_at)}</Text>
            <Text style={styles.reason}>“{r.reason}”</Text>
            {r.status === 'requested' && r.approval_level === 'admin' ? <Text style={styles.meta}>Needs a FRIDAH administrator</Text> : null}
            {r.decision_comment ? <Text style={styles.meta}>{r.decided_by_name}: {r.decision_comment}</Text> : null}
            {r.payout_reference ? <Text style={[styles.meta, { color: '#047857' }]}>Paid out · ref {r.payout_reference}</Text> : null}

            {admin && r.status === 'approved' ? (
              paying === r.id ? (
                <View style={{ marginTop: spacing.md, gap: spacing.sm }}>
                  <TextInput style={styles.input} value={ref} onChangeText={setRef} autoCapitalize="characters"
                             placeholder="M-Pesa reference of the payout" accessibilityLabel="Payout reference" />
                  <View style={styles.row}>
                    <Button label="Save payout" size="sm" color={color} disabled={ref.trim().length < 6} loading={busy === r.id}
                            onPress={() => run(r.id, async () => { await refundApi.markPaid(r.id, ref.trim()); setPaying(null); setRef('') })} />
                    <Button label="Cancel" size="sm" variant="outline" color={colors.gray600} onPress={() => setPaying(null)} />
                  </View>
                </View>
              ) : (
                <View style={[styles.row, { marginTop: spacing.md }]}>
                  {r.auto_payout_available && r.payout_status !== 'processing'
                    ? <Button label="Send via M-Pesa" size="sm" color="#059669" loading={busy === r.id} onPress={() => run(r.id, () => refundApi.payOut(r.id))} />
                    : null}
                  {r.payout_status === 'processing' ? <Text style={styles.meta}>M-Pesa payout processing…</Text> : null}
                  <Button label="Record payout" size="sm" variant="outline" color={colors.gray600} onPress={() => { setPaying(r.id); setRef('') }} />
                </View>
              )
            ) : null}

            {rejecting === r.id ? (
              <View style={{ marginTop: spacing.md, gap: spacing.sm }}>
                <TextInput style={styles.input} value={comment} onChangeText={setComment} multiline
                           placeholder="Reason for rejecting (required)" accessibilityLabel="Reason" />
                <View style={styles.row}>
                  <Button label="Send" size="sm" color={color} disabled={!comment.trim()} loading={busy === r.id}
                          onPress={() => run(r.id, () => refundApi.reject(r.id, comment.trim()))} />
                  <Button label="Cancel" size="sm" variant="outline" color={colors.gray600} onPress={() => setRejecting(null)} />
                </View>
              </View>
            ) : (
              <View style={[styles.row, { marginTop: spacing.md }]}>
                {r.can_decide ? (
                  <>
                    <Button label="Approve" size="sm" color="#059669" loading={busy === r.id} onPress={() => run(r.id, () => refundApi.approve(r.id))} />
                    <Button label="Reject" size="sm" variant="outline" color="#dc2626" onPress={() => { setRejecting(r.id); setComment('') }} />
                  </>
                ) : null}
                {r.status === 'requested' && r.requested_by === user?.id ? (
                  <Button label="Cancel request" size="sm" variant="outline" color={colors.gray600} disabled={busy === r.id}
                          onPress={() => run(r.id, () => refundApi.cancel(r.id))} />
                ) : null}
              </View>
            )}
            {rowError[r.id] ? <Text style={styles.error} accessibilityRole="alert">{rowError[r.id]}</Text> : null}
          </Card>
        </FadeIn>
      )}
    />
  )
}

const styles = StyleSheet.create({
  rowBetween: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: spacing.sm },
  row: { flexDirection: 'row', gap: spacing.sm, flexWrap: 'wrap' },
  amount: { fontSize: typography.base, fontWeight: '700', color: colors.gray900, flex: 1 },
  meta: { fontSize: typography.xs, color: colors.gray500, marginTop: 2 },
  reason: { fontSize: typography.sm, color: colors.gray700, marginTop: 6 },
  input: { borderWidth: 1, borderColor: colors.gray200, borderRadius: radius.md, padding: spacing.md, minHeight: 64, textAlignVertical: 'top' },
  error: { color: '#dc2626', marginTop: spacing.sm, fontSize: typography.sm },
})
