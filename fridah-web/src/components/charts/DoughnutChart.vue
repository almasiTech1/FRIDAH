<template>
  <div class="chart-wrap" :style="`height:${height}px`">
    <Doughnut v-if="hasData" :data="chartData" :options="options" />
    <div v-else class="chart-empty">No data yet</div>
  </div>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { Doughnut } from 'vue-chartjs'
import '@/components/charts/register'
import { useChartTheme } from '@/composables/useChartTheme'

const props = withDefaults(defineProps<{
  labels: string[]
  values: number[]
  colors?: string[]
  height?: number
}>(), { height: 220 })

const theme = useChartTheme()

const hasData = computed(() => props.values.some((v) => v > 0))

const chartData = computed(() => ({
  labels: props.labels,
  datasets: [{
    data: props.values,
    backgroundColor: props.colors && props.colors.length ? props.colors.map((c) => (c === '#e5e7eb' ? theme.value.track : c)) : theme.value.palette,
    borderWidth: 0,
    borderRadius: 8,
    spacing: 3,
    hoverOffset: 8,
  }],
}))

const options = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  cutout: '72%',
  plugins: {
    legend: { position: 'bottom' as const, labels: { boxWidth: 10, padding: 12, font: { size: 11 }, color: theme.value.text } },
    tooltip: { padding: 12, cornerRadius: 12, backgroundColor: theme.value.tipBg, titleColor: theme.value.tipText, bodyColor: theme.value.tipText },
  },
}))
</script>
<style scoped>
.chart-wrap { position: relative; width: 100%; }
.chart-empty { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--muted, #9ca3af); font-size: 0.875rem; }
</style>
