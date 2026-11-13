import React, { useState, useEffect } from 'react'
import { View, Text, FlatList, TouchableOpacity, StyleSheet, RefreshControl, Alert } from 'react-native'
import { useNavigation } from '@react-navigation/native'
import { propertiesApi } from '@/api/services'
import { Card, StatusBadge, EmptyState } from '@/components/common/Cards'
import { getTheme, colors, spacing, typography, radius } from '@/theme'
import type { Property } from '@/types'

export const AdminPropertiesScreen: React.FC = () => {
  const theme = getTheme('admin')
  const navigation = useNavigation<any>()
  const [properties, setProperties] = useState<Property[]>([])
  const [refreshing, setRefreshing] = useState(false)
  const [filter, setFilter] = useState('pending_approval')

  const load = async () => {
    try { const { data } = await propertiesApi.list({ status: filter || undefined }); setProperties(data.data?.results || []) }
    catch { setProperties([]) } finally { setRefreshing(false) }
  }
  useEffect(() => { load() }, [filter])

  const action = (id: string, act: string, label: string) => {
    Alert.alert(`${label}?`, `Are you sure you want to ${label.toLowerCase()} this property?`, [
      { text: 'Cancel', style: 'cancel' },
      { text: label, onPress: async () => {
        try {
          const res: any = await propertiesApi.approve(id, act)
          // An admin approval alone does not publish a property that also needs the landlord's approval.
          const missing: string[] = res?.data?.data?.missing_approvals || []
          if (act === 'approve' && missing.length) {
            Alert.alert('Approval recorded', `Still waiting on: ${missing.join(', ')}.`)
          }
          load()
        } catch (e: any) {
          Alert.alert('Action failed', e?.response?.data?.error?.message || 'Please try again.')
        }
      } }
    ])
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
      <View style={{ flexDirection: 'row', gap: spacing.sm, margin: spacing.lg, marginBottom: 0 }}>
        <TouchableOpacity style={[styles.filterBtn, { backgroundColor: theme.primary }]}
                          accessibilityRole="button" onPress={() => navigation.navigate('AdminReviewQueue')}>
          <Text style={[styles.filterText, { color: colors.white }]}>Open review queue</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.filterBtn, { backgroundColor: theme.primary }]}
                          accessibilityRole="button" onPress={() => navigation.navigate('AdminAgencies')}>
          <Text style={[styles.filterText, { color: colors.white }]}>Agencies</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.filterBtn, { backgroundColor: theme.primary }]}
                          accessibilityRole="button" onPress={() => navigation.navigate('AdminRefunds')}>
          <Text style={[styles.filterText, { color: colors.white }]}>Refunds</Text>
        </TouchableOpacity>
      </View>
      <View style={styles.filters}>
        {[{ k: 'pending_approval', l: 'Pending' }, { k: 'active', l: 'Active' }, { k: 'suspended', l: 'Suspended' }, { k: '', l: 'All' }].map(f => (
          <TouchableOpacity key={f.k} style={[styles.filterBtn, filter === f.k && { backgroundColor: theme.primary }]} onPress={() => setFilter(f.k)}>
            <Text style={[styles.filterText, filter === f.k && { color: colors.white }]}>{f.l}</Text>
          </TouchableOpacity>
        ))}
      </View>
      <FlatList
        data={properties}
        keyExtractor={i => i.id}
        contentContainerStyle={{ padding: spacing.lg, gap: 12 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} tintColor={theme.primary} />}
        ListEmptyComponent={<EmptyState emoji="🏠" message="No properties found" />}
        renderItem={({ item }) => (
          <Card style={{ padding: spacing.lg }}>
            <View style={styles.cardTop}>
              <View style={{ flex: 1 }}>
                <Text style={styles.propName}>{item.name}</Text>
                <Text style={styles.propMeta}>{item.town}, {item.county} · {item.property_type}</Text>
                <Text style={styles.landlordName}>by {item.landlord_name}</Text>
              </View>
              <View style={{ alignItems: 'flex-end', gap: 4 }}>
                <StatusBadge status={item.status} />
                {item.status !== 'active' && (item as any).review_state ? <StatusBadge status={(item as any).review_state} /> : null}
              </View>
            </View>
            <View style={styles.stats}>
              <Text style={styles.statItem}>🏢 {item.total_units} units</Text>
              <Text style={styles.statItem}>🚪 {item.vacant_units_count} vacant</Text>
            </View>
            <View style={styles.actions}>
              {item.status === 'pending_approval' && (
                <TouchableOpacity style={[styles.actionBtn, { backgroundColor: '#dcfce7' }]} onPress={() => action(item.id, 'approve', 'Approve')}>
                  <Text style={{ color: '#16a34a', fontWeight: '700', fontSize: typography.sm }}>✓ Approve</Text>
                </TouchableOpacity>
              )}
              {item.status === 'active' && (
                <TouchableOpacity style={[styles.actionBtn, { backgroundColor: '#fef3c7' }]} onPress={() => action(item.id, 'suspend', 'Suspend')}>
                  <Text style={{ color: '#d97706', fontWeight: '700', fontSize: typography.sm }}>⏸ Suspend</Text>
                </TouchableOpacity>
              )}
              {item.status === 'suspended' && (
                <TouchableOpacity style={[styles.actionBtn, { backgroundColor: '#dcfce7' }]} onPress={() => action(item.id, 'reinstate', 'Reactivate')}>
                  <Text style={{ color: '#16a34a', fontWeight: '700', fontSize: typography.sm }}>▶ Reactivate</Text>
                </TouchableOpacity>
              )}
            </View>
          </Card>
        )}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  filters: { flexDirection: 'row', gap: 8, padding: spacing.lg, paddingBottom: 4 },
  filterBtn: { paddingHorizontal: 14, paddingVertical: 7, borderRadius: radius.full, backgroundColor: colors.gray100, borderWidth: 1, borderColor: colors.gray200 },
  filterText: { fontSize: typography.xs, fontWeight: '600', color: colors.gray600 },
  cardTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 },
  propName: { fontSize: typography.base, fontWeight: '700', color: colors.gray900 },
  propMeta: { fontSize: typography.xs, color: colors.gray500, marginTop: 2, textTransform: 'capitalize' },
  landlordName: { fontSize: typography.xs, color: colors.gray400, marginTop: 1 },
  stats: { flexDirection: 'row', gap: 16, marginBottom: 12 },
  statItem: { fontSize: typography.xs, color: colors.gray600 },
  actions: { flexDirection: 'row', gap: 8 },
  actionBtn: { flex: 1, borderRadius: radius.lg, paddingVertical: 10, alignItems: 'center' },
})
