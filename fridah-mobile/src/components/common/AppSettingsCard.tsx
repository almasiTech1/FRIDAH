import React from 'react'
import { View, Text, Switch, TouchableOpacity, StyleSheet } from 'react-native'
import { useTranslation } from 'react-i18next'
import { Card, SectionHeader } from './Cards'
import { useThemeStore } from '@/stores/themeStore'
import { setAppLocale } from '@/i18n'
import { colors, radius, spacing, typography, getSurfaceColors } from '@/theme'

export const AppSettingsCard: React.FC<{ accentColor: string }> = ({ accentColor }) => {
  const { t, i18n } = useTranslation()
  const { mode, toggle } = useThemeStore()
  const isDark = mode === 'dark'
  const surface = getSurfaceColors(isDark)

  return (
    <Card style={styles.card}>
      <SectionHeader title={t('settings.title')} />

      <View style={styles.row}>
        <Text style={[styles.label, { color: surface.text }]}>{t('settings.darkMode')}</Text>
        <Switch
          value={isDark}
          onValueChange={toggle}
          trackColor={{ false: colors.gray200, true: accentColor }}
          thumbColor={colors.white}
        />
      </View>

      <Text style={[styles.label, { color: surface.text, marginBottom: 8 }]}>{t('settings.language')}</Text>
      <View style={styles.langRow}>
        <TouchableOpacity
          style={[
            styles.langBtn,
            { borderColor: surface.border },
            i18n.language === 'en' && { backgroundColor: accentColor, borderColor: accentColor },
          ]}
          onPress={() => setAppLocale('en')}
        >
          <Text style={[styles.langText, i18n.language === 'en' ? { color: colors.white } : { color: surface.text }]}>
            {t('settings.english')}
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[
            styles.langBtn,
            { borderColor: surface.border },
            i18n.language === 'sw' && { backgroundColor: accentColor, borderColor: accentColor },
          ]}
          onPress={() => setAppLocale('sw')}
        >
          <Text style={[styles.langText, i18n.language === 'sw' ? { color: colors.white } : { color: surface.text }]}>
            {t('settings.swahili')}
          </Text>
        </TouchableOpacity>
      </View>
    </Card>
  )
}

const styles = StyleSheet.create({
  card: { padding: spacing.lg },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  label: { fontSize: typography.sm, fontWeight: '600' },
  langRow: { flexDirection: 'row', gap: 10 },
  langBtn: { flex: 1, borderWidth: 1.5, borderRadius: radius.md, paddingVertical: 10, alignItems: 'center' },
  langText: { fontSize: typography.sm, fontWeight: '600' },
})
