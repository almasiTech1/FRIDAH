<template>
  <span ref="el">{{ display }}</span>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps<{
  end: number
  duration?: number
  prefix?: string
  suffix?: string
  decimals?: number
}>()

const el = ref<HTMLElement | null>(null)
const current = ref(0)
let observer: IntersectionObserver | null = null
let rafId: number | null = null

const display = computed(() => {
  const n = current.value.toFixed(props.decimals ?? 0)
  return `${props.prefix ?? ''}${Number(n).toLocaleString()}${props.suffix ?? ''}`
})

function animate() {
  const duration = props.duration ?? 1800
  const start = performance.now()
  const from = 0
  const to = props.end

  function tick(now: number) {
    const elapsed = now - start
    const progress = Math.min(elapsed / duration, 1)
    // ease-out-cubic
    const eased = 1 - Math.pow(1 - progress, 3)
    current.value = from + (to - from) * eased
    if (progress < 1) {
      rafId = requestAnimationFrame(tick)
    } else {
      current.value = to
    }
  }
  rafId = requestAnimationFrame(tick)
}

onMounted(() => {
  if (!el.value) return
  observer = new IntersectionObserver(
    (entries) => {
      if (entries[0]?.isIntersecting) {
        animate()
        observer?.disconnect()
      }
    },
    { threshold: 0.4 }
  )
  observer.observe(el.value)
})

onUnmounted(() => {
  observer?.disconnect()
  if (rafId) cancelAnimationFrame(rafId)
})
</script>
