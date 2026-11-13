import { ref, watch, onMounted, onBeforeUnmount, type Ref } from 'vue'

/** Animates a number towards `target` (ease-out cubic). Respects reduced-motion. */
export function useCountUp(target: Ref<number> | (() => number), duration = 900) {
  const get = typeof target === 'function' ? target : () => target.value
  const shown = ref(0)
  let raf = 0
  const reduce = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  function run(to: number) {
    cancelAnimationFrame(raf)
    if (reduce || !Number.isFinite(to)) { shown.value = to; return }
    const from = shown.value, t0 = performance.now()
    const step = (now: number) => {
      const p = Math.min((now - t0) / duration, 1)
      shown.value = Math.round(from + (to - from) * (1 - Math.pow(1 - p, 3)))
      if (p < 1) raf = requestAnimationFrame(step); else shown.value = to
    }
    raf = requestAnimationFrame(step)
  }
  onMounted(() => run(get()))
  watch(get, run)
  onBeforeUnmount(() => cancelAnimationFrame(raf))
  return shown
}

/**
 * Deterministic "shape" for an estimated trend. The dashboards only receive month totals from the API,
 * so charts that span several months are shaped from the current figure and labelled "estimated".
 */
export function estimateSeries(current: number, points: number, growth = 0.06): number[] {
  const wave = [0.92, 1.04, 0.97, 1.08, 1.0, 1.12, 1.03, 1.15, 1.06, 1.18, 1.09, 1.2]
  return Array.from({ length: points }, (_, i) => {
    const back = points - 1 - i
    return Math.max(0, Math.round(current / Math.pow(1 + growth, back) * wave[(i + 3) % wave.length] / wave[(points + 2) % wave.length]))
  })
}

export function monthLabels(n: number): string[] {
  const out: string[] = []
  const d = new Date()
  for (let i = n - 1; i >= 0; i--) out.push(new Date(d.getFullYear(), d.getMonth() - i, 1).toLocaleDateString('en-KE', { month: 'short' }))
  return out
}

export const compactKES = (n: number) => n >= 1e6 ? `KES ${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `KES ${Math.round(n / 1e3)}K` : `KES ${n}`
