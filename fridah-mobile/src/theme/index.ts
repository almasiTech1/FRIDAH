import { Role } from '@/types'

export interface PortalTheme {
  primary: string
  primaryDark: string
  primaryLight: string
  primaryBg: string
  label: string
  emoji: string
}

export const themes: Record<Role, PortalTheme> = {
  tenant: {
    primary: '#10b981',
    primaryDark: '#047857',
    primaryLight: '#d1fae5',
    primaryBg: '#ecfdf5',
    label: 'Tenant Portal',
    emoji: '🏠',
  },
  landlord: {
    primary: '#6366f1',
    primaryDark: '#4338ca',
    primaryLight: '#e0e7ff',
    primaryBg: '#eef2ff',
    label: 'Landlord Portal',
    emoji: '🏗️',
  },
  admin: {
    primary: '#8b5cf6',
    primaryDark: '#6d28d9',
    primaryLight: '#ede9fe',
    primaryBg: '#f5f3ff',
    label: 'Admin Portal',
    emoji: '⚙️',
  },
  service_provider: {
    primary: '#f97316',
    primaryDark: '#c2410c',
    primaryLight: '#ffedd5',
    primaryBg: '#fff7ed',
    label: 'Service Provider',
    emoji: '🔧',
  },
  hotel_owner: {
    primary: '#f59e0b',
    primaryDark: '#b45309',
    primaryLight: '#fef3c7',
    primaryBg: '#fffbeb',
    label: 'Hotel / BnB',
    emoji: '🏨',
  },
}

export const agencyTheme: PortalTheme = {
  primary: '#0ea5e9',
  primaryDark: '#0369a1',
  primaryLight: '#e0f2fe',
  primaryBg: '#f0f9ff',
  label: 'Agency Portal',
  emoji: '🏢',
}

export const colors = {
  white: '#ffffff',
  black: '#000000',
  gray50: '#f9fafb',
  gray100: '#f3f4f6',
  gray200: '#e5e7eb',
  gray300: '#d1d5db',
  gray400: '#9ca3af',
  gray500: '#6b7280',
  gray600: '#4b5563',
  gray700: '#374151',
  gray800: '#1f2937',
  gray900: '#111827',
  red500: '#ef4444',
  red600: '#dc2626',
  red100: '#fee2e2',
  green500: '#22c55e',
  green600: '#16a34a',
  green100: '#dcfce7',
  yellow500: '#eab308',
  yellow100: '#fef9c3',
  blue500: '#3b82f6',
  blue100: '#dbeafe',
}

// Semantic surface colors that flip between light/dark mode. Screen-level styling
// still largely uses the static `colors` palette above (RN's StyleSheet is static,
// unlike CSS variables on web), but shared components (Card, StatCard, Badge, nav
// chrome, splash) read from this so the most-reused UI responds to the toggle.
export interface SurfaceColors {
  background: string
  surface: string
  surfaceAlt: string
  border: string
  text: string
  textMuted: string
}

export const lightSurface: SurfaceColors = {
  background: colors.gray50,
  surface: colors.white,
  surfaceAlt: colors.gray100,
  border: colors.gray100,
  text: colors.gray900,
  textMuted: colors.gray500,
}

export const darkSurface: SurfaceColors = {
  background: '#0a0e17',
  surface: '#161b26',
  surfaceAlt: '#1f2530',
  border: '#262d3a',
  text: '#f3f4f6',
  textMuted: '#9099ab',
}

export function getSurfaceColors(isDark: boolean): SurfaceColors {
  return isDark ? darkSurface : lightSurface
}

export const typography = {
  xs: 11,
  sm: 13,
  base: 15,
  lg: 17,
  xl: 20,
  xxl: 24,
  xxxl: 30,
}

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  xxxl: 32,
}

export const radius = {
  sm: 6,
  md: 10,
  lg: 14,
  xl: 20,
  full: 9999,
}

export function getTheme(role?: Role): PortalTheme {
  return themes[role || 'tenant']
}
