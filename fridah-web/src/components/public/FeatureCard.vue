<template>
  <div class="group p-6 rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 hover:shadow-card-hover hover:-translate-y-1 transition-all duration-300">
    <div
      class="w-12 h-12 rounded-xl flex items-center justify-center text-2xl mb-4 transition-transform duration-300 group-hover:scale-110"
      :style="{ background: `${color}1a` }"
    >
      {{ icon }}
    </div>
    <h3 class="font-bold text-gray-900 dark:text-white mb-1">{{ title }}</h3>
    <p class="text-sm text-gray-500 dark:text-gray-400 leading-relaxed">{{ description }}</p>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  icon: string
  title: string
  description: string
  color?: string
}>(), {
  color: '#0d9488',
})
</script>
