<template>
  <div class="fx-ring" :style="`width:${size}px;height:${size}px`">
    <svg :width="size" :height="size" :viewBox="`0 0 ${size} ${size}`">
      <circle :cx="size / 2" :cy="size / 2" :r="r" fill="none" stroke="var(--surface-soft)" :stroke-width="stroke" />
      <circle :cx="size / 2" :cy="size / 2" :r="r" fill="none" :stroke="color" :stroke-width="stroke" stroke-linecap="round"
        :stroke-dasharray="c" :stroke-dashoffset="c * (1 - shown / 100)" style="transition: stroke-dashoffset .9s cubic-bezier(.2,.8,.2,1)" />
    </svg>
    <div class="inner"><slot><b>{{ Math.round(shown) }}%</b><span v-if="label">{{ label }}</span></slot></div>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
const props = withDefaults(defineProps<{ value: number; size?: number; stroke?: number; color?: string; label?: string }>(), { size: 120, stroke: 11, color: 'var(--accent)' })
const r = computed(() => (props.size - props.stroke) / 2)
const c = computed(() => 2 * Math.PI * r.value)
const shown = ref(0)
const clamp = (v: number) => Math.max(0, Math.min(100, v))
onMounted(() => requestAnimationFrame(() => (shown.value = clamp(props.value))))
watch(() => props.value, (v) => (shown.value = clamp(v)))
</script>
