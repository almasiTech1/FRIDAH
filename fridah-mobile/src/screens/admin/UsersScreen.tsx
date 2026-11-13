import React, { useState, useEffect, useCallback } from 'react'
import { View, Text, FlatList, RefreshControl, TextInput, StyleSheet, TouchableOpacity } from 'react-native'
import { analyticsApi } from '@/api/services'
import { Card, Badge, EmptyState } from '@/components/common/Cards'
import { getTheme, colors, spacing, typography, radius } from '@/theme'
import { formatDate } from '@/utils/formatters'
import type { User } from '@/types'

export const AdminUsersScreen: React.FC = () => {
  const theme = getTheme('admin')
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [search, setSearch] = useState('')

  const load = useCallback(async () => {
    try {
      const { data } = await analyticsApi.users({ search: search || undefined })
      setUsers(data.data?.results || data.data || [])
    } catch { setUsers([]) }
    finally { setLoading(false); setRefreshing(false) }
  }, [search])

  useEffect(() => { const t = setTimeout(load, 400); return () => clearTimeout(t) }, [search])

  const roleColor = (r: string) => ({ tenant: '#10b981', landlord: '#6366f1', admin: '#8b5cf6', service_provider: '#f97316', hotel_owner: '#f59e0b' }[r] || '#6b7280')
  const roleBg = (r: string) => roleColor(r) + '18'
  const kycColor = (k: string) => ({ verified: '#16a34a', pending: '#d97706', rejected: '#dc2626', not_submitted: '#9ca3af' }[k] || '#9ca3af')
  const kycBg = (k: string) => kycColor(k) + '18'

  return (
    <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
      <View style={styles.searchWrap}>
        <View style={styles.searchBox}>
          <Text style={styles.searchIcon}>🔍</Text>
          <TextInput style={styles.searchInput} placeholder="Search name, email, phone…" placeholderTextColor={colors.gray400} value={search} onChangeText={setSearch} />
          {search ? <TouchableOpacity onPress={() => setSearch('')}><Text style={{ color: colors.gray400, fontSize: 16 }}>✕</Text></TouchableOpacity> : null}
        </View>
      </View>
      <FlatList
        data={users}
        keyExtractor={i => i.id}
        contentContainerStyle={{ padding: spacing.lg, gap: 10 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} tintColor={theme.primary} />}
        ListEmptyComponent={<EmptyState emoji="👥" message="No users found" />}
        renderItem={({ item }) => (
          <Card style={styles.card}>
            <View style={styles.cardTop}>
              <View style={[styles.avatar, { backgroundColor: roleColor(item.role) + '25' }]}>
                <Text style={[styles.avatarText, { color: roleColor(item.role) }]}>
                  {((item.first_name?.[0] || '') + (item.last_name?.[0] || '')).toUpperCase() || item.username[0].toUpperCase()}
                </Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.name}>{item.first_name} {item.last_name}</Text>
                <Text style={styles.email}>{item.email}</Text>
                <Text style={styles.phone}>{item.phone_number}</Text>
              </View>
              <View style={{ gap: 4, alignItems: 'flex-end' }}>
                <Badge label={item.role.replace(/_/g, ' ')} color={roleColor(item.role)} bg={roleBg(item.role)} />
                <Badge label={item.kyc_status} color={kycColor(item.kyc_status)} bg={kycBg(item.kyc_status)} />
              </View>
            </View>
            <Text style={styles.joined}>Joined {formatDate(item.created_at)}</Text>
          </Card>
        )}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  searchWrap: { padding: spacing.lg, paddingBottom: 4 },
  searchBox: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: colors.white, borderRadius: radius.xl, borderWidth: 1.5, borderColor: colors.gray200, paddingHorizontal: 14, paddingVertical: 11 },
  searchIcon: { fontSize: 16 },
  searchInput: { flex: 1, fontSize: typography.sm, color: colors.gray900 },
  card: { padding: spacing.md },
  cardTop: { flexDirection: 'row', alignItems: 'flex-start', gap: 12 },
  avatar: { width: 44, height: 44, borderRadius: 14, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  avatarText: { fontSize: typography.base, fontWeight: '800' },
  name: { fontSize: typography.sm, fontWeight: '700', color: colors.gray900 },
  email: { fontSize: typography.xs, color: colors.gray500, marginTop: 1 },
  phone: { fontSize: typography.xs, color: colors.gray400, marginTop: 1 },
  joined: { fontSize: typography.xs, color: colors.gray400, marginTop: 8 },
})
