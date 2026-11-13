<template>
  <div>
    <div class="flex items-center justify-between mb-2">
      <label class="label mb-0">Price Range (KES)</label>
      <span class="text-sm font-semibold text-brand-600 dark:text-brand-400">
        {{ formatK(modelValue[0]) }} – {{ formatK(modelValue[1]) }}{{ modelValue[1] >= max ? '+' : '' }}
      </span>
    </div>
    <div class="relative h-6 flex items-center">
      <div class="absolute inset-x-0 h-1.5 rounded-full bg-gray-200 dark:bg-gray-700" />
      <div
        class="absolute h-1.5 rounded-full bg-brand-600"
        :style="{ left: trackLeft + '%', right: trackRight + '%' }"
      />
      <input
        type="range" :min="min" :max="max" :step="step"
        :value="modelValue[0]"
        class="range-thumb"
        @input="onMinInput"
      />
      <input
        type="range" :min="min" :max="max" :step="step"
        :value="modelValue[1]"
        class="range-thumb"
        @input="onMaxInput"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  modelValue: [number, number]
  min?: number
  max?: number
  step?: number
}>(), {
  min: 0,
  max: 200000,
  step: 1000,
})

const emit = defineEmits<{ (e: 'update:modelValue', value: [number, number]): void }>()

const trackLeft = computed(() => ((props.modelValue[0] - props.min) / (props.max - props.min)) * 100)
const trackRight = computed(() => 100 - ((props.modelValue[1] - props.min) / (props.max - props.min)) * 100)

function formatK(v: number) {
  return v >= 1000 ? `${(v / 1000).toFixed(0)}K` : String(v)
}

function onMinInput(e: Event) {
  const value = Math.min(Number((e.target as HTMLInputElement).value), props.modelValue[1] - props.step)
  emit('update:modelValue', [value, props.modelValue[1]])
}

function onMaxInput(e: Event) {
  const value = Math.max(Number((e.target as HTMLInputElement).value), props.modelValue[0] + props.step)
  emit('update:modelValue', [props.modelValue[0], value])
}
</script>

<style scoped>
.range-thumb {
  @apply absolute inset-x-0 w-full appearance-none bg-transparent pointer-events-none;
}
.range-thumb::-webkit-slider-thumb {
  @apply appearance-none w-5 h-5 rounded-full bg-white border-2 border-brand-600 shadow cursor-pointer pointer-events-auto;
  margin-top: 0;
}
.range-thumb::-moz-range-thumb {
  @apply w-5 h-5 rounded-full bg-white border-2 border-brand-600 shadow cursor-pointer pointer-events-auto;
}
.range-thumb::-webkit-slider-runnable-track {
  @apply bg-transparent;
}
.range-thumb::-moz-range-track {
  @apply bg-transparent;
}
</style>
