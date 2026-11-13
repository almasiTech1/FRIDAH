import { create } from 'zustand'
import { notificationsApi } from '@/api/services'
import type { Notification } from '@/types'

interface NotifState {
  notifications: Notification[]
  unreadCount: number
  fetchNotifications: () => Promise<void>
  fetchUnreadCount: () => Promise<void>
  markRead: (id: string) => Promise<void>
  markAllRead: () => Promise<void>
}

export const useNotificationsStore = create<NotifState>((set, get) => ({
  notifications: [],
  unreadCount: 0,

  fetchNotifications: async () => {
    try {
      const { data } = await notificationsApi.list()
      const items = data.data?.results || data.data || []
      set({ notifications: items })
    } catch {}
  },

  fetchUnreadCount: async () => {
    try {
      const { data } = await notificationsApi.unreadCount()
      set({ unreadCount: data.data?.unread_count ?? 0 })
    } catch {}
  },

  markRead: async (id) => {
    try {
      await notificationsApi.markRead(id)
      set(state => ({
        notifications: state.notifications.map(n =>
          n.id === id ? { ...n, is_read: true } : n,
        ),
        unreadCount: Math.max(0, state.unreadCount - 1),
      }))
    } catch {}
  },

  markAllRead: async () => {
    try {
      await notificationsApi.markAllRead()
      set(state => ({
        notifications: state.notifications.map(n => ({ ...n, is_read: true })),
        unreadCount: 0,
      }))
    } catch {}
  },
}))
