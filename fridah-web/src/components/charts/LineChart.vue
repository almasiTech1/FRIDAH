<template>
  <div class="chart-wrap" :style="`height:${height}px`">
    <Line v-if="hasData" :data="chartData" :options="mergedOptions" />
    <div v-else class="chart-empty">No data yet</div>
  </div>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import '@/components/charts/register'
import { useChartTheme } from '@/composables/useChartTheme'

interface Series { label: string; values: number[]; color?: string; dashed?: boolean }

const props = withDefaults(defineProps<{
  labels: string[]
  series: Series[]
  height?: number
  currency?: boolean
}>(), { height: 240, currency: false })

const theme = useChartTheme()

const hasData = computed(() => props.series.some((s) => s.values.some((v) => v > 0)))

const chartData = computed(() => ({
  labels: props.labels,
  datasets: props.series.map((s, i) => {
    const color = s.color || theme.value.palette[i % theme.value.palette.length]
    return {
      label: s.label,
      data: s.values,
      borderColor: color,
      backgroundColor: color.startsWith('#') ? color + '26' : color,
      borderDash: s.dashed ? [6, 4] : undefined,
      fill: true,
      tension: 0.35,
      pointRadius: 3,
      pointBackgroundColor: color,
    }
  }),
}))

const mergedOptions = computed(() => ({
  animation: { duration: 800, easing: 'easeOutQuart' as const },
  interaction: { mode: 'index' as const, intersect: false },
  responsive: true,
  maintainAspectRatio: false,
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
        label: (ctx: any) => `${ctx.dataset.label}: KES ${Number(ctx.parsed.y).toLocaleString()}`,
      } : undefined,
    },
  },
  scales: {
    x: { grid: { display: false }, border: { display: false }, ticks: { color: theme.value.muted } },
    y: {
      grid: { color: theme.value.grid },
      border: { display: false },
      ticks: { color: theme.value.muted, ...(props.currency ? { callback: (v: any) => `${Number(v) / 1000}k` } : {}) },
    },
  },
}))
</script>
<style scoped>
.chart-wrap { position: relative; width: 100%; }
.chart-empty { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--muted, #9ca3af); font-size: 0.875rem; }
</style>
