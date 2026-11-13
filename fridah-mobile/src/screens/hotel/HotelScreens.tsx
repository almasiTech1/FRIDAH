import React, { useState, useEffect } from 'react'
import {
  View, Text, ScrollView, FlatList, TouchableOpacity,
  StyleSheet, RefreshControl, TextInput, Alert,
} from 'react-native'
import { useNavigation } from '@react-navigation/native'
import { analyticsApi, bookingsApi, paymentsApi, authApi } from '@/api/services'
import { StatCard, Card, SectionHeader, StatusBadge, EmptyState, Skeleton } from '@/components/common/Cards'
import { AppSettingsCard } from '@/components/common/AppSettingsCard'
import { NotificationPreferencesCard } from '@/components/common/NotificationPreferencesCard'
import { PortalHeader } from '@/components/common/PortalHeader'
import { Button } from '@/components/common/Button'
import { getTheme, colors, spacing, typography, radius } from '@/theme'
import { formatKES, formatDate } from '@/utils/formatters'
import { useAuthStore } from '@/stores/authStore'
import type { HotelDashboard, Booking } from '@/types'

// ─── Dashboard ────────────────────────────────────────────────────────────────
export const HotelDashboardScreen: React.FC = () => {
  const nav = useNavigation<any>()
  const theme = getTheme('hotel_owner')
  const { user } = useAuthStore()
  const [stats, setStats] = useState<HotelDashboard | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  const load = async () => {
    try { const { data } = await analyticsApi.hotelDashboard(); setStats(data.data) }
    catch { setStats({ total_listings: 2, active_listings: 2, upcoming_checkins: 3, current_guests: 7, total_bookings_this_month: 24, revenue_this_month: 144000, wallet_balance: 98000 }) }
    finally { setRefreshing(false) }
  }
  useEffect(() => { load() }, [])

  return (
    <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
      <PortalHeader theme={theme} />
      <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: 12 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} tintColor={theme.primary} />}>

        <View style={[s.hero, { backgroundColor: theme.primary }]}>
          <Text style={s.heroSub}>Welcome, {user?.first_name} 🏨</Text>
          <Text style={s.heroTitle}>Hotel / BnB Portal</Text>
          {stats && (
            <View style={s.heroRow}>
              {[{ l: 'Active Listings', v: stats.active_listings }, { l: 'Guests Now', v: stats.current_guests }, { l: 'Revenue', v: formatKES(stats.revenue_this_month) }].map(h => (
                <View key={h.l} style={s.heroBadge}>
                  <Text style={s.heroBadgeVal}>{h.v}</Text>
                  <Text style={s.heroBadgeLbl}>{h.l}</Text>
                </View>
              ))}
            </View>
          )}
        </View>

        {stats && stats.upcoming_checkins > 0 && (
          <TouchableOpacity style={[s.alertBanner, { backgroundColor: theme.primaryBg, borderColor: theme.primary + '50' }]} onPress={() => nav.navigate('HotelBookings')}>
            <Text style={{ fontSize: 22 }}>🔑</Text>
            <View style={{ flex: 1 }}>
              <Text style={{ fontWeight: '700', fontSize: typography.sm, color: theme.primaryDark }}>{stats.upcoming_checkins} check-in(s) scheduled today</Text>
              <Text style={{ fontSize: typography.xs, color: theme.primary }}>Tap to manage bookings →</Text>
            </View>
          </TouchableOpacity>
        )}

        {stats ? (
          <View style={{ gap: 10 }}>
            <View style={s.row}>
              <StatCard label="Current Guests" value={stats.current_guests} icon="👥" color={theme.primary} style={{ flex: 1 }} />
              <StatCard label="Bookings (Month)" value={stats.total_bookings_this_month} icon="📅" color="#6366f1" style={{ flex: 1 }} />
            </View>
            <View style={s.row}>
              <StatCard label="Revenue (Month)" value={stats.revenue_this_month} currency icon="💰" color="#f59e0b" style={{ flex: 1 }} />
              <StatCard label="Wallet Balance" value={stats.wallet_balance} currency icon="💳" color="#10b981" style={{ flex: 1 }} />
            </View>
          </View>
        ) : (
          <View style={s.row}><Skeleton height={80} style={{ flex: 1 }} /><Skeleton height={80} style={{ flex: 1 }} /></View>
        )}

        <SectionHeader title="Quick Actions" />
        <View style={s.quickGrid}>
          {[
            { icon: '🏨', label: 'Listings', route: 'HotelListings', color: theme.primary },
            { icon: '📅', label: 'Bookings', route: 'HotelBookings', color: '#6366f1' },
            { icon: '💰', label: 'Wallet', route: 'HotelWallet', color: '#f59e0b' },
            { icon: '👤', label: 'Profile', route: 'HotelProfile', color: '#8b5cf6' },
          ].map(q => (
            <TouchableOpacity key={q.route} style={s.quickBtn} onPress={() => nav.navigate(q.route)}>
              <View style={[s.quickIcon, { backgroundColor: q.color + '18' }]}>
                <Text style={{ fontSize: 22 }}>{q.icon}</Text>
              </View>
              <Text style={s.quickLabel}>{q.label}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </ScrollView>
    </View>
  )
}

// ─── Bookings ─────────────────────────────────────────────────────────────────
export const HotelBookingsScreen: React.FC = () => {
  const theme = getTheme('hotel_owner')
  const [bookings, setBookings] = useState<Booking[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [filter, setFilter] = useState('')

  const load = async () => {
    try { const { data } = await bookingsApi.bookings(); setBookings(data.data?.results || []) }
    catch { setBookings([]) } finally { setLoading(false); setRefreshing(false) }
  }
  useEffect(() => { load() }, [])

  const filtered = filter ? bookings.filter(b => b.status === filter) : bookings

  const doAction = (id: string, type: 'checkin' | 'checkout' | 'cancel') => {
    const labels = { checkin: 'Check In', checkout: 'Check Out', cancel: 'Cancel' }
    Alert.alert(labels[type], `Confirm ${labels[type]}?`, [
      { text: 'No', style: 'cancel' },
      {
        text: 'Yes', onPress: async () => {
          try {
            if (type === 'checkin') await bookingsApi.checkIn(id)
            else if (type === 'checkout') await bookingsApi.checkOut(id)
            else await bookingsApi.cancelBooking(id, 'Cancelled by host')
            load()
          } catch { Alert.alert('Error', 'Action failed.') }
        }
      }
    ])
  }

  const filters = [
    { k: '', l: 'All' }, { k: 'confirmed', l: 'Confirmed' },
    { k: 'checked_in', l: 'Checked In' }, { k: 'checked_out', l: 'Checked Out' },
  ]

  return (
    <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ maxHeight: 52 }} contentContainerStyle={{ paddingHorizontal: spacing.lg, paddingVertical: 10, gap: 8, flexDirection: 'row' }}>
        {filters.map(f => (
          <TouchableOpacity key={f.k} style={[s.filterBtn, filter === f.k && { backgroundColor: theme.primary }]} onPress={() => setFilter(f.k)}>
            <Text style={[s.filterText, filter === f.k && { color: colors.white }]}>{f.l}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
      {loading ? (
        <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: 12 }}>
          {[0, 1, 2].map(i => <Skeleton key={i} height={120} />)}
        </ScrollView>
      ) : (
        <FlatList
          data={filtered}
          keyExtractor={i => i.id}
          contentContainerStyle={{ padding: spacing.lg, gap: 12 }}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} tintColor={theme.primary} />}
          ListEmptyComponent={<EmptyState emoji="📅" message="No bookings found" />}
          renderItem={({ item }) => (
            <Card style={{ padding: spacing.lg }}>
              <View style={s.bookingTop}>
                <View style={{ flex: 1 }}>
                  <Text style={s.bookingRef}>{item.booking_reference}</Text>
                  <Text style={s.guestName}>{item.guest_name}</Text>
                  <Text style={s.roomName}>{item.room_type_name}</Text>
                </View>
                <StatusBadge status={item.status} />
              </View>
              <View style={s.bookingDates}>
                <View><Text style={s.dateLabel}>Check-in</Text><Text style={s.dateVal}>{formatDate(item.check_in_date)}</Text></View>
                <Text style={s.dateSep}>→</Text>
                <View><Text style={s.dateLabel}>Check-out</Text><Text style={s.dateVal}>{formatDate(item.check_out_date)}</Text></View>
                <View><Text style={s.dateLabel}>Nights</Text><Text style={s.dateVal}>{item.nights}</Text></View>
                <View><Text style={s.dateLabel}>Total</Text><Text style={[s.dateVal, { color: theme.primary }]}>{formatKES(item.total_amount)}</Text></View>
              </View>
              <View style={s.bookingActions}>
                {item.status === 'confirmed' && (
                  <TouchableOpacity style={[s.actionBtn, { backgroundColor: theme.primary }]} onPress={() => doAction(item.id, 'checkin')}>
                    <Text style={s.actionText}>✓ Check In</Text>
                  </TouchableOpacity>
                )}
                {item.status === 'checked_in' && (
                  <TouchableOpacity style={[s.actionBtn, { backgroundColor: '#16a34a' }]} onPress={() => doAction(item.id, 'checkout')}>
                    <Text style={s.actionText}>Check Out</Text>
                  </TouchableOpacity>
                )}
                {item.status === 'confirmed' && (
                  <TouchableOpacity style={[s.actionBtn, { backgroundColor: '#fee2e2' }]} onPress={() => doAction(item.id, 'cancel')}>
                    <Text style={[s.actionText, { color: '#dc2626' }]}>Cancel</Text>
                  </TouchableOpacity>
                )}
              </View>
            </Card>
          )}
        />
      )}
    </View>
  )
}

