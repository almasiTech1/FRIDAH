import React from 'react'
import {
  TouchableOpacity,
  Text,
  ActivityIndicator,
  StyleSheet,
  ViewStyle,
  TextStyle,
} from 'react-native'
import { colors, radius, typography } from '@/theme'

interface Props {
  label: string
  onPress: () => void
  color?: string
  variant?: 'solid' | 'outline' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  disabled?: boolean
  style?: ViewStyle
  textStyle?: TextStyle
  fullWidth?: boolean
}

export const Button: React.FC<Props> = ({
  label, onPress, color = colors.gray900,
  variant = 'solid', size = 'md',
  loading = false, disabled = false,
  style, textStyle, fullWidth = false,
}) => {
  const pad = { sm: 8, md: 13, lg: 16 }[size]
  const fontSize = { sm: typography.sm, md: typography.base, lg: typography.lg }[size]

  const containerStyle: ViewStyle = {
    paddingVertical: pad,
    paddingHorizontal: pad! * 2,
    borderRadius: radius.lg,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
    opacity: disabled || loading ? 0.5 : 1,
    alignSelf: fullWidth ? 'stretch' : 'flex-start',
    ...(variant === 'solid' ? { backgroundColor: color } :
      variant === 'outline' ? { borderWidth: 1.5, borderColor: color, backgroundColor: 'transparent' } :
        { backgroundColor: 'transparent' }),
    ...style,
  }

  const labelColor =
    variant === 'solid' ? colors.white :
      variant === 'outline' ? color : color

  return (
    <TouchableOpacity
      style={containerStyle}
      onPress={onPress}
      disabled={disabled || loading}
      activeOpacity={0.75}
    >
      {loading
        ? <ActivityIndicator size="small" color={labelColor} />
        : <Text style={[{ color: labelColor, fontSize, fontWeight: '600' }, textStyle]}>{label}</Text>
      }
    </TouchableOpacity>
  )
}
