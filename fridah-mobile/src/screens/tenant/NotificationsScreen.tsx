import React, { useEffect } from 'react'
import { View, Text, FlatList, TouchableOpacity, StyleSheet, RefreshControl } from 'react-native'
import { useNotificationsStore } from '@/stores/notificationsStore'
import { Card, EmptyState } from '@/components/common/Cards'
import { Button } from '@/components/common/Button'
import { getTheme, colors, spacing, typography, radius } from '@/theme'
import { relativeTime } from '@/utils/formatters'

export const TenantNotificationsScreen: React.FC = () => {
  const theme = getTheme('tenant')
  const { notifications, unreadCount, fetchNotifications, markRead, markAllRead } = useNotificationsStore()
  const [refreshing, setRefreshing] = React.useState(false)

  useEffect(() => { fetchNotifications() }, [])

  const refresh = async () => { setRefreshing(true); await fetchNotifications(); setRefreshing(false) }

  const typeIcon = (t: string) => ({ payment:'💳', lease:'📋', maintenance:'🔧', booking:'🏨', kyc:'🔒', general:'📢' }[t] || '📢')

  return (
    <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
      {unreadCount > 0 && (
        <View style={styles.topBar}>
          <Text style={styles.unread}>{unreadCount} unread</Text>
          <TouchableOpacity onPress={markAllRead}>
            <Text style={[styles.markAll, { color: theme.primary }]}>Mark all read</Text>
          </TouchableOpacity>
        </View>
      )}
      <FlatList
        data={notifications}
        keyExtractor={i => i.id}
        contentContainerStyle={{ padding: spacing.lg, gap: 10 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={theme.primary} />}
        ListEmptyComponent={<EmptyState emoji="🔔" message="No notifications yet" />}
        renderItem={({ item }) => (
          <TouchableOpacity onPress={() => !item.is_read && markRead(item.id)} activeOpacity={0.8}>
            <Card style={[styles.card, !item.is_read ? { borderLeftWidth: 3, borderLeftColor: theme.primary } : null]}>
              <View style={styles.row}>
                <View style={[styles.iconBox, { backgroundColor: theme.primaryLight }]}>
                  <Text style={{ fontSize: 18 }}>{typeIcon(item.notification_type)}</Text>
                </View>
                <View style={{ flex: 1 }}>
                  <View style={styles.titleRow}>
                    <Text style={[styles.title, !item.is_read && { color: colors.gray900 }]}>{item.title}</Text>
                    {!item.is_read && <View style={[styles.dot, { backgroundColor: theme.primary }]} />}
                  </View>
                  <Text style={styles.msg}>{item.message}</Text>
                  <Text style={styles.time}>{relativeTime(item.created_at)}</Text>
                </View>
              </View>
            </Card>
          </TouchableOpacity>
        )}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  topBar: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: spacing.lg, paddingBottom: 4 },
  unread: { fontSize: typography.sm, fontWeight: '700', color: colors.gray700 },
  markAll: { fontSize: typography.sm, fontWeight: '600' },
  card: { padding: spacing.md },
  row: { flexDirection: 'row', gap: 12, alignItems: 'flex-start' },
  iconBox: { width: 40, height: 40, borderRadius: radius.lg, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  title: { fontSize: typography.sm, fontWeight: '600', color: colors.gray700, flex: 1 },
  dot: { width: 8, height: 8, borderRadius: 4, flexShrink: 0 },
  msg: { fontSize: typography.xs, color: colors.gray500, marginTop: 3, lineHeight: 18 },
  time: { fontSize: typography.xs, color: colors.gray400, marginTop: 4 },
})
