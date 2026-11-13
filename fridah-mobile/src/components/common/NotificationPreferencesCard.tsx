import React, { useEffect, useState } from 'react'
import { View, Text, Switch, TextInput, StyleSheet } from 'react-native'
import { notificationsApi } from '@/api/services'
import { Card, Skeleton } from '@/components/common/Cards'
import { Button } from '@/components/common/Button'
import { colors, spacing, typography, radius } from '@/theme'

const TOGGLES: { key: string; label: string }[] = [
  { key: 'sms_enabled', label: 'SMS messages' },
  { key: 'push_enabled', label: 'Push notifications' },
  { key: 'email_enabled', label: 'Email' },
  { key: 'payment_alerts', label: 'Rent & payment reminders (SMS/push)' },
  { key: 'maintenance_alerts', label: 'Maintenance updates' },
]
const HHMM = /^([01]\d|2[0-3]):[0-5]\d$/
const hhmm = (v?: string | null) => (v ? v.slice(0, 5) : '')

/** Channel toggles plus quiet hours. Payment reminders are held back during quiet hours. */
export const NotificationPreferencesCard: React.FC<{ accentColor: string }> = ({ accentColor }) => {
  const [prefs, setPrefs] = useState<Record<string, any>>({})
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    (async () => {
      try {
        const { data } = await notificationsApi.preferences()
        const d: any = (data as any).data || data
        setPrefs(d); setStart(hhmm(d.quiet_hours_start)); setEnd(hhmm(d.quiet_hours_end))
      } catch { setError('Could not load your notification preferences.') } finally { setLoading(false) }
    })()
  }, [])

  const save = async () => {
    setError(''); setSaved(false)
    if (!!start !== !!end) { setError('Set both quiet-hours times, or leave both empty.'); return }
    if ((start && !HHMM.test(start)) || (end && !HHMM.test(end))) { setError('Use 24-hour times like 21:00.'); return }
    setSaving(true)
    try {
      await notificationsApi.updatePreferences({
        ...Object.fromEntries(TOGGLES.map((t) => [t.key, !!prefs[t.key]])),
        quiet_hours_start: start || null, quiet_hours_end: end || null,
      })
      setSaved(true)
    } catch { setError('Could not save your preferences.') } finally { setSaving(false) }
  }

  if (loading) return <Skeleton height={120} />

  return (
    <Card>
      <Text style={styles.title}>Notifications</Text>
      <Text style={styles.help}>Payment reminders are held back during your quiet hours.</Text>
      {TOGGLES.map((t) => (
        <View key={t.key} style={styles.row}>
          <Text style={styles.label}>{t.label}</Text>
          <Switch value={!!prefs[t.key]} onValueChange={(v) => setPrefs((p) => ({ ...p, [t.key]: v }))}
                  trackColor={{ true: accentColor }} accessibilityLabel={t.label} />
        </View>
      ))}
      <View style={styles.row}>
        <View style={{ flex: 1 }}>
          <Text style={styles.label}>Quiet hours start</Text>
          <TextInput style={styles.input} value={start} onChangeText={setStart} placeholder="21:00" maxLength={5}
                     keyboardType="numbers-and-punctuation" accessibilityLabel="Quiet hours start" />
        </View>
        <View style={{ width: spacing.md }} />
        <View style={{ flex: 1 }}>
          <Text style={styles.label}>Quiet hours end</Text>
          <TextInput style={styles.input} value={end} onChangeText={setEnd} placeholder="07:00" maxLength={5}
                     keyboardType="numbers-and-punctuation" accessibilityLabel="Quiet hours end" />
        </View>
      </View>
      <Text style={styles.help}>Leave both empty to use the default (21:00 – 07:00).</Text>
      {error ? <Text style={styles.error} accessibilityRole="alert">{error}</Text> : null}
      {saved ? <Text style={styles.ok} accessibilityRole="alert">Saved</Text> : null}
      <Button label="Save preferences" color={accentColor} loading={saving} onPress={save} />
    </Card>
  )
}

const styles = StyleSheet.create({
  title: { fontSize: typography.base, fontWeight: '700', color: colors.gray900 },
  help: { fontSize: typography.xs, color: colors.gray500, marginBottom: spacing.sm },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: spacing.xs },
  label: { fontSize: typography.sm, color: colors.gray700, flexShrink: 1 },
  input: { borderWidth: 1, borderColor: colors.gray200, borderRadius: radius.md, padding: spacing.sm, marginTop: 4, backgroundColor: colors.white },
  error: { color: '#dc2626', fontSize: typography.sm, marginVertical: spacing.sm },
  ok: { color: '#047857', fontSize: typography.sm, marginVertical: spacing.sm },
})
