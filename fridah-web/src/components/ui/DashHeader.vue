<template>
  <header class="fx-head">
    <div>
      <h2>{{ greeting }}, {{ name }}</h2>
      <p>{{ subtitle || dateStr }}<span v-if="subtitle"> · {{ dateStr }}</span></p>
    </div>
    <div class="fx-actions"><slot /></div>
  </header>
</template>
<script setup lang="ts">
import { computed } from 'vue'
defineProps<{ name: string; subtitle?: string }>()
const greeting = computed(() => { const h = new Date().getHours(); return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening' })
const dateStr = new Date().toLocaleDateString('en-KE', { weekday: 'long', day: 'numeric', month: 'long' })
</script>
