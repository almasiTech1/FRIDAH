import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Toast { id: number; title: string; body?: string; tone: 'ok' | 'info' | 'warn' | 'error' }

export const useToastStore = defineStore('toasts', () => {
  const items = ref<Toast[]>([])
  let n = 0
  function push(title: string, opts: { body?: string; tone?: Toast['tone']; ms?: number } = {}) {
    const id = ++n
    items.value.push({ id, title, body: opts.body, tone: opts.tone ?? 'ok' })
    setTimeout(() => dismiss(id), opts.ms ?? 3200)
  }
  function dismiss(id: number) { items.value = items.value.filter((t) => t.id !== id) }
  return { items, push, dismiss }
})
