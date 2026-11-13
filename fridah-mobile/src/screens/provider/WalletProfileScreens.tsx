import React, { useState, useEffect } from 'react'
import { View, Text, ScrollView, TextInput, Alert, StyleSheet, TouchableOpacity } from 'react-native'
import { paymentsApi, authApi, servicesApi } from '@/api/services'
import { Card } from '@/components/common/Cards'
import { Button } from '@/components/common/Button'
import { AppSettingsCard } from '@/components/common/AppSettingsCard'
import { NotificationPreferencesCard } from '@/components/common/NotificationPreferencesCard'
import { getTheme, colors, spacing, typography, radius } from '@/theme'
import { formatKES, formatDate } from '@/utils/formatters'
import { useAuthStore } from '@/stores/authStore'

export const ProviderWalletScreen: React.FC = () => {
  const theme = getTheme('service_provider')
  const [balance, setBalance] = useState(0)
  const [transactions, setTransactions] = useState<any[]>([])
  const [amount, setAmount] = useState('')
  const [phone, setPhone] = useState('+254')
  const [withdrawing, setWithdrawing] = useState(false)

  useEffect(() => {
    paymentsApi.wallet().then(({ data }) => { setBalance(data.data.balance); setTransactions(data.data.recent_transactions || []) }).catch(() => setBalance(45000))
  }, [])

  const withdraw = async () => {
    const amt = parseFloat(amount)
    if (!amt || amt <= 0) { Alert.alert('Error', 'Enter a valid amount'); return }
    if (amt > balance) { Alert.alert('Error', 'Insufficient balance'); return }
    setWithdrawing(true)
    try { await paymentsApi.requestPayout(amt, phone); Alert.alert('Success', 'Payout initiated! Check your M-Pesa shortly.'); setAmount('') }
    catch (e: any) { Alert.alert('Error', e?.response?.data?.error?.message || 'Failed') }
    finally { setWithdrawing(false) }
  }

  return (
    <ScrollView style={{ flex: 1, backgroundColor: colors.gray50 }} contentContainerStyle={{ padding: spacing.lg, gap: 14 }}>
      <View style={[styles.balCard, { backgroundColor: theme.primary }]}>
        <Text style={styles.balLabel}>Available Balance</Text>
        <Text style={styles.balAmount}>{formatKES(balance)}</Text>
        <Text style={styles.balSub}>Your earnings after platform commission</Text>
      </View>
      <Card style={{ padding: spacing.lg }}>
        <Text style={styles.sectionTitle}>Withdraw to M-Pesa</Text>
        <Text style={styles.label}>Amount (KES)</Text>
        <TextInput style={styles.input} value={amount} onChangeText={setAmount} keyboardType="numeric" placeholder="Enter amount" placeholderTextColor={colors.gray400} />
        <Text style={styles.label}>M-Pesa Number</Text>
        <TextInput style={styles.input} value={phone} onChangeText={setPhone} keyboardType="phone-pad" placeholderTextColor={colors.gray400} />
        <Button label={`Withdraw ${amount ? formatKES(parseFloat(amount) || 0) : ''}`} onPress={withdraw} loading={withdrawing} color={theme.primary} fullWidth />
      </Card>
      {transactions.length > 0 && (
        <Card style={{ padding: spacing.lg }}>
          <Text style={styles.sectionTitle}>Recent Transactions</Text>
          {transactions.map(tx => (
            <View key={tx.id} style={styles.txRow}>
              <View style={[styles.txDot, { backgroundColor: tx.entry_type === 'credit' ? '#dcfce7' : '#fee2e2' }]}>
                <Text style={{ fontWeight: '800', color: tx.entry_type === 'credit' ? '#16a34a' : '#dc2626' }}>{tx.entry_type === 'credit' ? '+' : '−'}</Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={{ fontSize: typography.xs, color: colors.gray700, fontWeight: '500' }}>{tx.description}</Text>
                <Text style={{ fontSize: typography.xs, color: colors.gray400 }}>{formatDate(tx.created_at)}</Text>
              </View>
              <Text style={{ fontWeight: '700', fontSize: typography.sm, color: tx.entry_type === 'credit' ? '#16a34a' : '#dc2626' }}>{formatKES(tx.amount)}</Text>
            </View>
          ))}
        </Card>
      )}
    </ScrollView>
  )
}

