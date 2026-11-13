import React, { useCallback, useEffect, useState } from 'react'
import { View, Text, ScrollView, TextInput, StyleSheet, RefreshControl } from 'react-native'
import { reconciliationApi } from '@/api/services'
import { Card, Skeleton, FadeIn } from '@/components/common/Cards'
import { Button } from '@/components/common/Button'
import { colors, spacing, typography, radius, getTheme } from '@/theme'
import { formatKES, formatDate } from '@/utils/formatters'

const iso = (d: Date) => d.toISOString().slice(0, 10)

/** Settlement position, internal books check and open discrepancies. Statement CSV upload is web-only. */
export const AdminReconciliationScreen: React.FC = () => {
  const theme = getTheme('admin')
  const [settlement, setSettlement] = useState<any | null>(null)
  const [runs, setRuns] = useState<any[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [items, setItems] = useState<any[]>([])
  const [resolving, setResolving] = useState<string | null>(null)
  const [note, setNote] = useState('')
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setError('')
    try {
      const [s, r] = await Promise.all([reconciliationApi.settlement(), reconciliationApi.runs()])
      setSettlement((s.data as any).data)
      setRuns((r.data as any).data?.results || (r.data as any).results || [])
    } catch { setError('Could not load reconciliation data. Pull down to retry.') }
    finally { setLoading(false); setRefreshing(false) }
  }, [])
  useEffect(() => { load() }, [load])

  const openRun = async (id: string) => {
    if (selected === id) { setSelected(null); return }
    setSelected(id); setItems([])
    try { setItems(((await reconciliationApi.run(id)).data as any).data.items) } catch { setError('Could not load that run.') }
  }
  const runCheck = async () => {
    setBusy(true); setError(''); setMsg('')
    const y = iso(new Date(Date.now() - 86400000))
    try {
      const d: any = ((await reconciliationApi.runInternal(y, y)).data as any).data
      setMsg(`Checked ${d.rows_checked} payments: ${d.issues} issue(s).`)
      await load(); await openRun(d.id)
    } catch { setError('The check failed. Please try again.') } finally { setBusy(false) }
  }
  const resolve = async (i: any) => {
    try {
      await reconciliationApi.resolveItem(i.id, note.trim())
      setResolving(null); setNote('')
      if (selected) setItems(((await reconciliationApi.run(selected)).data as any).data.items)
      await load()
    } catch (e: any) { setError(e?.response?.data?.error?.message || 'Could not resolve this item.') }
  }

  if (loading) return <View style={{ padding: spacing.lg, gap: spacing.md }}><Skeleton height={120} /><Skeleton height={90} /></View>

  const cards = settlement ? [
    ['Collected', settlement.gross_collected], ['Commission', settlement.platform_commission],
    ['Owed in wallets', settlement.wallet_liability], ['Refunds awaiting payout', settlement.refunds_awaiting_payout],
  ] : []

  return (
    <ScrollView style={{ backgroundColor: colors.gray50 }} contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}
                refreshControl={<RefreshControl refreshing={refreshing} tintColor={theme.primary} onRefresh={() => { setRefreshing(true); load() }} />}>
      {error ? <Text style={styles.error} accessibilityRole="alert">{error}</Text> : null}
      <Card>
        <Text style={styles.title}>Settlement (last 30 days)</Text>
        <View style={styles.grid}>
          {cards.map(([l, v]) => (
            <View key={l as string} style={styles.cell}><Text style={styles.meta}>{l}</Text><Text style={styles.val}>{formatKES(v as string)}</Text></View>
          ))}
        </View>
      </Card>
      <Button label="Run books check for yesterday" color={theme.primary} loading={busy} onPress={runCheck} />
      {msg ? <Text style={styles.ok} accessibilityRole="alert">{msg}</Text> : null}
      <Text style={styles.meta}>To reconcile against a Safaricom statement, upload the CSV from the web portal.</Text>

      {runs.map((r, idx) => (
        <FadeIn key={r.id} index={idx}>
          <Card>
            <View style={styles.rowBetween}>
              <Text style={styles.name}>{r.source === 'statement' ? `Statement ${r.file_name}` : 'Internal check'}</Text>
              <Text style={[styles.pill, { backgroundColor: r.open_issues ? '#fee2e2' : '#dcfce7', color: r.open_issues ? '#dc2626' : '#16a34a' }]}>{r.open_issues} open</Text>
            </View>
            <Text style={styles.meta}>{formatDate(r.period_start)} – {formatDate(r.period_end)} · {r.rows_checked} checked · {r.matched} matched</Text>
            <View style={{ marginTop: spacing.sm }}>
              <Button label={selected === r.id ? 'Hide' : 'View'} size="sm" variant="outline" color={colors.gray600} onPress={() => openRun(r.id)} />
            </View>
            {selected === r.id ? (
              <View style={{ marginTop: spacing.md, gap: spacing.sm }}>
                {!items.length ? <Text style={styles.ok}>Everything in this run reconciles.</Text> : null}
                {items.map((i) => (
                  <View key={i.id} style={styles.item}>
                    <Text style={styles.itemKind}>{i.kind_label}</Text>
                    <Text style={styles.meta}>{i.note}</Text>
                    {i.resolved ? <Text style={styles.ok}>Resolved: {i.resolution_note}</Text> : resolving === i.id ? (
                      <View style={{ gap: spacing.sm, marginTop: spacing.sm }}>
                        <TextInput style={styles.input} value={note} onChangeText={setNote} placeholder="What was done / why this is fine (required)" accessibilityLabel="Resolution note" />
                        <Button label="Mark resolved" size="sm" color={theme.primary} disabled={!note.trim()} onPress={() => resolve(i)} />
                      </View>
                    ) : <Button label="Resolve" size="sm" variant="outline" color={colors.gray600} onPress={() => { setResolving(i.id); setNote('') }} />}
                  </View>
                ))}
              </View>
            ) : null}
          </Card>
        </FadeIn>
      ))}
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  title: { fontSize: typography.base, fontWeight: '700', color: colors.gray900, marginBottom: spacing.sm },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  cell: { width: '48%', backgroundColor: colors.gray50, borderRadius: radius.md, padding: spacing.sm },
  val: { fontSize: typography.base, fontWeight: '800', color: colors.gray900 },
  meta: { fontSize: typography.xs, color: colors.gray500 },
  name: { fontSize: typography.base, fontWeight: '700', color: colors.gray900, flex: 1 },
  pill: { fontSize: 11, fontWeight: '700', borderRadius: 999, paddingHorizontal: 8, paddingVertical: 2, overflow: 'hidden' },
  rowBetween: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: spacing.sm },
  item: { borderTopWidth: 1, borderTopColor: colors.gray100, paddingTop: spacing.sm, gap: 2 },
  itemKind: { fontSize: typography.sm, fontWeight: '600', color: colors.gray900 },
  input: { borderWidth: 1, borderColor: colors.gray200, borderRadius: radius.md, padding: spacing.md, backgroundColor: colors.white },
  error: { color: '#dc2626', fontSize: typography.sm },
  ok: { color: '#047857', fontSize: typography.sm },
})
