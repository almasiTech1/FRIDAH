<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between flex-wrap gap-3">
      <h1 class="page-title">Browse Properties</h1>
      <div class="flex gap-2">
        <input v-model="search" class="input w-48 text-sm" placeholder="Search town, estate…" />
        <select v-model="county" class="input w-40 text-sm">
          <option value="">All counties</option>
          <option v-for="c in counties" :key="c" :value="c">{{ c }}</option>
        </select>
      </div>
    </div>

    <!-- Recommended for You -->
    <div v-if="recommendations.length" class="space-y-3">
      <div class="flex items-center justify-between">
        <h2 class="section-title mb-0">{{ recsPersonalized ? '✨ Recommended for You' : '🆕 Recently Listed' }}</h2>
      </div>
      <div class="flex gap-4 overflow-x-auto pb-2 -mx-1 px-1">
        <div
          v-for="r in recommendations" :key="r.property.id"
          class="card overflow-hidden hover:shadow-md transition-shadow cursor-pointer shrink-0 w-56"
          @click="router.push(`/tenant/properties/${r.property.id}`)"
        >
          <div class="h-28 bg-gray-100 relative">
            <img v-if="r.property.primary_image" :src="r.property.primary_image" class="w-full h-full object-cover" />
            <div v-else class="w-full h-full flex items-center justify-center text-gray-300 text-3xl">🏠</div>
          </div>
          <div class="p-3">
            <p class="font-semibold text-gray-900 text-xs truncate">{{ r.property.name }}</p>
            <p class="text-tenant-600 font-semibold text-xs mt-1">{{ r.property.min_rent ? formatKES(r.property.min_rent) + '/mo' : 'Contact' }}</p>
            <p v-if="r.reasons?.length" class="text-[10px] text-gray-400 mt-1 truncate">{{ r.reasons[0] }}</p>
          </div>
        </div>
      </div>
    </div>

    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="i in 6" :key="i" class="card animate-pulse h-52 bg-gray-100 rounded-xl"/>
    </div>
    <div v-else-if="properties.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="p in properties" :key="p.id"
        class="card overflow-hidden hover:shadow-md transition-shadow cursor-pointer"
        @click="router.push(`/tenant/properties/${p.id}`)"
      >
        <div class="h-40 bg-gray-100 relative">
          <img v-if="p.primary_image" :src="p.primary_image" class="w-full h-full object-cover" />
          <div v-else class="w-full h-full flex items-center justify-center text-gray-300 text-4xl">🏠</div>
          <span class="absolute top-2 right-2 badge badge-green text-xs">{{ p.vacant_units_count }} vacant</span>
        </div>
        <div class="p-4">
          <p class="font-semibold text-gray-900 text-sm">{{ p.name }}</p>
          <p class="text-xs text-gray-500 mt-0.5">{{ p.estate ? p.estate + ', ' : '' }}{{ p.town }}, {{ p.county }}</p>
          <div class="flex items-center justify-between mt-3">
            <p class="text-tenant-600 font-semibold text-sm">{{ p.min_rent ? formatKES(p.min_rent) + '/mo' : 'Contact' }}</p>
            <span class="badge badge-gray capitalize">{{ p.property_type }}</span>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="card card-body text-center py-12 text-gray-400">No properties found.</div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { propertiesApi } from '@/api/services'
import { formatKES } from '@/utils/formatters'
import type { Property } from '@/types'
const router = useRouter()
const properties = ref<Property[]>([])
const loading = ref(true)
const search = ref('')
const county = ref('')
const counties = ['Nairobi','Mombasa','Kisumu','Nakuru','Eldoret','Thika','Nyeri','Machakos','Meru','Kiambu']

const recommendations = ref<{ property: Property; score: number | null; reasons: string[] }[]>([])
const recsPersonalized = ref(false)
async function loadRecommendations() {
  try {
    const { data } = await propertiesApi.recommendations(8)
    recommendations.value = (data as any).data?.results || []
    recsPersonalized.value = (data as any).data?.is_personalized || false
  } catch { recommendations.value = [] }
}

async function load() {
  loading.value = true
  try {
    const { data } = await propertiesApi.list({ search: search.value, county: county.value || undefined })
    properties.value = data.data?.results || data.data || []
  } catch { properties.value = [] } finally { loading.value = false }
}
watch([search, county], load)
onMounted(() => { load(); loadRecommendations() })
</script>
