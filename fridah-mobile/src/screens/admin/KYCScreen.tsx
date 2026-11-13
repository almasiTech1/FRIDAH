import React, { useState, useEffect } from 'react'
import { View, Text, FlatList, TouchableOpacity, StyleSheet, RefreshControl, Alert } from 'react-native'
import { analyticsApi } from '@/api/services'
import { Card, EmptyState } from '@/components/common/Cards'
import { Button } from '@/components/common/Button'
import { getTheme, colors, spacing, typography, radius } from '@/theme'
import type { User } from '@/types'

export const AdminKYCScreen: React.FC = () => {
  const theme = getTheme('admin')
  const [pending, setPending] = useState<User[]>([])
  const [refreshing, setRefreshing] = useState(false)
  const [processing, setProcessing] = useState('')

  const load = async () => {
    try { const { data } = await analyticsApi.kycPending(); setPending(data.data?.results || data.data || []) }
    catch { setPending([]) } finally { setRefreshing(false) }
  }
  useEffect(() => { load() }, [])

  const review = async (userId: string, action: 'approve' | 'reject') => {
    if (action === 'reject') {
      Alert.prompt('Rejection Reason', 'Enter reason for rejection:', async (reason) => {
        setProcessing(userId)
        try { await analyticsApi.reviewKyc(userId, 'reject', reason || ''); load() }
        finally { setProcessing('') }
      })
      return
    }
    Alert.alert('Approve KYC', 'Approve this user\'s identity verification?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Approve', onPress: async () => {
          setProcessing(userId)
          try { await analyticsApi.reviewKyc(userId, 'approve'); load() }
          finally { setProcessing('') }
        }
      }
    ])
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
      <View style={styles.headerBanner}>
        <Text style={styles.bannerText}>🔒 {pending.length} submission(s) awaiting review</Text>
      </View>
      <FlatList
        data={pending}
        keyExtractor={i => i.id}
        contentContainerStyle={{ padding: spacing.lg, gap: 12 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} tintColor={theme.primary} />}
        ListEmptyComponent={
          <EmptyState emoji="✅" message="All KYC submissions reviewed!" />
        }
        renderItem={({ item }) => (
          <Card style={{ padding: spacing.lg }}>
            <View style={styles.userRow}>
              <View style={[styles.avatar, { backgroundColor: theme.primaryLight }]}>
                <Text style={[styles.avatarText, { color: theme.primary }]}>
                  {((item.first_name?.[0] || '') + (item.last_name?.[0] || '')).toUpperCase() || '?'}
                </Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.name}>{item.first_name} {item.last_name}</Text>
                <Text style={styles.email}>{item.email}</Text>
                <Text style={styles.phone}>{item.phone_number}</Text>
                <Text style={styles.role}>Role: {item.role.replace(/_/g, ' ')}</Text>
              </View>
            </View>
            {item.national_id && (
              <View style={styles.idRow}>
                <Text style={styles.idLabel}>National ID:</Text>
                <Text style={styles.idValue}>{item.national_id}</Text>
              </View>
            )}
            <View style={styles.btnRow}>
              <Button
                label={processing === item.id ? '...' : '✕ Reject'}
                onPress={() => review(item.id, 'reject')}
                variant="outline"
                style={{ flex: 1, borderColor: '#fecaca' }}
                textStyle={{ color: colors.red500 }}
                disabled={!!processing}
              />
              <Button
                label={processing === item.id ? '...' : '✓ Approve'}
                onPress={() => review(item.id, 'approve')}
                color="#16a34a"
                style={{ flex: 1 }}
                disabled={!!processing}
                loading={processing === item.id}
              />
            </View>
          </Card>
        )}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  headerBanner: { backgroundColor: '#fef3c7', padding: spacing.md, margin: spacing.lg, marginBottom: 0, borderRadius: radius.lg, borderWidth: 1, borderColor: '#fde68a' },
  bannerText: { fontSize: typography.sm, fontWeight: '600', color: '#92400e', textAlign: 'center' },
  userRow: { flexDirection: 'row', gap: 12, marginBottom: 12 },
  avatar: { width: 48, height: 48, borderRadius: 14, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  avatarText: { fontSize: typography.lg, fontWeight: '800' },
  name: { fontSize: typography.base, fontWeight: '700', color: colors.gray900 },
  email: { fontSize: typography.xs, color: colors.gray500, marginTop: 2 },
  phone: { fontSize: typography.xs, color: colors.gray400, marginTop: 1 },
  role: { fontSize: typography.xs, color: colors.gray400, textTransform: 'capitalize', marginTop: 2 },
  idRow: { flexDirection: 'row', gap: 8, backgroundColor: colors.gray50, padding: 10, borderRadius: radius.md, marginBottom: 12 },
  idLabel: { fontSize: typography.xs, fontWeight: '600', color: colors.gray500 },
  idValue: { fontSize: typography.xs, fontWeight: '700', color: colors.gray900 },
  btnRow: { flexDirection: 'row', gap: 10 },
})
