import React, { useState, useEffect } from 'react'
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet,
  Alert, TextInput,
} from 'react-native'
import { useAuthStore } from '@/stores/authStore'
import { authApi } from '@/api/services'
import { Button } from '@/components/common/Button'
import { useNavigation } from '@react-navigation/native'
import { Card } from '@/components/common/Cards'
import { KYCSubmissionCard } from '@/components/common/KYCSubmissionCard'
import { AppSettingsCard } from '@/components/common/AppSettingsCard'
import { NotificationPreferencesCard } from '@/components/common/NotificationPreferencesCard'
import { getTheme, colors, spacing, typography, radius } from '@/theme'

export const TenantProfileScreen: React.FC = () => {
  const theme = getTheme('tenant')
  const navigation = useNavigation<any>()
  const { user, fetchMe, logout } = useAuthStore()
  const [form, setForm] = useState({ first_name: '', last_name: '', county: '', town: '' })
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const set = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }))

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
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Avatar */}
      <View style={styles.avatarSection}>
        <View style={[styles.avatar, { backgroundColor: theme.primary }]}>
          <Text style={styles.avatarText}>{initials}</Text>
        </View>
        <Text style={styles.name}>{user?.first_name} {user?.last_name}</Text>
        <Text style={styles.email}>{user?.email}</Text>
        <Text style={styles.phone}>{user?.phone_number}</Text>
        <View style={[styles.rolePill, { backgroundColor: theme.primaryLight }]}>
          <Text style={[styles.roleText, { color: theme.primary }]}>🏠 Tenant</Text>
        </View>
      </View>

      {/* KYC status + submission */}
      <KYCSubmissionCard accentColor={theme.primary} />

      {/* Profile form */}
      <Card style={styles.card}>
        <Text style={styles.sectionTitle}>Personal Information</Text>
        <View style={styles.row}>
          <View style={{ flex: 1, marginRight: 8 }}>
            <Text style={styles.label}>First name</Text>
            <TextInput style={styles.input} value={form.first_name} onChangeText={v => set('first_name', v)} placeholderTextColor={colors.gray400} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.label}>Last name</Text>
            <TextInput style={styles.input} value={form.last_name} onChangeText={v => set('last_name', v)} placeholderTextColor={colors.gray400} />
          </View>
        </View>
        <Text style={styles.label}>County</Text>
        <TextInput style={styles.input} value={form.county} onChangeText={v => set('county', v)} placeholder="e.g. Nairobi" placeholderTextColor={colors.gray400} />
        <Text style={styles.label}>Town</Text>
        <TextInput style={styles.input} value={form.town} onChangeText={v => set('town', v)} placeholder="e.g. Westlands" placeholderTextColor={colors.gray400} />
        <Button label={saved ? '✓ Saved!' : 'Save Changes'} onPress={save} loading={saving} color={saved ? '#16a34a' : theme.primary} fullWidth style={{ marginTop: 8 }} />
      </Card>

      {/* App settings */}
      <Button label="My refunds" variant="outline" color={theme.primary} onPress={() => navigation.navigate('TenantRefunds')} />
      <NotificationPreferencesCard accentColor={theme.primary} />
      <AppSettingsCard accentColor={theme.primary} />


      {/* Logout */}
      <TouchableOpacity style={styles.logoutBtn} onPress={doLogout}>
        <Text style={styles.logoutText}>Sign Out</Text>
      </TouchableOpacity>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.gray50 },
  content: { padding: spacing.lg, gap: 16, paddingBottom: 40 },
  avatarSection: { alignItems: 'center', paddingVertical: spacing.xl },
  avatar: { width: 72, height: 72, borderRadius: 22, alignItems: 'center', justifyContent: 'center', marginBottom: 12 },
  avatarText: { color: colors.white, fontSize: 28, fontWeight: '800' },
  name: { fontSize: typography.xl, fontWeight: '800', color: colors.gray900 },
  email: { fontSize: typography.sm, color: colors.gray500, marginTop: 2 },
  phone: { fontSize: typography.sm, color: colors.gray500, marginTop: 2 },
  rolePill: { paddingHorizontal: 16, paddingVertical: 6, borderRadius: radius.full, marginTop: 10 },
  roleText: { fontSize: typography.sm, fontWeight: '600' },
  kycBanner: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: spacing.md, borderRadius: radius.xl, borderWidth: 1.5 },
  kycIcon: { fontSize: 24 },
  kycTitle: { fontSize: typography.sm, fontWeight: '700' },
  kycSub: { fontSize: typography.xs, marginTop: 2 },
  card: { padding: spacing.lg },
  sectionTitle: { fontSize: typography.base, fontWeight: '700', color: colors.gray900, marginBottom: 16 },
  row: { flexDirection: 'row' },
  label: { fontSize: typography.xs, fontWeight: '600', color: colors.gray600, marginBottom: 6 },
  input: { borderWidth: 1.5, borderColor: colors.gray200, borderRadius: radius.md, paddingHorizontal: 14, paddingVertical: 11, fontSize: typography.sm, color: colors.gray900, backgroundColor: colors.white, marginBottom: 14 },
  logoutBtn: { padding: spacing.lg, alignItems: 'center', backgroundColor: colors.white, borderRadius: radius.xl, borderWidth: 1.5, borderColor: '#fecaca' },
  logoutText: { color: colors.red500, fontWeight: '700', fontSize: typography.base },
})
