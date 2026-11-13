import React from 'react'
import { View } from 'react-native'
import { PropertyReviewQueue } from '@/components/common/PropertyReviewQueue'
import { colors } from '@/theme'
import { getTheme } from '@/theme'

export const LandlordApprovalsScreen: React.FC = () => (
  <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
    <PropertyReviewQueue role="landlord" color={getTheme('landlord').primary} />
  </View>
)
