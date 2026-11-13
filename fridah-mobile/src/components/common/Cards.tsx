import React from 'react'
import { View, Text, StyleSheet, StyleProp, ViewStyle, Animated } from 'react-native'
import { colors, radius, typography, spacing, getSurfaceColors } from '@/theme'
import { formatKES } from '@/utils/formatters'
import { statusColor, statusBg } from '@/utils/formatters'
import { useThemeStore } from '@/stores/themeStore'
import { useReducedMotion } from '@/utils/useReducedMotion'

// ─── Card ─────────────────────────────────────────────────────────────────────
export const Card: React.FC<{ children: React.ReactNode; style?: StyleProp<ViewStyle> }> = ({
  children, style,
}) => {
  const isDark = useThemeStore((s) => s.mode === 'dark')
  const surface = getSurfaceColors(isDark)
  return (
    <View style={[
      styles.card,
      { backgroundColor: surface.surface, borderColor: surface.border },
      style,
    ]}>
      {children}
    </View>
  )
}

// ─── StatCard ─────────────────────────────────────────────────────────────────
interface StatCardProps {
  label: string
  value: number | string
  currency?: boolean
  sub?: string
  icon?: string
  color?: string
  style?: StyleProp<ViewStyle>
}

export const StatCard: React.FC<StatCardProps> = ({
  label, value, currency = false, sub, icon, color, style,
}) => {
  const isDark = useThemeStore((s) => s.mode === 'dark')
  const surface = getSurfaceColors(isDark)
  return (
    <Card style={[styles.statCard, style]}>
      <View style={styles.statHeaderRow}>
        {icon && <Text style={styles.statIcon}>{icon}</Text>}
        <Text style={[styles.statLabel, { color: surface.textMuted }]}>{label}</Text>
      </View>
      <Text style={[styles.statValue, { color: color || surface.text }]}>
        {currency ? formatKES(Number(value)) : value}
      </Text>
      {sub && <Text style={[styles.statSub, { color: surface.textMuted }]}>{sub}</Text>}
    </Card>
  )
}

// ─── Badge ────────────────────────────────────────────────────────────────────
interface BadgeProps {
  label: string
  color?: string
  bg?: string
}

export const Badge: React.FC<BadgeProps> = ({
  label,
  color = colors.gray600,
  bg = colors.gray100,
}) => (
  <View style={[styles.badge, { backgroundColor: bg }]}>
    <Text style={[styles.badgeText, { color }]}>{label}</Text>
  </View>
)

// ─── StatusBadge ──────────────────────────────────────────────────────────────
export const StatusBadge: React.FC<{ status: string }> = ({ status }) => (
  <Badge
    label={status.replace(/_/g, ' ')}
    color={statusColor(status)}
    bg={statusBg(status)}
  />
)

// ─── Divider ─────────────────────────────────────────────────────────────────
export const Divider: React.FC<{ style?: StyleProp<ViewStyle> }> = ({ style }) => (
  <View style={[{ height: 1, backgroundColor: colors.gray100 }, style]} />
)

// ─── SectionHeader ───────────────────────────────────────────────────────────
export const SectionHeader: React.FC<{ title: string; style?: StyleProp<ViewStyle> }> = ({
  title, style,
}) => {
  const isDark = useThemeStore((s) => s.mode === 'dark')
  const surface = getSurfaceColors(isDark)
  return (
    <Text style={[styles.sectionHeader, { color: surface.text }, style]}>{title}</Text>
  )
}

// ─── EmptyState ───────────────────────────────────────────────────────────────
export const EmptyState: React.FC<{ emoji?: string; message: string }> = ({
  emoji = '📭', message,
}) => (
  <View style={styles.empty}>
    <Text style={styles.emptyEmoji}>{emoji}</Text>
    <Text style={styles.emptyText}>{message}</Text>
  </View>
)

// ─── Skeleton ────────────────────────────────────────────────────────────────
export const Skeleton: React.FC<{ height?: number; style?: StyleProp<ViewStyle> }> = ({
  height = 60, style,
}) => {
  // Gentle pulse; completely static when the OS "reduce motion" setting is on.
  const reduced = useReducedMotion()
  const opacity = React.useRef(new Animated.Value(1)).current
  React.useEffect(() => {
    if (reduced) { opacity.setValue(1); return }
    const loop = Animated.loop(Animated.sequence([
      Animated.timing(opacity, { toValue: 0.55, duration: 700, useNativeDriver: true }),
      Animated.timing(opacity, { toValue: 1, duration: 700, useNativeDriver: true }),
    ]))
    loop.start()
    return () => loop.stop()
  }, [reduced, opacity])
  return <Animated.View accessibilityRole="progressbar" accessibilityLabel="Loading"
    style={[styles.skeleton, { height, opacity }, style]} />
}

/** Short fade/slide-in for list items; renders instantly when reduced motion is requested. */
export const FadeIn: React.FC<{ children: React.ReactNode; index?: number; style?: StyleProp<ViewStyle> }> = ({
  children, index = 0, style,
}) => {
  const reduced = useReducedMotion()
  const v = React.useRef(new Animated.Value(reduced ? 1 : 0)).current
  React.useEffect(() => {
    if (reduced) { v.setValue(1); return }
    Animated.timing(v, { toValue: 1, duration: 260, delay: Math.min(index, 8) * 40, useNativeDriver: true }).start()
  }, [reduced, v, index])
  return (
    <Animated.View style={[style, { opacity: v, transform: [{ translateY: v.interpolate({ inputRange: [0, 1], outputRange: [10, 0] }) }] }]}>
      {children}
    </Animated.View>
  )
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.white,
    borderRadius: radius.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.gray100,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 3,
    elevation: 1,
  },
  statCard: {
    flex: 1,
  },
  statHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 4,
  },
  statIcon: {
    fontSize: typography.sm,
  },
  statLabel: {
    fontSize: typography.xs,
    color: colors.gray500,
    fontWeight: '500',
  },
  statValue: {
    fontSize: typography.xl,
    fontWeight: '700',
    color: colors.gray900,
  },
  statSub: {
    fontSize: typography.xs,
    color: colors.gray400,
    marginTop: 2,
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: radius.full,
    alignSelf: 'flex-start',
  },
  badgeText: {
    fontSize: 11,
    fontWeight: '600',
    textTransform: 'capitalize',
  },
  sectionHeader: {
    fontSize: typography.lg,
    fontWeight: '700',
    color: colors.gray900,
    marginBottom: spacing.md,
  },
  empty: {
    alignItems: 'center',
    paddingVertical: 40,
  },
  emptyEmoji: {
    fontSize: 40,
    marginBottom: 12,
  },
  emptyText: {
    fontSize: typography.base,
    color: colors.gray400,
    textAlign: 'center',
  },
  skeleton: {
    backgroundColor: colors.gray100,
    borderRadius: radius.md,
    marginBottom: spacing.sm,
  },
})
