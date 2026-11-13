<template>
  <Teleport to="body">
    <div v-if="modelValue" class="fx-cmdk-overlay" @mousedown.self="close">
      <div class="fx-cmdk" role="dialog" aria-modal="true" aria-label="Command palette" @keydown="onKey">
        <input ref="input" v-model="q" placeholder="Search pages, switch skins, run actions…" autocomplete="off" spellcheck="false" />
        <div ref="list" class="fx-cmdk-list">
          <template v-for="g in grouped" :key="g.name">
            <h4 class="fx-pop" style="all:unset;display:block;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);padding:10px 12px 4px;font-weight:800">{{ g.name }}</h4>
            <button v-for="it in g.items" :key="it.id" :data-i="it.idx" class="fx-pop-item" :class="{ sel: it.idx === cursor }" @mousemove="cursor = it.idx" @click="run(it)">
              <span class="fx-ico"><component :is="it.icon" /></span>
              <span class="min-w-0 flex-1"><b class="block truncate font-semibold">{{ it.label }}</b><small v-if="it.hint">{{ it.hint }}</small></span>
              <span v-if="it.idx === cursor" class="fx-kbd">↵</span>
            </button>
          </template>
          <p v-if="!flat.length" class="p-6 text-center text-sm" style="color:var(--muted)">No matches for “{{ q }}”</p>
        </div>
        <div class="fx-cmdk-foot"><span><kbd>↑</kbd> <kbd>↓</kbd> navigate</span><span><kbd>↵</kbd> select</span><span><kbd>esc</kbd> close</span></div>
      </div>
    </div>
  </Teleport>
</template>
<script setup lang="ts">
import { computed, nextTick, ref, watch, type Component } from 'vue'
import { useRouter } from 'vue-router'
import { Compass, Palette, PanelLeft, Sun, LogOut, ImageOff, Bell } from 'lucide-vue-next'
import { SKINS, useSkinStore } from '@/stores/skin'
import { useToastStore } from '@/stores/toasts'
import { useAuthStore } from '@/stores/auth'

interface Item { id: string; group: string; label: string; hint?: string; icon: Component; run: () => void; idx: number }
const props = defineProps<{ modelValue: boolean; navItems: { to: string; label: string; icon: any }[]; notifRoute?: string }>()
const emit = defineEmits<{ 'update:modelValue': [v: boolean] }>()
const router = useRouter(); const skin = useSkinStore(); const toast = useToastStore(); const auth = useAuthStore()
const q = ref(''); const cursor = ref(0); const input = ref<HTMLInputElement>(); const list = ref<HTMLElement>()

const close = () => emit('update:modelValue', false)
const base = computed(() => {
  const items: Omit<Item, 'idx'>[] = [
    ...props.navItems.map((n) => ({ id: `go:${n.to}`, group: 'Go to', label: n.label, hint: n.to, icon: n.icon, run: () => router.push(n.to) })),
    ...SKINS.map((s) => ({ id: `skin:${s.id}`, group: 'Appearance', label: `Skin · ${s.name}`, hint: s.blurb, icon: Palette, run: () => { skin.set(s.id); toast.push(`${s.name} applied`, { tone: 'info' }) } })),
    { id: 'a:mode', group: 'Actions', label: skin.isDark ? 'Switch to a light skin' : 'Switch to a dark skin', icon: Sun, run: () => skin.toggleMode() },
    { id: 'a:side', group: 'Actions', label: 'Collapse / expand sidebar', icon: PanelLeft, run: () => skin.toggleCollapsed() },
    ...(skin.wallpaper ? [{ id: 'a:wall', group: 'Actions', label: 'Remove custom wallpaper', icon: ImageOff, run: () => skin.setWallpaper(null) }] : []),
    ...(props.notifRoute ? [{ id: 'a:notif', group: 'Actions', label: 'Open notifications', icon: Bell, run: () => router.push(props.notifRoute!) }] : []),
    { id: 'a:out', group: 'Actions', label: 'Sign out', icon: LogOut, run: async () => { await auth.logout(); router.push('/login') } },
  ]
  return items
})
const flat = computed<Item[]>(() => {
  const s = q.value.trim().toLowerCase()
  const f = base.value.filter((i) => !s || `${i.label} ${i.hint || ''} ${i.group}`.toLowerCase().includes(s))
  return f.map((i, idx) => ({ ...i, idx })) as Item[]
})
const grouped = computed(() => {
  const m = new Map<string, Item[]>()
  flat.value.forEach((i) => m.set(i.group, [...(m.get(i.group) || []), i]))
  return [...m].map(([name, items]) => ({ name, items }))
})
watch(q, () => (cursor.value = 0))
watch(() => props.modelValue, async (o) => { if (o) { q.value = ''; cursor.value = 0; await nextTick(); input.value?.focus() } })
function run(it: Item) { close(); it.run() }
async function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') { e.preventDefault(); close() }
  else if (e.key === 'ArrowDown') { e.preventDefault(); cursor.value = (cursor.value + 1) % Math.max(1, flat.value.length); await scroll() }
  else if (e.key === 'ArrowUp') { e.preventDefault(); cursor.value = (cursor.value - 1 + flat.value.length) % Math.max(1, flat.value.length); await scroll() }
  else if (e.key === 'Enter') { e.preventDefault(); const it = flat.value[cursor.value]; if (it) run(it) }
}
async function scroll() { await nextTick(); list.value?.querySelector(`[data-i="${cursor.value}"]`)?.scrollIntoView({ block: 'nearest' }) }
void Compass
</script>
