import { defineStore } from 'pinia'
import { ref } from 'vue'
import { notificationsApi } from '@/api/services'
import type { Notification } from '@/types'

export const useNotificationsStore = defineStore('notifications', () => {
  const notifications = ref<Notification[]>([])
  const unreadCount = ref(0)

  async function fetchNotifications() {
    const { data } = await notificationsApi.list()
    notifications.value = data.data?.results || data.data || []
  }

  async function fetchUnreadCount() {
    const { data } = await notificationsApi.unreadCount()
    unreadCount.value = data.data?.unread_count ?? 0
  }

  async function markRead(id: string) {
    await notificationsApi.markRead(id)
    const n = notifications.value.find(n => n.id === id)
    if (n) { n.is_read = true; unreadCount.value = Math.max(0, unreadCount.value - 1) }
  }

  async function markAllRead() {
    await notificationsApi.markAllRead()
    notifications.value.forEach(n => n.is_read = true)
    unreadCount.value = 0
  }

  return { notifications, unreadCount, fetchNotifications, fetchUnreadCount, markRead, markAllRead }
})
