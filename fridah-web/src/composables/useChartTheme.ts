import { computed } from 'vue'
import { useSkinStore } from '@/stores/skin'

/** Reads the active skin's CSS variables so Chart.js colours follow the dashboard look. */
export function useChartTheme() {
  const skin = useSkinStore()
  return computed(() => {
    void skin.id
    const cs = typeof document !== 'undefined' ? getComputedStyle(document.documentElement) : null
    const v = (n: string, fb: string) => (cs?.getPropertyValue(n).trim() || fb)
    const resolve = (n: string, fb: string) => {
      const raw = v(n, fb)
      if (!raw.startsWith('var(') || !cs) return raw
      return v(raw.slice(4, -1).trim(), fb)
    }
    return {
      muted: v('--muted', '#9ca3af'), text: v('--text-2', '#374151'), grid: v('--border', '#f3f4f6'),
      palette: [resolve('--c1', '#6366f1'), resolve('--c2', '#10b981'), resolve('--c3', '#f59e0b'), resolve('--c4', '#ef4444'), resolve('--c5', '#8b5cf6'), '#0ea5e9', '#f97316', '#14b8a6'],
      tipBg: v('--pop-bg', '#111827'), tipText: v('--text', '#fff'), track: v('--surface-soft', '#e5e7eb'),
    }
  })
}
