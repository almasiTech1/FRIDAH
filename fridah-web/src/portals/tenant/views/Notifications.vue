<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="page-title">Notifications</h1>
      <button v-if="store.unreadCount > 0" class="btn-outline border-gray-200 text-sm" @click="store.markAllRead()">Mark all read</button>
    </div>
    <div class="card divide-y divide-gray-50">
      <div v-if="loading" class="p-8 text-center text-gray-400">Loading…</div>
      <div v-else-if="!store.notifications.length" class="p-10 text-center text-gray-400">No notifications yet.</div>
      <div v-else v-for="n in store.notifications" :key="n.id"
        :class="['flex gap-4 p-4 cursor-pointer hover:bg-gray-50 transition-colors', !n.is_read && 'bg-tenant-50']"
        @click="store.markRead(n.id)">
        <div :class="['w-2 h-2 rounded-full mt-2 flex-shrink-0', !n.is_read ? 'bg-tenant-600' : 'bg-gray-200']"/>
        <div class="flex-1">
          <p class="text-sm font-medium text-gray-900">{{ n.title }}</p>
          <p class="text-xs text-gray-500 mt-0.5">{{ n.message }}</p>
          <p class="text-xs text-gray-400 mt-1">{{ relativeTime(n.created_at) }}</p>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useNotificationsStore } from '@/stores/notifications'
import { relativeTime } from '@/utils/formatters'
const store = useNotificationsStore()
const loading = ref(true)
onMounted(async () => { await store.fetchNotifications(); loading.value = false })
</script>
