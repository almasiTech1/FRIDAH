<template>
  <div class="space-y-2">
    <div class="flex items-center justify-between mb-1">
      <span class="text-xs font-bold opacity-70">{{ doneCount }}/{{ tasks.length }} done</span>
      <div class="fx-track w-24"><i :style="`width:${tasks.length ? (doneCount / tasks.length) * 100 : 0}%`" /></div>
    </div>
    <button v-for="t in tasks" :key="t.id" class="fx-task" :class="{ done: t.done }" @click="toggle(t)">
      <span class="fx-checkbox">✓</span>
      <span class="min-w-0 flex-1"><span class="t block truncate font-semibold">{{ t.title }}</span><small v-if="t.meta">{{ t.meta }}</small></span>
      <RouterLink v-if="t.to" :to="t.to" class="fx-kbd" @click.stop>Open</RouterLink>
    </button>
    <p v-if="!tasks.length" class="text-sm opacity-60 py-4 text-center">Nothing to do — enjoy the calm ✨</p>
  </div>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useToastStore } from '@/stores/toasts'
export interface TaskItem { id: string; title: string; meta?: string; to?: string; done?: boolean }
const props = defineProps<{ items: TaskItem[] }>()
const toast = useToastStore()
const tasks = ref<TaskItem[]>(props.items.map((t) => ({ ...t })))
watch(() => props.items, (v) => { tasks.value = v.map((t) => ({ ...t, done: tasks.value.find((x) => x.id === t.id)?.done ?? t.done })) })
const doneCount = computed(() => tasks.value.filter((t) => t.done).length)
function toggle(t: TaskItem) {
  t.done = !t.done
  if (t.done && doneCount.value === tasks.value.length) toast.push('All caught up', { body: 'Every task on your list is ticked off.' })
}
</script>
