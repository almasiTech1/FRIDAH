<template>
  <div class="fx-toasts" aria-live="polite">
    <TransitionGroup name="fx-toast">
      <div v-for="t in toasts.items" :key="t.id" class="fx-toast" role="status" @click="toasts.dismiss(t.id)">
        <i class="tone" :class="t.tone" /><div><b>{{ t.title }}</b><span v-if="t.body">{{ t.body }}</span></div>
      </div>
    </TransitionGroup>
  </div>
</template>
<script setup lang="ts">
import { useToastStore } from '@/stores/toasts'
const toasts = useToastStore()
</script>
