<template>
  <div class="fx-bars" :style="`--h:${height}px`" @mouseleave="hover = -1">
    <div class="fx-grid-lines"><i /><i /><i /><i /></div>
    <div v-for="(v, i) in values" :key="`${i}-${labels[i]}`" class="fx-bar-col" :class="{ sel: selected === i }"
      tabindex="0" role="button" :aria-label="`${labels[i]}: ${fmt(v)}`"
      @click="pick(i)" @keydown.enter.prevent="pick(i)" @keydown.space.prevent="pick(i)" @mouseenter="hover = i">
      <span class="fx-bar-tip">{{ fmt(v) }}</span>
      <div class="fx-bar" :style="`height:${Math.max(6, (v / max) * 100)}%;animation-delay:${i * 55}ms`" />
      <span class="fx-bar-lab">{{ labels[i] }}</span>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { compactKES } from '@/composables/useCountUp'
const props = withDefaults(defineProps<{ labels: string[]; values: number[]; height?: number; currency?: boolean; modelValue?: number }>(), { height: 230, currency: true })
const emit = defineEmits<{ 'update:modelValue': [i: number]; select: [i: number] }>()
const hover = ref(-1)
const selected = ref(props.modelValue ?? props.values.length - 1)
watch(() => props.modelValue, (v) => { if (v !== undefined) selected.value = v })
watch(() => props.values.length, (n) => { if (selected.value >= n) selected.value = n - 1 })
const max = computed(() => Math.max(1, ...props.values) * 1.08)
const fmt = (v: number) => props.currency ? compactKES(v) : v.toLocaleString()
function pick(i: number) { selected.value = i; emit('update:modelValue', i); emit('select', i) }
</script>
