<template>
  <div
    class="relative rounded-3xl p-8 flex flex-col transition-all duration-300"
    :class="highlighted
      ? 'bg-gray-900 dark:bg-brand-950 text-white shadow-2xl scale-105 border-2 border-brand-500'
      : 'bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 hover:shadow-card-hover'"
  >
    <span v-if="highlighted" class="absolute -top-3 left-1/2 -translate-x-1/2 bg-brand-500 text-white text-xs font-bold px-4 py-1 rounded-full">
      Most Popular
    </span>
    <h3 class="text-lg font-bold mb-1" :class="highlighted ? 'text-white' : 'text-gray-900 dark:text-white'">{{ name }}</h3>
    <p class="text-sm mb-5" :class="highlighted ? 'text-white/70' : 'text-gray-500 dark:text-gray-400'">{{ tagline }}</p>
    <div class="mb-6">
      <span class="text-4xl font-black" :class="highlighted ? 'text-white' : 'text-gray-900 dark:text-white'">{{ price }}</span>
      <span v-if="period" class="text-sm" :class="highlighted ? 'text-white/60' : 'text-gray-400'"> {{ period }}</span>
    </div>
    <ul class="space-y-3 mb-8 flex-1">
      <li v-for="f in features" :key="f" class="flex items-start gap-2 text-sm" :class="highlighted ? 'text-white/90' : 'text-gray-600 dark:text-gray-300'">
        <svg class="w-5 h-5 flex-shrink-0" :class="highlighted ? 'text-brand-400' : 'text-brand-600 dark:text-brand-400'" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
        </svg>
        {{ f }}
      </li>
    </ul>
    <RouterLink
      to="/register"
      class="btn text-center justify-center"
      :class="highlighted ? 'bg-brand-500 hover:bg-brand-400 text-white' : 'btn-outline'"
    >
      Choose Plan
    </RouterLink>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  name: string
  tagline: string
  price: string
  period?: string
  features: string[]
  highlighted?: boolean
}>()
</script>
