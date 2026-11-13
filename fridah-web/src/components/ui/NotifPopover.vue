<template>
  <div ref="root" class="fx-pop-wrap">
    <button class="fx-icon-btn" aria-label="Notifications" :aria-expanded="open" @click="toggle">
      <Bell /><span v-if="store.unreadCount > 0" class="fx-dot">{{ store.unreadCount > 9 ? '9+' : store.unreadCount }}</span>
    </button>
    <div v-if="open" class="fx-pop">
      <div class="flex items-center justify-between pr-2"><h4>Notifications</h4>
        <button v-if="store.unreadCount" class="fx-link" @click="markAll">Mark all read</button></div>
      <p v-if="loading" class="p-5 text-sm text-center" style="color:var(--muted)">Loading…</p>
      <p v-else-if="!recent.length" class="p-6 text-sm text-center" style="color:var(--muted)">You're all caught up 🎉</p>
      <button v-for="n in recent" :key="n.id" class="fx-pop-item" @click="read(n)">
        <span class="fx-ico"><Bell /></span>
        <span class="min-w-0 flex-1"><b class="block truncate" :style="n.is_read ? 'font-weight:600;opacity:.7' : 'font-weight:800'">{{ n.title }}</b><small class="truncate block">{{ n.message || n.body }}</small></span>
        <i v-if="!n.is_read" style="width:8px;height:8px;border-radius:50%;background:var(--accent);flex-shrink:0" />
      </button>
      <button v-if="route" class="fx-pop-item" style="justify-content:center;font-weight:700;color:var(--link)" @click="go">View all notifications</button>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { onClickOutside } from '@vueuse/core'
import { Bell } from 'lucide-vue-next'
import { useNotificationsStore } from '@/stores/notifications'
const props = defineProps<{ route?: string }>()
const store = useNotificationsStore(); const router = useRouter()
const open = ref(false); const loading = ref(false); const root = ref<HTMLElement>()
onClickOutside(root, () => (open.value = false))
const recent = computed<any[]>(() => store.notifications.slice(0, 5))
async function toggle() {
  open.value = !open.value
  if (open.value) { loading.value = true; try { await store.fetchNotifications() } catch { /* offline: show whatever we have */ } finally { loading.value = false } }
}
async function read(n: any) { try { if (!n.is_read) await store.markRead(n.id) } catch { /* ignore */ } }
async function markAll() { try { await store.markAllRead() } catch { /* ignore */ } }
function go() { open.value = false; if (props.route) router.push(props.route) }
</script>
