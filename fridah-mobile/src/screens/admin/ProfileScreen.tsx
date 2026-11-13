import React from 'react'
import { View, Text, ScrollView, StyleSheet } from 'react-native'
import { useAuthStore } from '@/stores/authStore'
import { Card } from '@/components/common/Cards'
import { Button } from '@/components/common/Button'
import { NotificationPreferencesCard } from '@/components/common/NotificationPreferencesCard'
import { colors, spacing, typography, getTheme } from '@/theme'

/** Administrators' account screen: who is signed in, notification preferences, sign out. */
export const AdminProfileScreen: React.FC = () => {
  const theme = getTheme('admin')
  const { user, logout } = useAuthStore()
  return (
    <ScrollView style={{ backgroundColor: colors.gray50 }} contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
      <Card>
        <Text style={styles.name}>{user?.first_name} {user?.last_name}</Text>
        <Text style={styles.meta}>{user?.email}</Text>
        <Text style={styles.meta}>Administrator</Text>
      </Card>
      <NotificationPreferencesCard accentColor={theme.primary} />
      <Button label="Sign out" variant="outline" color="#dc2626" onPress={() => logout()} />
      <View style={{ height: spacing.xl }} />
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  name: { fontSize: typography.lg, fontWeight: '800', color: colors.gray900 },
  meta: { fontSize: typography.sm, color: colors.gray500, marginTop: 2 },
})
