<template>
  <component :is="to ? RouterLink : 'div'" v-bind="to ? { to } : {}" v-spot class="fx-kpi" :class="[variant, { clickable: !!to }]"
    :style="`--kc:${color};--kc-soft:${color}22`">
    <div class="fx-kpi-top">
      <div class="fx-kpi-icon">
        <component :is="iconComp" v-if="iconComp" />
        <span v-else class="text-lg leading-none">{{ icon }}</span>
      </div>
      <span v-if="trend !== undefined" class="fx-chip" :class="trend < 0 ? 'down' : trend === 0 ? 'neutral' : ''">
        {{ trend > 0 ? '▲' : trend < 0 ? '▼' : '•' }} {{ Math.abs(trend) }}%
      </span>
    </div>
    <p class="fx-kpi-val">{{ displayValue }}</p>
    <p class="fx-kpi-label">{{ label }}</p>
    <p v-if="sub" class="fx-kpi-sub">{{ sub }}</p>
    <Sparkline v-if="spark?.length || bars?.length" :values="(spark?.length ? spark : bars) as number[]" :color="variant === 'default' ? color : 'currentColor'" />
  </component>
</template>
<script setup lang="ts">
import { computed, type Component } from 'vue'
import { RouterLink } from 'vue-router'
import { formatKES } from '@/utils/formatters'
import { useCountUp } from '@/composables/useCountUp'
import Sparkline from '@/components/ui/Sparkline.vue'

const props = withDefaults(defineProps<{
  label: string; value: number | string; currency?: boolean; sub?: string; icon?: string; iconComp?: Component
  color?: string; trend?: number; bars?: number[]; spark?: number[]; animate?: boolean; to?: string
  variant?: 'default' | 'accent' | 'inverse'
}>(), { color: 'var(--accent)', icon: '📊', animate: true, variant: 'default' })

const numeric = computed(() => typeof props.value === 'number' ? props.value : NaN)
const counted = useCountUp(() => (Number.isFinite(numeric.value) ? numeric.value : 0))
const displayValue = computed(() => {
  if (typeof props.value === 'string') return props.value
  const v = props.animate ? counted.value : props.value
  return props.currency ? formatKES(v) : v.toLocaleString()
})
</script>
