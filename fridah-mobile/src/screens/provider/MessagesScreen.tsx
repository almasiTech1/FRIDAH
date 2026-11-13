import React from 'react'
import { ChatScreen } from '@/screens/shared/ChatScreen'
import { getTheme } from '@/theme'

export const ProviderMessagesScreen: React.FC = () => <ChatScreen theme={getTheme('service_provider')} />
