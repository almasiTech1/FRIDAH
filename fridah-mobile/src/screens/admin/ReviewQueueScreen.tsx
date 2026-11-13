import React from 'react'
import { View } from 'react-native'
import { PropertyReviewQueue } from '@/components/common/PropertyReviewQueue'
import { colors, getTheme } from '@/theme'

export const AdminReviewQueueScreen: React.FC = () => (
  <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
    <PropertyReviewQueue role="admin" color={getTheme('admin').primary} />
  </View>
)
