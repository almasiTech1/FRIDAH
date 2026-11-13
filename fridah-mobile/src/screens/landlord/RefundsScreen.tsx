import React from 'react'
import { View } from 'react-native'
import { RefundsQueue } from '@/components/common/RefundsQueue'
import { colors, getTheme } from '@/theme'

export const LandlordRefundsScreen: React.FC = () => (
  <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
    <RefundsQueue canRequest color={getTheme('landlord').primary} />
  </View>
)
