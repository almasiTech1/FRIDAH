<template>
  <section class="py-24 max-w-7xl mx-auto px-6">
    <div v-reveal="'up'" class="text-center max-w-2xl mx-auto mb-14">
      <h2 class="text-3xl md:text-4xl font-black text-gray-900 dark:text-white">Find your area</h2>
      <p class="mt-3 text-gray-500 dark:text-gray-400">Browse available properties across Kenya's most popular counties.</p>
    </div>

    <div v-if="loading" class="grid grid-cols-2 md:grid-cols-4 gap-5">
      <div v-for="i in 8" :key="i" class="h-32 rounded-2xl bg-gray-100 dark:bg-gray-800 animate-pulse" />
    </div>

    <div v-else-if="areas.length" class="grid grid-cols-2 md:grid-cols-4 gap-5">
      <RouterLink
        v-for="(a, i) in areas" :key="a.county" v-reveal="'zoom'" :style="{ transitionDelay: `${(i % 8) * 60}ms` }"
        :to="`/properties?county=${encodeURIComponent(a.county)}`"
        class="group p-6 rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 hover:shadow-card-hover hover:-translate-y-1 transition-all duration-300"
      >
        <div class="text-3xl mb-3">📍</div>
        <p class="font-bold text-gray-900 dark:text-white group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors">{{ a.county }}</p>
        <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{{ a.property_count }} {{ a.property_count === 1 ? 'property' : 'properties' }}</p>
        <p class="text-xs text-emerald-600 dark:text-emerald-400 mt-0.5">{{ a.vacant_units }} vacant units</p>
      </RouterLink>
    </div>

    <div v-else class="text-center py-10 text-gray-400 text-sm">
      No listed areas yet — check back soon as properties come online.
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { propertiesApi } from '@/api/services'

interface AreaSummary { county: string; property_count: number; vacant_units: number }

const areas = ref<AreaSummary[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const { data } = await propertiesApi.areas()
    areas.value = ((data as any).data || []).slice(0, 8)
  } catch {
    areas.value = []
  } finally {
    loading.value = false
  }
})
</script>
