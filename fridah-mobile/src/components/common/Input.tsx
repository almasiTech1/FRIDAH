import React, { useState } from 'react'
import { View, Text, TextInput, TextInputProps, StyleSheet, ViewStyle } from 'react-native'
import { colors, radius, typography } from '@/theme'

interface Props extends TextInputProps {
  label?: string
  error?: string
  containerStyle?: ViewStyle
  accentColor?: string
}

export const Input: React.FC<Props> = ({
  label, error, containerStyle, accentColor = colors.gray900, ...props
}) => {
  const [focused, setFocused] = useState(false)

  return (
    <View style={[styles.container, containerStyle]}>
      {label && <Text style={styles.label}>{label}</Text>}
      <TextInput
        style={[
          styles.input,
          focused && { borderColor: accentColor },
          error && { borderColor: colors.red500 },
        ]}
        placeholderTextColor={colors.gray400}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        {...props}
      />
      {error && <Text style={styles.error}>{error}</Text>}
    </View>
  )
}

const styles = StyleSheet.create({
  container: { marginBottom: 14 },
  label: {
    fontSize: typography.sm,
    fontWeight: '500',
    color: colors.gray700,
    marginBottom: 6,
  },
  input: {
    borderWidth: 1.5,
    borderColor: colors.gray200,
    borderRadius: radius.md,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: typography.base,
    color: colors.gray900,
    backgroundColor: colors.white,
  },
  error: {
    fontSize: typography.xs,
    color: colors.red500,
    marginTop: 4,
  },
})
