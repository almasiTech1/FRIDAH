import React from 'react'
import { ChatScreen } from '@/screens/shared/ChatScreen'
import { getTheme } from '@/theme'

export const LandlordMessagesScreen: React.FC = () => <ChatScreen theme={getTheme('landlord')} canCreateGroups />
