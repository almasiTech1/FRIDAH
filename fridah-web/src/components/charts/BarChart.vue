<template>
  <div class="chart-wrap" :style="`height:${height}px`">
    <Bar v-if="hasData" :data="chartData" :options="mergedOptions" />
    <div v-else class="chart-empty">No data yet</div>
  </div>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'
import '@/components/charts/register'
import { useChartTheme } from '@/composables/useChartTheme'

interface Series { label: string; values: number[]; color?: string }

const props = withDefaults(defineProps<{
  labels: string[]
  series: Series[]
  height?: number
  currency?: boolean
  horizontal?: boolean
  stacked?: boolean
}>(), { height: 240, currency: false, horizontal: false, stacked: false })

const theme = useChartTheme()

const hasData = computed(() => props.series.some((s) => s.values.some((v) => v > 0)))

const chartData = computed(() => ({
  labels: props.labels,
  datasets: props.series.map((s, i) => ({
    label: s.label,
    data: s.values,
    backgroundColor: s.color || theme.value.palette[i % theme.value.palette.length],
    borderRadius: 10,
    borderSkipped: false as const,
    maxBarThickness: 36,
  })),
}))

const mergedOptions = computed(() => ({
  animation: { duration: 700, easing: 'easeOutQuart' as const },
  responsive: true,
  maintainAspectRatio: false,
  indexAxis: props.horizontal ? ('y' as const) : ('x' as const),
  plugins: {
    legend: { display: props.series.length > 1, position: 'bottom' as const, labels: { boxWidth: 10, font: { size: 11 }, color: theme.value.text } },
    tooltip: {
      padding: 12,
      cornerRadius: 12,
      backgroundColor: theme.value.tipBg,
      titleColor: theme.value.tipText,
      bodyColor: theme.value.tipText,
      borderColor: theme.value.grid,
      borderWidth: 1,
      callbacks: props.currency ? {
        label: (ctx: any) => `${ctx.dataset.label}: KES ${Number(ctx.parsed[props.horizontal ? 'x' : 'y']).toLocaleString()}`,
      } : undefined,
    },
  },
  scales: {
    x: { stacked: props.stacked, grid: { display: false }, border: { display: false }, ticks: { color: theme.value.muted } },
    y: {
      stacked: props.stacked,
      grid: { color: theme.value.grid },
      border: { display: false },
      ticks: { color: theme.value.muted, ...(props.currency && !props.horizontal ? { callback: (v: any) => `${Number(v) / 1000}k` } : {}) },
    },
  },
}))
</script>
<style scoped>
.chart-wrap { position: relative; width: 100%; }
.chart-empty { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--muted, #9ca3af); font-size: 0.875rem; }
</style>
