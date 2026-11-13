import React from 'react'
import { View } from 'react-native'
import { RefundsQueue } from '@/components/common/RefundsQueue'
import { colors, getTheme } from '@/theme'

export const AdminRefundsScreen: React.FC = () => (
  <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
    <RefundsQueue admin canRequest color={getTheme('admin').primary} />
  </View>
)
