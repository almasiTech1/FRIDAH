import React, { useState, useEffect } from 'react'
import { View, Text, FlatList, TouchableOpacity, StyleSheet, RefreshControl, Alert } from 'react-native'
import { servicesApi } from '@/api/services'
import { Card, StatusBadge, EmptyState } from '@/components/common/Cards'
import { getTheme, colors, spacing, typography, radius } from '@/theme'
import { formatDate } from '@/utils/formatters'
import type { ServiceJob } from '@/types'

export const ProviderMyJobsScreen: React.FC = () => {
  const theme = getTheme('service_provider')
  const [jobs, setJobs] = useState<ServiceJob[]>([])
  const [refreshing, setRefreshing] = useState(false)

  const load = async () => {
    try {
      const { data } = await servicesApi.jobs()
      setJobs((data.data?.results || []).filter((j: ServiceJob) => ['assigned', 'in_progress', 'completed'].includes(j.status)))
    } catch { setJobs([]) }
    finally { setRefreshing(false) }
  }
  useEffect(() => { load() }, [])

  const doAction = (id: string, type: 'start' | 'complete') => {
    const label = type === 'start' ? 'Start Job' : 'Mark Complete'
    Alert.alert(label, `Confirm ${label.toLowerCase()}?`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Confirm', onPress: async () => {
          try {
            if (type === 'start') await servicesApi.startJob(id)
            else await servicesApi.completeJob(id)
            load()
          } catch { Alert.alert('Error', 'Action failed.') }
        }
      }
    ])
  }

  const statusColor = (s: string) => ({ assigned: '#2563eb', in_progress: '#d97706', completed: '#16a34a' }[s] || '#6b7280')
  const statusBg = (s: string) => ({ assigned: '#dbeafe', in_progress: '#fef3c7', completed: '#dcfce7' }[s] || '#f3f4f6')

  return (
    <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
      <FlatList
        data={jobs}
        keyExtractor={i => i.id}
        contentContainerStyle={{ padding: spacing.lg, gap: 12 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} tintColor={theme.primary} />}
        ListEmptyComponent={<EmptyState emoji="🔧" message="No active jobs yet. Browse open jobs to get started." />}
        renderItem={({ item }) => (
          <Card style={{ padding: spacing.lg }}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
              <View style={{ flex: 1, marginRight: 10 }}>
                <Text style={styles.jobTitle}>{item.title}</Text>
                <Text style={styles.jobMeta}>📍 {item.town}, {item.county} · {item.category_name}</Text>
              </View>
              <View style={{ backgroundColor: statusBg(item.status), borderRadius: radius.full, paddingHorizontal: 10, paddingVertical: 4 }}>
                <Text style={{ color: statusColor(item.status), fontSize: typography.xs, fontWeight: '700', textTransform: 'capitalize' }}>
                  {item.status.replace('_', ' ')}
                </Text>
              </View>
            </View>
            <Text style={styles.desc}>{item.description}</Text>
            {item.scheduled_date && <Text style={styles.scheduled}>📅 Scheduled: {formatDate(item.scheduled_date)}</Text>}
            <View style={{ flexDirection: 'row', gap: 8, marginTop: 12 }}>
              {item.status === 'assigned' && (
                <TouchableOpacity style={[styles.actionBtn, { backgroundColor: theme.primary }]} onPress={() => doAction(item.id, 'start')}>
                  <Text style={styles.actionText}>▶ Start Job</Text>
                </TouchableOpacity>
              )}
              {item.status === 'in_progress' && (
                <TouchableOpacity style={[styles.actionBtn, { backgroundColor: '#16a34a' }]} onPress={() => doAction(item.id, 'complete')}>
                  <Text style={styles.actionText}>✓ Mark Complete</Text>
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
  jobTitle: { fontSize: typography.base, fontWeight: '700', color: colors.gray900 },
  jobMeta: { fontSize: typography.xs, color: colors.gray500, marginTop: 2 },
  desc: { fontSize: typography.sm, color: colors.gray600, lineHeight: 20 },
  scheduled: { fontSize: typography.xs, color: colors.gray500, marginTop: 6 },
  actionBtn: { flex: 1, borderRadius: radius.lg, paddingVertical: 11, alignItems: 'center' },
  actionText: { color: colors.white, fontWeight: '700', fontSize: typography.sm },
})
