import React from 'react'
import { ChatScreen } from '@/screens/shared/ChatScreen'
import { agencyTheme } from '@/theme'

export const AgencyMessagesScreen: React.FC = () => <ChatScreen theme={agencyTheme} canCreateGroups />
