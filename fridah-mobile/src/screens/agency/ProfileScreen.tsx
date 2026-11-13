import React, { useState, useEffect } from 'react'
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, Alert, TextInput } from 'react-native'
import { useAuthStore } from '@/stores/authStore'
import { authApi } from '@/api/services'
import { Button } from '@/components/common/Button'
import { Card, StatusBadge } from '@/components/common/Cards'
import { KYCSubmissionCard } from '@/components/common/KYCSubmissionCard'
import { NotificationPreferencesCard } from '@/components/common/NotificationPreferencesCard'
import { agencyTheme, colors, spacing, typography, radius } from '@/theme'

export const AgencyProfileScreen: React.FC = () => {
  const { user, agencies, fetchMe, logout } = useAuthStore()
  const [form, setForm] = useState({ first_name: '', last_name: '', county: '', town: '' })
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }))

  useEffect(() => {
    if (user) setForm({ first_name: user.first_name || '', last_name: user.last_name || '', county: user.county || '', town: user.town || '' })
  }, [user])

  const initials = ((user?.first_name?.[0] || '') + (user?.last_name?.[0] || '')).toUpperCase() || '?'

  const save = async () => {
    setSaving(true)
    try { await authApi.updateProfile(form); await fetchMe(); setSaved(true); setTimeout(() => setSaved(false), 2500) }
    catch { Alert.alert('Error', 'Failed to save profile.') }
    finally { setSaving(false) }
  }

  const doLogout = () => Alert.alert('Logout', 'Are you sure you want to logout?', [
    { text: 'Cancel', style: 'cancel' },
    { text: 'Logout', style: 'destructive', onPress: logout },
  ])

  return (
    <ScrollView style={{ flex: 1, backgroundColor: colors.gray50 }} contentContainerStyle={styles.content}>
      <View style={styles.avatarSection}>
        <View style={[styles.avatar, { backgroundColor: agencyTheme.primary }]}>
          <Text style={styles.avatarText}>{initials}</Text>
        </View>
        <Text style={styles.name}>{user?.first_name} {user?.last_name}</Text>
        <Text style={styles.email}>{user?.email}</Text>
      </View>

      <View style={{ marginBottom: spacing.md }}>
        <KYCSubmissionCard accentColor={agencyTheme.primary} />
        <NotificationPreferencesCard accentColor={agencyTheme.primary} />
      </View>

      <Card style={{ marginBottom: spacing.md }}>
        <Text style={styles.sectionTitle}>Details</Text>
        <TextInput style={styles.input} placeholder="First name" value={form.first_name} onChangeText={(v) => set('first_name', v)} />
        <TextInput style={styles.input} placeholder="Last name" value={form.last_name} onChangeText={(v) => set('last_name', v)} />
        <TextInput style={styles.input} placeholder="County" value={form.county} onChangeText={(v) => set('county', v)} />
        <TextInput style={styles.input} placeholder="Town" value={form.town} onChangeText={(v) => set('town', v)} />
        <Button label={saved ? '✓ Saved' : 'Save'} onPress={save} loading={saving} color={agencyTheme.primary} fullWidth />
      </Card>

      {agencies.length > 0 && (
        <Card style={{ marginBottom: spacing.md }}>
          <Text style={styles.sectionTitle}>Your Agencies</Text>
          {agencies.map((a) => (
            <View key={a.id} style={styles.agencyRow}>
              <View style={{ flex: 1 }}>
                <Text style={styles.agencyName}>{a.name}</Text>
                <Text style={styles.agencyMeta}>{a.managed_properties_count} properties · {a.owners_count} owners</Text>
              </View>
              <StatusBadge status={a.status} />
            </View>
          ))}
        </Card>
      )}

      <TouchableOpacity onPress={doLogout} style={styles.logoutBtn}>
        <Text style={styles.logoutText}>Log Out</Text>
      </TouchableOpacity>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg },
  avatarSection: { alignItems: 'center', marginBottom: spacing.xl },
  avatar: { width: 76, height: 76, borderRadius: 38, alignItems: 'center', justifyContent: 'center', marginBottom: spacing.sm },
  avatarText: { color: colors.white, fontSize: 28, fontWeight: '700' },
  name: { fontSize: typography.lg, fontWeight: '700', color: colors.gray900 },
  email: { fontSize: typography.sm, color: colors.gray500, marginTop: 2 },
  sectionTitle: { fontSize: typography.base, fontWeight: '700', color: colors.gray900, marginBottom: spacing.sm },
  input: { borderWidth: 1, borderColor: colors.gray200, borderRadius: radius.md, paddingHorizontal: 12, paddingVertical: 10, fontSize: typography.sm, marginBottom: spacing.sm, color: colors.gray900 },
  agencyRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: spacing.sm, borderTopWidth: 1, borderTopColor: colors.gray100 },
  agencyName: { fontSize: typography.sm, fontWeight: '700', color: colors.gray800 },
  agencyMeta: { fontSize: typography.xs, color: colors.gray400, marginTop: 2 },
  logoutBtn: { alignItems: 'center', paddingVertical: spacing.md },
  logoutText: { color: colors.red600, fontWeight: '700', fontSize: typography.sm },
})
