import React, { useCallback, useEffect, useState } from 'react'
import { View, Text, FlatList, TextInput, StyleSheet, RefreshControl, Alert, Platform } from 'react-native'
import { agencyApi } from '@/api/services'
import { Card, StatusBadge, EmptyState, Skeleton, FadeIn } from '@/components/common/Cards'
import { Button } from '@/components/common/Button'
import { colors, spacing, typography, radius, getTheme } from '@/theme'

const blank = { admin_first_name: '', admin_last_name: '', admin_email: '', admin_phone_number: '', name: '', email: '', phone_number: '', county: '', town: '' }

/** Administrators register and manage agency companies. Nobody else can create one. */
export const AdminAgenciesScreen: React.FC = () => {
  const theme = getTheme('admin')
  const [agencies, setAgencies] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(blank)
  const [saving, setSaving] = useState(false)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [credentials, setCredentials] = useState<{ agency: string; login_email: string; temporary_password: string } | null>(null)
  const set = (k: keyof typeof blank, v: string) => setForm((f) => ({ ...f, [k]: v }))

  const load = useCallback(async () => {
    try {
      const { data } = await agencyApi.list()
      setAgencies((data as any).results || (data as any).data?.results || (data as any).data || [])
    } catch { setAgencies([]) } finally { setLoading(false); setRefreshing(false) }
  }, [])
  useEffect(() => { load() }, [load])

  const register = async () => {
    if (!form.name.trim() || !form.admin_email.trim() || !form.admin_first_name.trim() || !form.admin_last_name.trim() || !form.admin_phone_number.trim()) {
      setError('Agency name and the agency admin\'s first name, last name, email and phone are required.'); return
    }
    setSaving(true); setError('')
    try {
      const res: any = await agencyApi.create({ ...form, default_fee_percent: 5 })
      const c = res?.data?.data?.credentials
      if (c) setCredentials({ agency: form.name, login_email: c.login_email, temporary_password: c.temporary_password })
      setForm(blank); setShowForm(false); await load()
    } catch (e: any) {
      const d = e?.response?.data
      setError(d?.error?.message || (d && typeof d === 'object' ? Object.values(d).flat().join(' ') : '') || 'Could not register the agency.')
    } finally { setSaving(false) }
  }

  const resetLogin = (a: any) => {
    Alert.alert('Reset login', `Issue a new temporary password to the Agency Admin of ${a.name}? Their current password stops working.`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Reset', style: 'destructive', onPress: async () => {
        setBusy(a.id)
        try {
          const res: any = await agencyApi.resetAdminPassword(a.id)
          const c = res?.data?.data
          setCredentials({ agency: a.name, login_email: c.login_email, temporary_password: c.temporary_password })
        } catch { Alert.alert('Failed', 'Could not reset the login.') } finally { setBusy(null) }
      } },
    ])
  }

  const change = (a: any, status: 'active' | 'suspended') => {
    const run = async () => {
      setBusy(a.id)
      try { await agencyApi.setStatus(a.id, status); await load() }
      catch { Alert.alert('Failed', 'Could not change the agency status.') } finally { setBusy(null) }
    }
    if (status === 'suspended') {
      Alert.alert('Suspend agency', `Suspend ${a.name}? It will disappear from the agency directory.`, [
        { text: 'Cancel', style: 'cancel' }, { text: 'Suspend', style: 'destructive', onPress: run },
      ])
    } else run()
  }

  if (loading) return <View style={{ padding: spacing.lg, gap: spacing.md }}><Skeleton height={80} /><Skeleton height={80} /></View>

  return (
    <FlatList
      style={{ backgroundColor: colors.gray50 }}
      data={agencies}
      keyExtractor={(a) => a.id}
      contentContainerStyle={{ padding: spacing.lg, gap: spacing.md, flexGrow: 1 }}
      keyboardShouldPersistTaps="handled"
      refreshControl={<RefreshControl refreshing={refreshing} tintColor={theme.primary} onRefresh={() => { setRefreshing(true); load() }} />}
      ListHeaderComponent={
        <View style={{ gap: spacing.md }}>
          <Text style={styles.note}>Only administrators can register an agency company.</Text>
          {credentials && (
            <Card>
              <Text style={styles.credTitle}>Login for {credentials.agency} - copy it now</Text>
              <Text style={styles.help}>Shown only once and cannot be retrieved later. Give it to the agency admin securely; they must change it at first login. If it is lost, use Reset login.</Text>
              <Text selectable style={styles.cred}>Email: {credentials.login_email}</Text>
              <Text selectable style={[styles.cred, { fontWeight: '800' }]}>Temporary password: {credentials.temporary_password}</Text>
              <Button label="I have saved it - dismiss" size="sm" variant="outline" color={colors.gray600} onPress={() => setCredentials(null)} />
            </Card>
          )}
          <Button label={showForm ? 'Close' : '+ Register agency'} color={theme.primary} onPress={() => { setShowForm(!showForm); setError('') }} />
          {showForm && (
            <Card>
              <Text style={styles.label}>Agency admin - you create their login</Text>
              <Text style={styles.help}>They become the first Agency Admin and invite their own team. Nobody registers an agency themselves: you hand over a temporary password that they must change at first login.</Text>
              <TextInput style={styles.input} placeholder="First name *" value={form.admin_first_name} onChangeText={(v) => set('admin_first_name', v)} accessibilityLabel="Agency admin first name" />
              <TextInput style={styles.input} placeholder="Last name *" value={form.admin_last_name} onChangeText={(v) => set('admin_last_name', v)} accessibilityLabel="Agency admin last name" />
              <TextInput style={styles.input} value={form.admin_email} onChangeText={(v) => set('admin_email', v)}
                         autoCapitalize="none" keyboardType="email-address" placeholder="Login email *" accessibilityLabel="Agency admin email" />
              <TextInput style={styles.input} placeholder="Phone (+2547XXXXXXXX) *" value={form.admin_phone_number} onChangeText={(v) => set('admin_phone_number', v)} keyboardType="phone-pad" accessibilityLabel="Agency admin phone" />
              <TextInput style={styles.input} placeholder="Agency name *" value={form.name} onChangeText={(v) => set('name', v)} accessibilityLabel="Agency name" />
              <TextInput style={styles.input} placeholder="Agency email" value={form.email} onChangeText={(v) => set('email', v)} autoCapitalize="none" keyboardType="email-address" />
              <TextInput style={styles.input} placeholder="Phone (+2547XXXXXXXX)" value={form.phone_number} onChangeText={(v) => set('phone_number', v)} keyboardType="phone-pad" />
              <TextInput style={styles.input} placeholder="County" value={form.county} onChangeText={(v) => set('county', v)} />
              <TextInput style={styles.input} placeholder="Town" value={form.town} onChangeText={(v) => set('town', v)} />
              {error ? <Text style={styles.error} accessibilityRole="alert">{error}</Text> : null}
              <Button label="Register agency" color={theme.primary} loading={saving} onPress={register} />
            </Card>
          )}
        </View>
      }
      ListEmptyComponent={<EmptyState emoji="🏢" message="No agencies registered yet." />}
      renderItem={({ item: a, index }) => (
        <FadeIn index={index}>
          <Card>
            <View style={styles.rowBetween}>
              <Text style={styles.name}>{a.name}</Text>
              <StatusBadge status={a.status} />
            </View>
            <Text style={styles.meta}>{[a.town, a.county].filter(Boolean).join(', ') || '—'} · {a.managed_properties_count ?? 0} properties</Text>
            <View style={{ marginTop: spacing.md, flexDirection: 'row', gap: spacing.sm }}>
              <Button label="Reset login" size="sm" variant="outline" color={colors.gray600} disabled={busy === a.id} onPress={() => resetLogin(a)} />
              {a.status !== 'active'
                ? <Button label="Activate" size="sm" variant="outline" color="#059669" disabled={busy === a.id} onPress={() => change(a, 'active')} />
                : <Button label="Suspend" size="sm" variant="outline" color="#dc2626" disabled={busy === a.id} onPress={() => change(a, 'suspended')} />}
            </View>
          </Card>
        </FadeIn>
      )}
    />
  )
}

const styles = StyleSheet.create({
  credTitle: { fontSize: typography.base, fontWeight: '700', color: '#92400e', marginBottom: 4 },
  cred: { fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace', fontSize: typography.sm, color: colors.gray900, marginBottom: 4 },
  note: { fontSize: typography.sm, color: colors.gray500 },
  label: { fontSize: typography.sm, fontWeight: '600', color: colors.gray700, marginBottom: 4 },
  help: { fontSize: typography.xs, color: colors.gray500, marginBottom: spacing.sm },
  input: { borderWidth: 1, borderColor: colors.gray200, borderRadius: radius.md, padding: spacing.md, marginBottom: spacing.sm, backgroundColor: colors.white },
  error: { color: '#dc2626', fontSize: typography.sm, marginBottom: spacing.sm },
  rowBetween: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: spacing.sm },
  name: { fontSize: typography.base, fontWeight: '700', color: colors.gray900, flex: 1 },
  meta: { fontSize: typography.xs, color: colors.gray500, marginTop: 2 },
})
