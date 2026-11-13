<template>
  <div class="fx-feed">
    <RouterLink v-for="a in items" :key="a.id" :to="a.to || '#'" class="fx-feed-item" @click="!a.to && $event.preventDefault()">
      <span class="fx-avatar" style="width:36px;height:36px;border-radius:12px">{{ a.initials }}</span>
      <span class="min-w-0"><b class="block truncate">{{ a.title }}</b><small>{{ a.meta }}</small></span>
      <span v-if="a.amount" class="amt" :class="a.amount.startsWith('-') || a.amount.startsWith('−') ? 'neg' : 'pos'">{{ a.amount }}</span>
    </RouterLink>
  </div>
</template>
<script setup lang="ts">
import { RouterLink } from 'vue-router'
defineProps<{ items: { id: string | number; initials: string; title: string; meta: string; amount?: string; to?: string }[] }>()
</script>
