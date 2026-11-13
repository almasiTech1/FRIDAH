import React from 'react'
import { ChatScreen } from '@/screens/shared/ChatScreen'
import { getTheme } from '@/theme'

export const HotelMessagesScreen: React.FC = () => <ChatScreen theme={getTheme('hotel_owner')} />