export const ProviderProfileScreen: React.FC = () => {
  const theme = getTheme('service_provider')
  const { user, fetchMe, logout } = useAuthStore()
  const [form, setForm] = useState({ first_name: '', last_name: '', county: '', town: '' })
  const [providerForm, setProviderForm] = useState({ bio: '', years_experience: 0, is_available: true })
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const initials = ((user?.first_name?.[0] || '') + (user?.last_name?.[0] || '')).toUpperCase() || '?'

  useEffect(() => {
    if (user) setForm({ first_name: user.first_name || '', last_name: user.last_name || '', county: user.county || '', town: user.town || '' })
    servicesApi.providerProfile().then(({ data }) => setProviderForm({ bio: data.data.bio || '', years_experience: data.data.years_experience || 0, is_available: data.data.is_available !== false })).catch(() => {})
  }, [user])

  const saveProfile = async () => {
    setSaving(true)
    try {
      await authApi.updateProfile(form)
      await servicesApi.updateProviderProfile(providerForm as any)
      await fetchMe()
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch { Alert.alert('Error', 'Failed to save.') }
    finally { setSaving(false) }
  }

  return (
    <ScrollView style={{ flex: 1, backgroundColor: colors.gray50 }} contentContainerStyle={{ padding: spacing.lg, gap: 14, paddingBottom: 40 }}>
      <View style={styles.avatarSection}>
        <View style={[styles.avatar, { backgroundColor: theme.primary }]}>
          <Text style={styles.avatarText}>{initials}</Text>
        </View>
        <Text style={styles.name}>{user?.first_name} {user?.last_name}</Text>
        <Text style={styles.email}>{user?.email}</Text>
        <View style={[styles.rolePill, { backgroundColor: theme.primaryLight }]}>
          <Text style={[styles.roleLabel, { color: theme.primary }]}>🔧 Service Provider</Text>
        </View>
      </View>
      <Card style={{ padding: spacing.lg }}>
        <Text style={styles.sectionTitle}>Personal Info</Text>
        <View style={{ flexDirection: 'row', gap: 10 }}>
          <View style={{ flex: 1 }}>
            <Text style={styles.label}>First name</Text>
            <TextInput style={styles.input} value={form.first_name} onChangeText={v => setForm(f => ({ ...f, first_name: v }))} placeholderTextColor={colors.gray400} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.label}>Last name</Text>
            <TextInput style={styles.input} value={form.last_name} onChangeText={v => setForm(f => ({ ...f, last_name: v }))} placeholderTextColor={colors.gray400} />
          </View>
        </View>
        <Text style={styles.label}>Bio</Text>
        <TextInput style={[styles.input, { height: 72 }]} value={providerForm.bio} onChangeText={v => setProviderForm(f => ({ ...f, bio: v }))} multiline placeholder="Describe your skills and experience…" placeholderTextColor={colors.gray400} textAlignVertical="top" />
        <Text style={styles.label}>Years of Experience</Text>
        <TextInput style={styles.input} value={String(providerForm.years_experience)} onChangeText={v => setProviderForm(f => ({ ...f, years_experience: parseInt(v) || 0 }))} keyboardType="numeric" placeholderTextColor={colors.gray400} />
        <TouchableOpacity style={styles.availRow} onPress={() => setProviderForm(f => ({ ...f, is_available: !f.is_available }))}>
          <View style={[styles.toggle, { backgroundColor: providerForm.is_available ? theme.primary : colors.gray300 }]}>
            <View style={[styles.toggleKnob, { transform: [{ translateX: providerForm.is_available ? 18 : 2 }] }]} />
          </View>
          <Text style={styles.availLabel}>Available for work</Text>
        </TouchableOpacity>
        <Button label={saved ? '✓ Saved!' : 'Save Profile'} onPress={saveProfile} loading={saving} color={saved ? '#16a34a' : theme.primary} fullWidth style={{ marginTop: 8 }} />
      </Card>
      <NotificationPreferencesCard accentColor={theme.primary} />
      <AppSettingsCard accentColor={theme.primary} />
      <TouchableOpacity style={styles.logoutBtn} onPress={logout}>
        <Text style={styles.logoutText}>Sign Out</Text>
      </TouchableOpacity>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  balCard: { borderRadius: radius.xl, padding: spacing.xl },
  balLabel: { color: 'rgba(255,255,255,0.7)', fontSize: typography.sm, fontWeight: '500' },
  balAmount: { color: colors.white, fontSize: 36, fontWeight: '900', marginTop: 4 },
  balSub: { color: 'rgba(255,255,255,0.5)', fontSize: typography.xs, marginTop: 4 },
  sectionTitle: { fontSize: typography.base, fontWeight: '700', color: colors.gray900, marginBottom: 14 },
  label: { fontSize: typography.xs, fontWeight: '600', color: colors.gray600, marginBottom: 6 },
  input: { borderWidth: 1.5, borderColor: colors.gray200, borderRadius: radius.md, paddingHorizontal: 14, paddingVertical: 11, fontSize: typography.sm, color: colors.gray900, marginBottom: 14 },
  txRow: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: colors.gray50 },
  txDot: { width: 36, height: 36, borderRadius: 18, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  avatarSection: { alignItems: 'center', paddingVertical: spacing.xl },
  avatar: { width: 72, height: 72, borderRadius: 22, alignItems: 'center', justifyContent: 'center', marginBottom: 12 },
  avatarText: { color: colors.white, fontSize: 28, fontWeight: '800' },
  name: { fontSize: typography.xl, fontWeight: '800', color: colors.gray900 },
  email: { fontSize: typography.sm, color: colors.gray500, marginTop: 2 },
  rolePill: { paddingHorizontal: 16, paddingVertical: 6, borderRadius: radius.full, marginTop: 10 },
  roleLabel: { fontSize: typography.sm, fontWeight: '600' },
  availRow: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 14 },
  toggle: { width: 44, height: 26, borderRadius: 13, padding: 2, justifyContent: 'center' },
  toggleKnob: { width: 22, height: 22, borderRadius: 11, backgroundColor: colors.white, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.2, shadowRadius: 2, elevation: 2 },
  availLabel: { fontSize: typography.sm, fontWeight: '500', color: colors.gray700 },
  logoutBtn: { padding: spacing.lg, alignItems: 'center', backgroundColor: colors.white, borderRadius: radius.xl, borderWidth: 1.5, borderColor: '#fecaca' },
  logoutText: { color: colors.red500, fontWeight: '700', fontSize: typography.base },
})
