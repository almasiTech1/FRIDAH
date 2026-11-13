import React from 'react'
import { ChatScreen } from '@/screens/shared/ChatScreen'
import { getTheme } from '@/theme'

export const TenantMessagesScreen: React.FC = () => <ChatScreen theme={getTheme('tenant')} />
