<template>
  <div class="relative max-w-3xl mx-auto">
    <div class="overflow-hidden rounded-3xl">
      <div
        class="flex transition-transform duration-500 ease-out"
        :style="{ transform: `translateX(-${index * 100}%)` }"
      >
        <div v-for="(t, i) in items" :key="i" class="w-full flex-shrink-0 px-2">
          <div class="glass-card p-8 md:p-10 text-center">
            <div class="flex justify-center gap-1 mb-4">
              <svg v-for="s in 5" :key="s" class="w-5 h-5 text-amber-400" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.518 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.196-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118L2.075 10.1c-.783-.57-.38-1.81.588-1.81h4.915a1 1 0 00.95-.69l1.518-4.674z" />
              </svg>
            </div>
            <p class="text-lg md:text-xl font-medium text-gray-800 dark:text-gray-100 leading-relaxed mb-6">
              &ldquo;{{ t.quote }}&rdquo;
            </p>
            <p class="font-semibold text-gray-900 dark:text-white">{{ t.name }}</p>
            <p class="text-sm text-gray-500 dark:text-gray-400">{{ t.role }}</p>
          </div>
        </div>
      </div>
    </div>

    <button class="carousel-nav left-0 -translate-x-4" @click="prev" aria-label="Previous testimonial">
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
    </button>
    <button class="carousel-nav right-0 translate-x-4" @click="next" aria-label="Next testimonial">
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
    </button>

    <div class="flex justify-center gap-2 mt-6">
      <button
        v-for="(_, i) in items" :key="i"
        class="h-2 rounded-full transition-all duration-300"
        :class="index === i ? 'w-6 bg-brand-600' : 'w-2 bg-gray-300 dark:bg-gray-700'"
        @click="index = i"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps<{ items: { quote: string; name: string; role: string }[] }>()
const index = ref(0)
let timer: ReturnType<typeof setInterval> | null = null

function next() { index.value = (index.value + 1) % props.items.length }
function prev() { index.value = (index.value - 1 + props.items.length) % props.items.length }

onMounted(() => { timer = setInterval(next, 6000) })
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<style scoped>
.carousel-nav {
  @apply absolute top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-white dark:bg-gray-800 shadow-lg flex items-center justify-center text-gray-500 hover:text-brand-600 dark:text-gray-400 dark:hover:text-brand-400 transition-colors hidden md:flex;
}
</style>
