<template>
  <div class="space-y-3">
    <div
      v-for="(item, i) in items" :key="i"
      class="border border-gray-200 dark:border-gray-800 rounded-2xl overflow-hidden bg-white dark:bg-gray-900"
    >
      <button
        class="w-full flex items-center justify-between gap-4 p-5 text-left"
        @click="openIndex = openIndex === i ? null : i"
      >
        <span class="font-semibold text-gray-900 dark:text-white">{{ item.q }}</span>
        <svg
          class="w-5 h-5 flex-shrink-0 text-brand-600 dark:text-brand-400 transition-transform duration-300"
          :class="{ 'rotate-45': openIndex === i }"
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
      </button>
      <div
        class="grid transition-all duration-300 ease-out"
        :style="{ gridTemplateRows: openIndex === i ? '1fr' : '0fr' }"
      >
        <div class="overflow-hidden">
          <p class="px-5 pb-5 text-gray-600 dark:text-gray-400 text-sm leading-relaxed">{{ item.a }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{ items: { q: string; a: string }[] }>()
const openIndex = ref<number | null>(0)
</script>
