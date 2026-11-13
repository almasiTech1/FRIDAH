import React, { useState } from 'react'
import { View, Text, ScrollView, StyleSheet, KeyboardAvoidingView, Platform, TouchableOpacity } from 'react-native'
import { authApi } from '@/api/services'
import { useAuthStore } from '@/stores/authStore'
import { Input } from '@/components/common/Input'
import { Button } from '@/components/common/Button'
import { colors, typography, spacing, radius } from '@/theme'

/** Shown instead of the app while an admin-issued temporary password is still in force. */
export const ForceChangePasswordScreen: React.FC = () => {
  const { fetchMe, fetchAgencies, logout } = useAuthStore()
  const [oldPw, setOldPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const [confirm, setConfirm] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const submit = async () => {
    setError('')
    if (newPw !== confirm) { setError('The new passwords do not match.'); return }
    setSaving(true)
    try {
      await authApi.changePassword(oldPw, newPw)
      await fetchMe()          // clears must_change_password, so the navigator switches to the app
      await fetchAgencies()    // refused while the temporary password was active
    } catch (e: any) {
      const d = e?.response?.data
      const pick = (v: any) => (Array.isArray(v) ? v.join(' ') : v)
      setError(d?.error?.message || pick(d?.new_password) || pick(d?.old_password) || 'Could not change your password.')
    } finally { setSaving(false) }
  }

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView style={{ flex: 1, backgroundColor: colors.gray50 }} contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <Text style={styles.title}>Set your own password</Text>
        <Text style={styles.sub}>
          You signed in with a temporary password issued by a FRIDAH administrator. Choose a new one to continue.
        </Text>
        <View style={styles.card}>
          <Input label="Temporary password" value={oldPw} onChangeText={setOldPw} secureTextEntry autoCapitalize="none" />
          <Input label="New password" value={newPw} onChangeText={setNewPw} secureTextEntry autoCapitalize="none" />
          <Input label="Confirm new password" value={confirm} onChangeText={setConfirm} secureTextEntry autoCapitalize="none" />
          <Text style={styles.hint}>At least 8 characters; not a common password or similar to your name or email.</Text>
          {error ? <Text style={styles.error} accessibilityRole="alert">{error}</Text> : null}
          <Button label="Save and continue" loading={saving} disabled={!oldPw || !newPw || !confirm} onPress={submit} />
          <TouchableOpacity onPress={() => logout()} accessibilityRole="button" style={{ alignItems: 'center', marginTop: spacing.md }}>
            <Text style={{ color: colors.gray500, fontSize: typography.sm }}>Sign out</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  container: { padding: spacing.xl, paddingTop: spacing.xxl, gap: spacing.md },
  title: { fontSize: typography.xxl, fontWeight: '800', color: colors.gray900 },
  sub: { fontSize: typography.sm, color: colors.gray500, marginBottom: spacing.sm },
  card: { backgroundColor: colors.white, borderRadius: radius.lg, padding: spacing.lg, gap: spacing.sm },
  hint: { fontSize: typography.xs, color: colors.gray400 },
  error: { color: '#dc2626', fontSize: typography.sm },
})
