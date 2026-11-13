import { computed, ref, type Ref } from 'vue'
import { estimateSeries, monthLabels } from './useCountUp'

export interface MonthPoint { month: string; amount: number }

const shortMonth = (ym: string) => new Date(`${ym}-01T00:00:00`).toLocaleDateString('en-KE', { month: 'short' })

/**
 * Range-switchable (3 / 6 / 9 months) trend + the selected-bar read-out used by the dashboards.
 * Pass `history` (real month-by-month figures from the API, oldest first) to show actual data;
 * without it the chart falls back to an estimated shape built from the current figure.
 */
export function useTrend(current: Ref<number> | (() => number), growth = 0.06, initial = 6, history?: () => MonthPoint[] | undefined | null) {
  const get = typeof current === 'function' ? current : () => current.value
  const range = ref(initial)
  const ranges = [{ label: '3 mo', value: 3 }, { label: '6 mo', value: 6 }, { label: '9 mo', value: 9 }]
  const real = computed(() => { const h = history?.(); return h && h.length ? h : null })
  const isReal = computed(() => !!real.value)
  const labels = computed(() => real.value ? real.value.slice(-range.value).map((p) => shortMonth(p.month)) : monthLabels(range.value))
  const values = computed(() => real.value ? real.value.slice(-range.value).map((p) => p.amount) : estimateSeries(get(), range.value, growth))
  const sel = ref(range.value - 1)
  const selected = computed(() => Math.min(sel.value, values.value.length - 1))
  const selValue = computed(() => values.value[selected.value] ?? 0)
  const delta = computed(() => {
    const i = selected.value
    if (i <= 0 || !values.value[i - 1]) return 0
    return Math.round(((values.value[i] - values.value[i - 1]) / values.value[i - 1]) * 100)
  })
  function setRange(v: number) { range.value = v; sel.value = v - 1 }
  return { range, ranges, labels, values, sel, selected, selValue, delta, setRange, isReal }
}
