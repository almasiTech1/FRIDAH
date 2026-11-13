<template>
  <button type="button" class="fx-back" :aria-label="label" :title="label" @click="goBack"><ArrowLeft /><span>{{ label }}</span></button>
</template>
<script setup lang="ts">
import { ArrowLeft } from 'lucide-vue-next'
import { useRouter } from 'vue-router'

const props = withDefaults(defineProps<{ fallback?: string; label?: string }>(), { fallback: '/', label: 'Back' })
const router = useRouter()

/** Goes to the previous in-app page; if the tab was opened directly (no history), goes to the fallback instead. */
function goBack() {
  const hasPrev = typeof window.history.state?.back === 'string' && window.history.state.back
  if (hasPrev) router.back()
  else router.push(props.fallback)
}
</script>
