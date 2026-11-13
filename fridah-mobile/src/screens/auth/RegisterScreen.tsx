import React, { useState } from 'react'
import {
  View, Text, ScrollView, TouchableOpacity,
  StyleSheet, KeyboardAvoidingView, Platform, Alert,
} from 'react-native'
import { useNavigation } from '@react-navigation/native'
import { useAuthStore } from '@/stores/authStore'
import { Input } from '@/components/common/Input'
import { Button } from '@/components/common/Button'
import { colors, typography, spacing, radius } from '@/theme'
import type { Role } from '@/types'

const roles: { value: Role; label: string; emoji: string }[] = [
  { value: 'tenant', label: 'Tenant', emoji: '🏠' },
  { value: 'landlord', label: 'Landlord', emoji: '🏗️' },
  { value: 'service_provider', label: 'Service Provider', emoji: '🔧' },
  { value: 'hotel_owner', label: 'Hotel / BnB Owner', emoji: '🏨' },
]

const roleRoute: Record<Role, string> = {
  tenant: 'TenantTabs', landlord: 'LandlordTabs',
  admin: 'AdminTabs', service_provider: 'ProviderTabs', hotel_owner: 'HotelTabs',
}

export const RegisterScreen: React.FC = () => {
  const nav = useNavigation<any>()
  const { register, loading } = useAuthStore()
  const [form, setForm] = useState({
    first_name: '', last_name: '', username: '',
    email: '', phone_number: '+254', password: '',
    password_confirm: '', role: 'tenant' as Role,
    service_category: '',
  })

  const set = (key: string, val: string) => setForm(f => ({ ...f, [key]: val }))

  const handleRegister = async () => {
    if (!form.email || !form.password || !form.phone_number || !form.username) {
      Alert.alert('Error', 'Please fill in all required fields.'); return
    }
    if (form.password !== form.password_confirm) {
      Alert.alert('Error', 'Passwords do not match.'); return
    }
    try {
      const user = await register(form)
      nav.reset({ index: 0, routes: [{ name: roleRoute[user.role] }] })
    } catch (e: any) {
      const errs = e?.response?.data?.error?.details
      const msg = errs ? Object.values(errs).flat().join('\n') : e?.response?.data?.error?.message || 'Registration failed.'
      Alert.alert('Error', msg)
    }
  }

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView style={styles.bg} contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <View style={styles.header}>
          <TouchableOpacity onPress={() => nav.goBack()} style={styles.back}>
            <Text style={styles.backText}>← Back</Text>
          </TouchableOpacity>
          <Text style={styles.title}>Create Account</Text>
          <Text style={styles.sub}>Join FRIDAH today</Text>
        </View>

        <View style={styles.card}>
          {/* Role selector */}
          <Text style={styles.roleLabel}>I am a…</Text>
          <View style={styles.roleGrid}>
            {roles.map(r => (
              <TouchableOpacity
                key={r.value}
                style={[styles.roleBtn, form.role === r.value && styles.roleBtnActive]}
                onPress={() => set('role', r.value)}
              >
                <Text style={styles.roleEmoji}>{r.emoji}</Text>
                <Text style={[styles.roleName, form.role === r.value && { color: colors.gray900, fontWeight: '600' }]}>
                  {r.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          <View style={styles.row}>
            <View style={{ flex: 1, marginRight: 8 }}>
              <Input label="First name" value={form.first_name} onChangeText={v => set('first_name', v)} placeholder="John" />
            </View>
            <View style={{ flex: 1 }}>
              <Input label="Last name" value={form.last_name} onChangeText={v => set('last_name', v)} placeholder="Doe" />
            </View>
          </View>
          <Input label="Username" value={form.username} onChangeText={v => set('username', v)} placeholder="johndoe" autoCapitalize="none" />
          <Input label="Email" value={form.email} onChangeText={v => set('email', v)} keyboardType="email-address" autoCapitalize="none" placeholder="you@example.com" />
          <Input label="Safaricom Phone (+254…)" value={form.phone_number} onChangeText={v => set('phone_number', v)} keyboardType="phone-pad" placeholder="+254712345678" />
          {form.role === 'service_provider' && (
            <Input label="Service Category" value={form.service_category} onChangeText={v => set('service_category', v)} placeholder="e.g. Plumber, Electrician" />
          )}
          <Input label="Password" value={form.password} onChangeText={v => set('password', v)} secureTextEntry placeholder="••••••••" />
          <Input label="Confirm Password" value={form.password_confirm} onChangeText={v => set('password_confirm', v)} secureTextEntry placeholder="••••••••" />

          <Button label="Create Account" onPress={handleRegister} loading={loading} color={colors.gray900} fullWidth style={{ marginTop: 8 }} />

          <View style={styles.footer}>
            <Text style={styles.footerText}>Already have an account? </Text>
            <TouchableOpacity onPress={() => nav.navigate('Login')}>
              <Text style={[styles.footerLink, { color: colors.gray900 }]}>Sign In</Text>
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  bg: { flex: 1, backgroundColor: colors.gray50 },
  container: { flexGrow: 1, padding: spacing.xl, paddingTop: 60 },
  header: { marginBottom: spacing.xl },
  back: { marginBottom: 16 },
  backText: { fontSize: typography.base, color: colors.gray500 },
  title: { fontSize: typography.xxl, fontWeight: '800', color: colors.gray900 },
  sub: { fontSize: typography.sm, color: colors.gray500, marginTop: 4 },
  card: {
    backgroundColor: colors.white, borderRadius: radius.xl,
    padding: spacing.xl, borderWidth: 1, borderColor: colors.gray100,
  },
  roleLabel: { fontSize: typography.sm, fontWeight: '500', color: colors.gray700, marginBottom: 10 },
  roleGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: spacing.lg },
  roleBtn: {
    paddingHorizontal: 12, paddingVertical: 8, borderRadius: radius.md,
    borderWidth: 1.5, borderColor: colors.gray200, alignItems: 'center', flexDirection: 'row', gap: 6,
  },
  roleBtnActive: { borderColor: colors.gray900, backgroundColor: colors.gray50 },
  roleEmoji: { fontSize: 16 },
  roleName: { fontSize: typography.sm, color: colors.gray500 },
  row: { flexDirection: 'row' },
  footer: { flexDirection: 'row', justifyContent: 'center', marginTop: spacing.lg },
  footerText: { fontSize: typography.sm, color: colors.gray500 },
  footerLink: { fontSize: typography.sm, fontWeight: '600' },
})
