<template>
  <div>
    <div class="fx-donut">
      <svg viewBox="0 0 120 120" role="img" :aria-label="title">
        <circle cx="60" cy="60" :r="R" fill="none" stroke="var(--surface-soft)" stroke-width="14" />
        <circle v-for="(s, i) in segs" :key="s.label" class="seg" cx="60" cy="60" :r="R" fill="none" :stroke="s.color"
          :stroke-width="active === i ? 19 : 14" stroke-linecap="butt" :stroke-dasharray="`${s.len} ${C - s.len}`" :stroke-dashoffset="-s.off"
          :opacity="active === -1 || active === i ? 1 : .35" @mouseenter="active = i" @mouseleave="active = -1" @click="$emit('select', s.label)" />
      </svg>
      <div class="fx-donut-center"><b>{{ active === -1 ? centerValue : fmt(segs[active].value) }}</b><span>{{ active === -1 ? centerLabel : segs[active].label }}</span></div>
    </div>
    <div class="fx-legend">
      <button v-for="(s, i) in segs" :key="s.label" :class="{ on: active === i }" @mouseenter="active = i" @mouseleave="active = -1" @focus="active = i" @blur="active = -1">
        <i :style="`background:${s.color}`" />{{ s.label }}<em>{{ fmt(s.value) }}</em>
      </button>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
const props = withDefaults(defineProps<{ items: { label: string; value: number; color?: string }[]; centerLabel?: string; centerText?: string; title?: string; money?: boolean }>(), { centerLabel: 'Total', title: 'Breakdown' })
defineEmits<{ select: [label: string] }>()
const R = 46, C = 2 * Math.PI * R
const active = ref(-1)
const PALETTE = ['var(--c1)', 'var(--c2)', 'var(--c3)', 'var(--c4)', 'var(--c5)']
const total = computed(() => props.items.reduce((a, b) => a + b.value, 0))
const segs = computed(() => {
  let off = 0
  return props.items.map((it, i) => {
    const len = total.value ? (it.value / total.value) * C - (props.items.length > 1 ? 3 : 0) : 0
    const seg = { ...it, color: it.color || PALETTE[i % PALETTE.length], len: Math.max(len, 0), off }
    off += total.value ? (it.value / total.value) * C : 0
    return seg
  })
})
const fmt = (n: number) => props.money ? (n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(1)}K` : String(n)) : n.toLocaleString()
const centerValue = computed(() => props.centerText ?? fmt(total.value))
</script>
