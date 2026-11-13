<template>
  <svg class="fx-spark" :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="none" aria-hidden="true">
    <defs>
      <linearGradient :id="gid" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" :stop-color="color" stop-opacity=".38" /><stop offset="100%" :stop-color="color" stop-opacity="0" />
      </linearGradient>
    </defs>
    <path :d="area" :fill="`url(#${gid})`" />
    <path :d="line" fill="none" :stroke="color" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke" class="spark-line" />
  </svg>
</template>
<script setup lang="ts">
import { computed } from 'vue'
const props = withDefaults(defineProps<{ values: number[]; color?: string }>(), { color: 'var(--accent)' })
const W = 120, H = 36
const gid = `sg${Math.random().toString(36).slice(2, 8)}`
const pts = computed(() => {
  const v = props.values.length > 1 ? props.values : [0, ...props.values, 0]
  const min = Math.min(...v), max = Math.max(...v), span = max - min || 1
  return v.map((n, i) => [i * (W / (v.length - 1)), H - 4 - ((n - min) / span) * (H - 8)] as [number, number])
})
const line = computed(() => pts.value.reduce((d, [x, y], i, a) => {
  if (!i) return `M${x},${y}`
  const [px, py] = a[i - 1], cx = (px + x) / 2
  return `${d} C${cx},${py} ${cx},${y} ${x},${y}`
}, ''))
const area = computed(() => `${line.value} L${W},${H} L0,${H} Z`)
</script>
<style scoped>
.spark-line { stroke-dasharray: 400; stroke-dashoffset: 400; animation: draw 1.2s .1s ease forwards; }
@keyframes draw { to { stroke-dashoffset: 0; } }
@media (prefers-reduced-motion: reduce) { .spark-line { animation: none; stroke-dashoffset: 0; } }
</style>
