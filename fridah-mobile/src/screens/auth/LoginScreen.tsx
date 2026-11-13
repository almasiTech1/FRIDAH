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

const roleRoute: Record<Role, string> = {
  tenant: 'TenantTabs',
  landlord: 'LandlordTabs',
  admin: 'AdminTabs',
  service_provider: 'ProviderTabs',
  hotel_owner: 'HotelTabs',
}

export const LoginScreen: React.FC = () => {
  const nav = useNavigation<any>()
  const { login, loading } = useAuthStore()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const handleLogin = async () => {
    if (!email || !password) { Alert.alert('Error', 'Please fill in all fields.'); return }
    try {
      const user = await login(email, password)
      // Accounts on an admin-issued temporary password are taken to the change-password screen by the root navigator.
      if (user.must_change_password) return
      nav.reset({ index: 0, routes: [{ name: roleRoute[user.role] }] })
    } catch (e: any) {
      Alert.alert('Login Failed', e?.response?.data?.error?.message || 'Invalid credentials.')
    }
  }

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView style={styles.bg} contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        {/* Logo */}
        <View style={styles.logoWrap}>
          <View style={styles.logo}><Text style={styles.logoText}>F</Text></View>
          <Text style={styles.appName}>FRIDAH</Text>
          <Text style={styles.tagline}>Kenya's Property Super App</Text>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Welcome back</Text>
          <Text style={styles.cardSub}>Sign in to your account</Text>

          <Input
            label="Email address"
            value={email}
            onChangeText={setEmail}
            keyboardType="email-address"
            autoCapitalize="none"
            placeholder="you@example.com"
            containerStyle={{ marginTop: 20 }}
          />
          <Input
            label="Password"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            placeholder="••••••••"
          />

          <Button
            label="Sign In"
            onPress={handleLogin}
            loading={loading}
            color={colors.gray900}
            fullWidth
            style={{ marginTop: 8 }}
          />

          <View style={styles.footer}>
            <Text style={styles.footerText}>Don't have an account? </Text>
            <TouchableOpacity onPress={() => nav.navigate('Register')}>
              <Text style={[styles.footerLink, { color: colors.gray900 }]}>Register</Text>
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  bg: { flex: 1, backgroundColor: colors.gray50 },
  container: { flexGrow: 1, justifyContent: 'center', padding: spacing.xl },
  logoWrap: { alignItems: 'center', marginBottom: spacing.xxxl },
  logo: {
    width: 64, height: 64, borderRadius: 18,
    backgroundColor: colors.gray900,
    alignItems: 'center', justifyContent: 'center', marginBottom: 12,
  },
  logoText: { color: colors.white, fontSize: 28, fontWeight: '800' },
  appName: { fontSize: typography.xxl, fontWeight: '800', color: colors.gray900 },
  tagline: { fontSize: typography.sm, color: colors.gray500, marginTop: 4 },
  card: {
    backgroundColor: colors.white, borderRadius: radius.xl,
    padding: spacing.xl, borderWidth: 1, borderColor: colors.gray100,
  },
  cardTitle: { fontSize: typography.xxl, fontWeight: '700', color: colors.gray900 },
  cardSub: { fontSize: typography.sm, color: colors.gray500, marginTop: 4 },
  footer: { flexDirection: 'row', justifyContent: 'center', marginTop: spacing.lg },
  footerText: { fontSize: typography.sm, color: colors.gray500 },
  footerLink: { fontSize: typography.sm, fontWeight: '600' },
})
