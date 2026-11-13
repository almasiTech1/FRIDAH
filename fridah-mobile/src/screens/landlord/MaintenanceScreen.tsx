import React, { useState, useEffect } from 'react'
import { View, Text, FlatList, TouchableOpacity, StyleSheet, RefreshControl, Alert, TextInput, Modal } from 'react-native'
import { rentalsApi } from '@/api/services'
import { Card, StatusBadge, EmptyState } from '@/components/common/Cards'
import { Button } from '@/components/common/Button'
import { getTheme, colors, spacing, typography, radius } from '@/theme'
import { formatDate, priorityColor } from '@/utils/formatters'
import type { MaintenanceRequest } from '@/types'

export const LandlordMaintenanceScreen: React.FC = () => {
  const theme = getTheme('landlord')
  const [requests, setRequests] = useState<MaintenanceRequest[]>([])
  const [refreshing, setRefreshing] = useState(false)
  const [assignModal, setAssignModal] = useState('')
  const [providerId, setProviderId] = useState('')

  const load = async () => {
    try { const { data } = await rentalsApi.maintenanceList(); setRequests(data.data?.results || []) }
    catch { setRequests([]) } finally { setRefreshing(false) }
  }
  useEffect(() => { load() }, [])

  const assign = async (id: string) => {
    if (!providerId) { Alert.alert('Error', 'Enter provider ID'); return }
    try { await rentalsApi.assignMaintenance(id, providerId); setAssignModal(''); setProviderId(''); load() }
    catch { Alert.alert('Error', 'Failed to assign') }
  }

  const priorityDot = (p: string) => ({ low:'#9ca3af', medium:'#3b82f6', high:'#f59e0b', urgent:'#ef4444' }[p] || '#9ca3af')

  return (
    <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
      <FlatList
        data={requests}
        keyExtractor={i => i.id}
        contentContainerStyle={{ padding: spacing.lg, gap: 12 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} tintColor={theme.primary} />}
        ListEmptyComponent={<EmptyState emoji="🔧" message="No maintenance requests" />}
        renderItem={({ item }) => (
          <Card style={{ padding: spacing.lg }}>
            <View style={{ flexDirection: 'row', alignItems: 'flex-start', gap: 10, marginBottom: 8 }}>
              <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: priorityDot(item.priority), marginTop: 4, flexShrink: 0 }} />
              <View style={{ flex: 1 }}>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <Text style={{ fontSize: typography.sm, fontWeight: '700', color: colors.gray900, flex: 1, marginRight: 8 }}>{item.title}</Text>
                  <StatusBadge status={item.status} />
                </View>
                <Text style={{ fontSize: typography.xs, color: colors.gray500, marginTop: 2 }}>{item.tenant_name} · {item.property_name} · Unit {item.unit_number}</Text>
              </View>
            </View>
            <Text style={{ fontSize: typography.sm, color: colors.gray600, marginBottom: 10 }}>{item.description}</Text>
            {item.provider_name
              ? <Text style={{ fontSize: typography.xs, color: colors.gray500 }}>👷 Assigned: {item.provider_name}</Text>
              : item.status === 'open' && (
                <TouchableOpacity style={[styles.assignBtn, { backgroundColor: theme.primary }]} onPress={() => setAssignModal(item.id)}>
                  <Text style={styles.assignText}>Assign Provider</Text>
                </TouchableOpacity>
              )}
          </Card>
        )}
      />
      <Modal visible={!!assignModal} animationType="slide" transparent onRequestClose={() => setAssignModal('')}>
        <View style={styles.overlay}>
          <View style={styles.sheet}>
            <Text style={styles.sheetTitle}>Assign Provider</Text>
            <Text style={styles.sheetLabel}>Provider UUID</Text>
            <TextInput style={styles.input} value={providerId} onChangeText={setProviderId} placeholder="Enter provider ID" placeholderTextColor={colors.gray400} />
            <View style={{ flexDirection: 'row', gap: 10, marginTop: 8 }}>
              <Button label="Cancel" onPress={() => setAssignModal('')} variant="outline" style={{ flex: 1 }} />
              <Button label="Assign" onPress={() => assign(assignModal)} color={theme.primary} style={{ flex: 1 }} />
            </View>
          </View>
        </View>
      </Modal>
    </View>
  )
}

const styles = StyleSheet.create({
  assignBtn: { borderRadius: radius.lg, paddingVertical: 10, alignItems: 'center' },
  assignText: { color: colors.white, fontWeight: '700', fontSize: typography.sm },
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  sheet: { backgroundColor: colors.white, borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: spacing.xl, paddingBottom: 36 },
  sheetTitle: { fontSize: typography.lg, fontWeight: '700', color: colors.gray900, marginBottom: 16 },
  sheetLabel: { fontSize: typography.xs, fontWeight: '600', color: colors.gray600, marginBottom: 6 },
  input: { borderWidth: 1.5, borderColor: colors.gray200, borderRadius: radius.md, paddingHorizontal: 14, paddingVertical: 12, fontSize: typography.sm, color: colors.gray900, marginBottom: 8 },
})
