<template>
  <div class="fx-tiles">
    <RouterLink v-for="q in items" :key="q.to" :to="q.to" class="fx-tile">
      <span class="fx-ico"><component :is="q.icon" /></span>{{ q.label }}
    </RouterLink>
  </div>
</template>
<script setup lang="ts">
import type { Component } from 'vue'
import { RouterLink } from 'vue-router'
defineProps<{ items: { to: string; label: string; icon: Component }[] }>()
</script>
