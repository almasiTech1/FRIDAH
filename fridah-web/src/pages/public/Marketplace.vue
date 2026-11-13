<template>
  <div>
    <section class="max-w-7xl mx-auto px-6 pt-16 pb-10">
      <p v-reveal="'fade'" class="text-brand-600 dark:text-brand-400 font-semibold text-sm uppercase tracking-widest mb-3">Marketplace</p>
      <h1 v-reveal="'up'" class="text-3xl md:text-4xl font-black text-gray-900 dark:text-white mb-3">Verified service providers</h1>
      <p v-reveal="'up'" class="text-gray-500 dark:text-gray-400 max-w-2xl mb-8">
        Electricians, plumbers, painters, cleaners, movers, and carpenters — vetted and rated by real landlords on the platform.
      </p>

      <div v-reveal="'up'" class="flex flex-wrap gap-2">
        <button
          v-for="cat in categories" :key="cat"
          class="px-4 py-2 rounded-full text-sm font-semibold transition-colors"
          :class="activeCategory === cat ? 'bg-brand-600 text-white' : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300'"
          @click="activeCategory = cat"
        >
          {{ cat }}
        </button>
      </div>
    </section>

    <section class="max-w-7xl mx-auto px-6 pb-24">
      <div v-if="loading" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <div v-for="i in 6" :key="i" class="h-48 rounded-3xl bg-gray-100 dark:bg-gray-800 animate-pulse" />
      </div>
      <div v-else-if="filteredProviders.length === 0" class="text-center py-20 text-gray-400">
        No providers found in this category yet.
      </div>
      <div v-else class="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <div
          v-for="(p, i) in filteredProviders" :key="p.id" v-reveal="'up'" :style="{ transitionDelay: `${(i % 6) * 60}ms` }"
          class="p-6 rounded-3xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 hover:shadow-card-hover hover:-translate-y-1 transition-all duration-300"
        >
          <div class="flex items-start justify-between mb-3">
            <div class="w-12 h-12 rounded-2xl bg-brand-50 dark:bg-brand-950 flex items-center justify-center text-xl font-bold text-brand-700 dark:text-brand-400">
              {{ p.name?.[0]?.toUpperCase() || '?' }}
            </div>
            <span v-if="p.is_verified" class="flex items-center gap-1 text-xs font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950 px-2 py-1 rounded-full">
              <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>
              Verified
            </span>
          </div>
          <h3 class="font-bold text-gray-900 dark:text-white">{{ p.name }}</h3>
          <p class="text-sm text-gray-500 dark:text-gray-400 mb-3">{{ p.categories_detail?.map((c: any) => c.name).join(', ') }}</p>
          <div class="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400 mb-3">
            <span v-if="p.average_rating" class="flex items-center gap-1">⭐ {{ p.average_rating.toFixed(1) }}</span>
            <span>{{ p.years_experience }} yrs experience</span>
          </div>
          <p class="text-sm text-gray-600 dark:text-gray-300 line-clamp-2">{{ p.bio }}</p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { servicesApi } from '@/api/services'

const providers = ref<any[]>([])
const loading = ref(true)
const categories = ['All', 'Electricians', 'Plumbers', 'Painters', 'Cleaners', 'Movers', 'Carpenters']
const activeCategory = ref('All')

const filteredProviders = computed(() => {
  if (activeCategory.value === 'All') return providers.value
  return providers.value.filter((p) =>
    p.categories_detail?.some((c: any) => c.name?.toLowerCase().includes(activeCategory.value.toLowerCase()))
  )
})

onMounted(async () => {
  try {
    const { data } = await servicesApi.publicProviders()
    providers.value = (data as any).data?.results || (data as any).data || []
  } catch {
    providers.value = []
  } finally {
    loading.value = false
  }
})
</script>
