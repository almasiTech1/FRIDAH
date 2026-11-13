<template>
  <button type="button" class="fx-fav" :class="{ on: saved }" :aria-pressed="saved" :aria-label="saved ? 'Remove from saved' : 'Save'" @click.stop.prevent="$emit('toggle')">
    <Heart :fill="saved ? 'currentColor' : 'none'" />
  </button>
</template>
<script setup lang="ts">
import { Heart } from 'lucide-vue-next'
defineProps<{ saved: boolean }>()
defineEmits<{ toggle: [] }>()
</script>
