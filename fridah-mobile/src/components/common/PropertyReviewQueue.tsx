import React, { useCallback, useEffect, useState } from 'react'
import { View, Text, FlatList, TextInput, StyleSheet, RefreshControl } from 'react-native'
import { approvalApi } from '@/api/services'
import { Card, StatusBadge, EmptyState, Skeleton, FadeIn } from '@/components/common/Cards'
import { Button } from '@/components/common/Button'
import { colors, spacing, typography, radius } from '@/theme'
import { reviewStateLabel, partyLabel } from '@/utils/formatters'

type Action = 'approve' | 'reject' | 'request_changes'

/** Properties waiting on the signed-in landlord (role="landlord") or on an administrator (role="admin"). */
export const PropertyReviewQueue: React.FC<{ role: 'landlord' | 'admin'; color: string }> = ({ role, color }) => {
  const [items, setItems] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState<string | null>(null)
  const [pending, setPending] = useState<{ id: string; action: 'reject' | 'request_changes' } | null>(null)
  const [comment, setComment] = useState('')

  const load = useCallback(async () => {
    setError('')
    try {
      const { data } = await approvalApi.queue()
      setItems((data as any).data?.results || [])
    } catch {
      setError('Could not load the review queue. Pull down to retry.')
    } finally {
      setLoading(false); setRefreshing(false)
    }
  }, [])
  useEffect(() => { load() }, [load])

  const send = async (p: any, action: Action, text = '') => {
    setBusy(p.id); setError('')
    try {
      if (role === 'admin') await approvalApi.adminDecision(p.id, action, text)
      else await approvalApi.landlordDecision(p.id, action, text)
      setPending(null); setComment('')
      await load()
    } catch (e: any) {
      setError(e?.response?.data?.error?.message || e?.response?.data?.detail || 'That action failed.')
    } finally {
      setBusy(null)
    }
  }

  if (loading) {
    return <View style={{ padding: spacing.lg, gap: spacing.md }}><Skeleton height={110} /><Skeleton height={110} /></View>
  }

  return (
    <FlatList
      data={items}
      keyExtractor={(p) => p.id}
      contentContainerStyle={{ padding: spacing.lg, gap: spacing.md, flexGrow: 1 }}
      refreshControl={<RefreshControl refreshing={refreshing} tintColor={color} onRefresh={() => { setRefreshing(true); load() }} />}
      ListHeaderComponent={error ? <Text style={styles.error} accessibilityRole="alert">{error}</Text> : null}
      ListEmptyComponent={<EmptyState emoji="✅" message={role === 'admin' ? 'Nothing is waiting for admin review.' : 'No properties are waiting for your approval.'} />}
      renderItem={({ item: p, index }) => (
        <FadeIn index={index}>
          <Card>
            <View style={styles.rowBetween}>
              <Text style={styles.name}>{p.name}</Text>
              <StatusBadge status={p.review_state} />
            </View>
            <Text style={styles.meta}>
              {p.town}, {p.county}{p.submitted_by_agency ? ` · Submitted by ${p.submitted_by_agency}` : ''}
              {role === 'admin' ? ` · Owner ${p.landlord_name}` : ''}
            </Text>
            <Text style={[styles.meta, p.age_days >= 3 && { color: '#d97706', fontWeight: '600' }]}>
              Waiting {p.age_days} day{p.age_days === 1 ? '' : 's'} · v{p.submission_version}
            </Text>
            {p.requires_landlord_approval && (
              <Text style={styles.meta}>
                Needs {p.missing_approvals.map(partyLabel).join(' and ')} approval before going live.
              </Text>
            )}
            <Text style={styles.state}>{reviewStateLabel(p.review_state)}</Text>

            {pending && pending.id === p.id ? (
              <View style={{ marginTop: spacing.md, gap: spacing.sm }}>
                <Text style={styles.label}>{pending.action === 'reject' ? 'Why are you rejecting this property?' : 'What needs to change?'}</Text>
                <TextInput
                  style={styles.input} value={comment} onChangeText={setComment} multiline
                  placeholder="Required - the submitter will see this" accessibilityLabel="Reason"
                />
                <View style={styles.row}>
                  <Button label="Send" size="sm" color={color} loading={busy === p.id} disabled={!comment.trim()}
                          onPress={() => send(p, pending.action, comment.trim())} />
                  <Button label="Cancel" size="sm" variant="outline" color={colors.gray600} onPress={() => setPending(null)} />
                </View>
              </View>
            ) : (
              <View style={[styles.row, { marginTop: spacing.md }]}>
                <Button label="Approve" size="sm" color="#059669" loading={busy === p.id} onPress={() => send(p, 'approve')} />
                <Button label="Changes" size="sm" variant="outline" color="#2563eb"
                        onPress={() => { setPending({ id: p.id, action: 'request_changes' }); setComment('') }} />
                <Button label="Reject" size="sm" variant="outline" color="#dc2626"
                        onPress={() => { setPending({ id: p.id, action: 'reject' }); setComment('') }} />
              </View>
            )}
          </Card>
        </FadeIn>
      )}
    />
  )
}

const styles = StyleSheet.create({
  rowBetween: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: spacing.sm },
  row: { flexDirection: 'row', gap: spacing.sm, flexWrap: 'wrap' },
  name: { fontSize: typography.base, fontWeight: '700', color: colors.gray900, flex: 1 },
  meta: { fontSize: typography.xs, color: colors.gray500, marginTop: 2 },
  state: { fontSize: typography.xs, color: colors.gray700, marginTop: 6, fontWeight: '600' },
  label: { fontSize: typography.sm, fontWeight: '600', color: colors.gray700 },
  input: { borderWidth: 1, borderColor: colors.gray200, borderRadius: radius.md, padding: spacing.md, minHeight: 72, textAlignVertical: 'top' },
  error: { color: '#dc2626', marginBottom: spacing.sm, fontSize: typography.sm },
})
