import React from 'react'
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native'
import { useAuthStore } from '@/stores/authStore'
import { useNotificationsStore } from '@/stores/notificationsStore'
import { colors, typography, spacing } from '@/theme'
import type { PortalTheme } from '@/theme'

interface Props {
  theme: PortalTheme
  title?: string
  onNotifPress?: () => void
  rightAction?: React.ReactNode
}

export const PortalHeader: React.FC<Props> = ({
  theme, title, onNotifPress, rightAction,
}) => {
  const { user } = useAuthStore()
  const { unreadCount } = useNotificationsStore()
  const initials =
    ((user?.first_name?.[0] || '') + (user?.last_name?.[0] || '')).toUpperCase() ||
    user?.username?.[0]?.toUpperCase() || '?'

  return (
    <View style={[styles.header, { backgroundColor: theme.primary }]}>
      <View style={styles.left}>
        <View style={[styles.avatar, { backgroundColor: theme.primaryDark }]}>
          <Text style={styles.avatarText}>{initials}</Text>
        </View>
        <View>
          <Text style={styles.greeting}>
            {title || `Hi, ${user?.first_name || 'there'} 👋`}
          </Text>
          <Text style={styles.role}>{theme.label}</Text>
        </View>
      </View>
      <View style={styles.right}>
        {rightAction}
        {onNotifPress && (
          <TouchableOpacity onPress={onNotifPress} style={styles.notifBtn}>
            <Text style={styles.notifIcon}>🔔</Text>
            {unreadCount > 0 && (
              <View style={styles.badge}>
                <Text style={styles.badgeText}>
                  {unreadCount > 9 ? '9+' : unreadCount}
                </Text>
              </View>
            )}
          </TouchableOpacity>
        )}
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.lg,
  },
  left: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  avatar: {
    width: 38, height: 38, borderRadius: 19,
    alignItems: 'center', justifyContent: 'center',
  },
  avatarText: { color: colors.white, fontSize: typography.base, fontWeight: '700' },
  greeting: { color: colors.white, fontSize: typography.base, fontWeight: '600' },
  role: { color: 'rgba(255,255,255,0.7)', fontSize: typography.xs },
  right: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  notifBtn: { position: 'relative', padding: 4 },
  notifIcon: { fontSize: 22 },
  badge: {
    position: 'absolute', top: 0, right: 0,
    backgroundColor: colors.red500,
    minWidth: 16, height: 16, borderRadius: 8,
    alignItems: 'center', justifyContent: 'center', paddingHorizontal: 2,
  },
  badgeText: { color: colors.white, fontSize: 9, fontWeight: '700' },
})