// ─── Wallet ────────────────────────────────────────────────────────────────────
export const HotelWalletScreen: React.FC = () => {
  const theme = getTheme('hotel_owner')
  const [balance, setBalance] = useState(0)
  const [transactions, setTransactions] = useState<any[]>([])
  const [amount, setAmount] = useState('')
  const [phone, setPhone] = useState('+254')
  const [withdrawing, setWithdrawing] = useState(false)

  useEffect(() => {
    paymentsApi.wallet()
      .then(({ data }) => { setBalance(data.data.balance); setTransactions(data.data.recent_transactions || []) })
      .catch(() => setBalance(98000))
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
    <ScrollView style={{ flex: 1, backgroundColor: colors.gray50 }} contentContainerStyle={{ padding: spacing.lg, gap: 14, paddingBottom: 40 }}>
      <View style={[s.balCard, { backgroundColor: theme.primary }]}>
        <Text style={s.balLabel}>Available Balance</Text>
        <Text style={s.balAmount}>{formatKES(balance)}</Text>
        <Text style={s.balSub}>Booking revenue after platform commission</Text>
      </View>
      <Card style={{ padding: spacing.lg }}>
        <Text style={s.sectionTitle}>Withdraw to M-Pesa</Text>
        <Text style={s.label}>Amount (KES)</Text>
        <TextInput style={s.input} value={amount} onChangeText={setAmount} keyboardType="numeric" placeholder="Enter amount" placeholderTextColor={colors.gray400} />
        <Text style={s.label}>M-Pesa Number</Text>
        <TextInput style={s.input} value={phone} onChangeText={setPhone} keyboardType="phone-pad" placeholderTextColor={colors.gray400} />
        <Button label={`Withdraw ${amount ? formatKES(parseFloat(amount) || 0) : ''}`} onPress={withdraw} loading={withdrawing} color={theme.primary} fullWidth />
      </Card>
      {transactions.length > 0 && (
        <Card style={{ padding: spacing.lg }}>
          <Text style={s.sectionTitle}>Recent Transactions</Text>
          {transactions.map(tx => (
            <View key={tx.id} style={s.txRow}>
              <View style={[s.txDot, { backgroundColor: tx.entry_type === 'credit' ? '#dcfce7' : '#fee2e2' }]}>
                <Text style={{ fontWeight: '800', color: tx.entry_type === 'credit' ? '#16a34a' : '#dc2626', fontSize: 16 }}>{tx.entry_type === 'credit' ? '+' : '−'}</Text>
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

// ─── Profile ──────────────────────────────────────────────────────────────────
export const HotelProfileScreen: React.FC = () => {
  const theme = getTheme('hotel_owner')
  const { user, fetchMe, logout } = useAuthStore()
  const [form, setForm] = useState({ first_name: '', last_name: '', county: '', town: '' })
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const initials = ((user?.first_name?.[0] || '') + (user?.last_name?.[0] || '')).toUpperCase() || '?'

  useEffect(() => {
    if (user) setForm({ first_name: user.first_name || '', last_name: user.last_name || '', county: user.county || '', town: user.town || '' })
  }, [user])

  const save = async () => {
    setSaving(true)
    try { await authApi.updateProfile(form); await fetchMe(); setSaved(true); setTimeout(() => setSaved(false), 2500) }
    catch { Alert.alert('Error', 'Failed to save profile.') }
    finally { setSaving(false) }
  }

  return (
    <ScrollView style={{ flex: 1, backgroundColor: colors.gray50 }} contentContainerStyle={{ padding: spacing.lg, gap: 14, paddingBottom: 40 }}>
      <View style={s.avatarSection}>
        <View style={[s.avatar, { backgroundColor: theme.primary }]}>
          <Text style={s.avatarText}>{initials}</Text>
        </View>
        <Text style={s.name}>{user?.first_name} {user?.last_name}</Text>
        <Text style={s.email}>{user?.email}</Text>
        <View style={[s.rolePill, { backgroundColor: theme.primaryLight }]}>
          <Text style={[s.roleLabel, { color: theme.primary }]}>🏨 Hotel / BnB Owner</Text>
        </View>
      </View>
      <Card style={{ padding: spacing.lg }}>
        <Text style={s.sectionTitle}>Personal Info</Text>
        <View style={{ flexDirection: 'row', gap: 10 }}>
          <View style={{ flex: 1 }}>
            <Text style={s.label}>First name</Text>
            <TextInput style={s.input} value={form.first_name} onChangeText={v => setForm(f => ({ ...f, first_name: v }))} placeholderTextColor={colors.gray400} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={s.label}>Last name</Text>
            <TextInput style={s.input} value={form.last_name} onChangeText={v => setForm(f => ({ ...f, last_name: v }))} placeholderTextColor={colors.gray400} />
          </View>
        </View>
        <Text style={s.label}>County</Text>
        <TextInput style={s.input} value={form.county} onChangeText={v => setForm(f => ({ ...f, county: v }))} placeholder="e.g. Nairobi" placeholderTextColor={colors.gray400} />
        <Text style={s.label}>Town</Text>
        <TextInput style={s.input} value={form.town} onChangeText={v => setForm(f => ({ ...f, town: v }))} placeholder="e.g. Kilimani" placeholderTextColor={colors.gray400} />
        <Button label={saved ? '✓ Saved!' : 'Save Changes'} onPress={save} loading={saving} color={saved ? '#16a34a' : theme.primary} fullWidth style={{ marginTop: 8 }} />
      </Card>
      <NotificationPreferencesCard accentColor={theme.primary} />
      <AppSettingsCard accentColor={theme.primary} />
      <TouchableOpacity style={s.logoutBtn} onPress={logout}>
        <Text style={s.logoutText}>Sign Out</Text>
      </TouchableOpacity>
    </ScrollView>
  )
}

const s = StyleSheet.create({
  hero: { borderRadius: radius.xl, padding: spacing.xl },
  heroSub: { color: 'rgba(255,255,255,0.7)', fontSize: typography.sm, fontWeight: '500' },
  heroTitle: { color: colors.white, fontSize: typography.xxl, fontWeight: '800', marginTop: 2 },
  heroRow: { flexDirection: 'row', gap: 10, marginTop: 16 },
  heroBadge: { flex: 1, backgroundColor: 'rgba(255,255,255,0.18)', borderRadius: radius.lg, padding: 10, alignItems: 'center' },
  heroBadgeVal: { color: colors.white, fontSize: typography.sm, fontWeight: '800' },
  heroBadgeLbl: { color: 'rgba(255,255,255,0.6)', fontSize: typography.xs, marginTop: 2 },
  alertBanner: { flexDirection: 'row', alignItems: 'center', gap: 12, borderRadius: radius.xl, borderWidth: 1.5, padding: spacing.md },
  row: { flexDirection: 'row', gap: 10 },
  quickGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  quickBtn: { width: '47%', backgroundColor: colors.white, borderRadius: radius.xl, padding: spacing.md, alignItems: 'center', borderWidth: 1, borderColor: colors.gray100 },
  quickIcon: { width: 48, height: 48, borderRadius: radius.lg, alignItems: 'center', justifyContent: 'center', marginBottom: 6 },
  quickLabel: { fontSize: typography.xs, fontWeight: '600', color: colors.gray700 },
  filterBtn: { paddingHorizontal: 14, paddingVertical: 7, borderRadius: radius.full, backgroundColor: colors.gray100, borderWidth: 1, borderColor: colors.gray200 },
  filterText: { fontSize: typography.xs, fontWeight: '600', color: colors.gray600 },
  bookingTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 },
  bookingRef: { fontSize: typography.xs, fontFamily: 'monospace', fontWeight: '700', color: colors.gray500 },
  guestName: { fontSize: typography.base, fontWeight: '700', color: colors.gray900, marginTop: 2 },
  roomName: { fontSize: typography.xs, color: colors.gray400, marginTop: 1 },
  bookingDates: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 12, flexWrap: 'wrap' },
  dateLabel: { fontSize: typography.xs, color: colors.gray400, fontWeight: '500' },
  dateVal: { fontSize: typography.sm, fontWeight: '700', color: colors.gray900, marginTop: 2 },
  dateSep: { fontSize: 18, color: colors.gray300 },
  bookingActions: { flexDirection: 'row', gap: 8 },
  actionBtn: { flex: 1, borderRadius: radius.lg, paddingVertical: 10, alignItems: 'center' },
  actionText: { color: colors.white, fontWeight: '700', fontSize: typography.sm },
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
  logoutBtn: { padding: spacing.lg, alignItems: 'center', backgroundColor: colors.white, borderRadius: radius.xl, borderWidth: 1.5, borderColor: '#fecaca' },
  logoutText: { color: colors.red500, fontWeight: '700', fontSize: typography.base },
})
