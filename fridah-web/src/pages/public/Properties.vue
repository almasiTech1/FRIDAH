<template>
  <div>
    <section class="max-w-7xl mx-auto px-6 pt-16 pb-10">
      <p v-reveal="'fade'" class="text-brand-600 dark:text-brand-400 font-semibold text-sm uppercase tracking-widest mb-3">Properties</p>
      <h1 v-reveal="'up'" class="text-3xl md:text-4xl font-black text-gray-900 dark:text-white mb-6">Find your next home</h1>

      <div v-reveal="'up'" class="mb-6 p-5 rounded-2xl bg-gradient-to-br from-brand-50 to-white dark:from-brand-950 dark:to-gray-900 border border-brand-100 dark:border-brand-900">
        <label class="flex items-center gap-2 text-sm font-semibold text-brand-700 dark:text-brand-400 mb-2">
          ✨ Ask our AI Property Assistant
        </label>
        <div class="flex flex-col sm:flex-row gap-2">
          <input
            v-model="aiQuery" placeholder='e.g. "2-bedroom under KSh 30,000 near Kilimani with parking"'
            class="input flex-1" @keyup.enter="runAiSearch"
          />
          <button class="btn-primary bg-brand-600 hover:bg-brand-700 justify-center whitespace-nowrap" :disabled="aiLoading" @click="runAiSearch">
            <span v-if="aiLoading" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
            <span v-else>Ask AI</span>
          </button>
          <button v-if="aiResults" class="btn-outline whitespace-nowrap" @click="clearAiSearch">Clear</button>
        </div>
        <p v-if="aiError" class="text-xs text-red-500 mt-2">{{ aiError }}</p>
      </div>

      <div v-if="aiResults" class="mb-8">
        <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
          {{ aiResults.length }} AI-matched {{ aiResults.length === 1 ? 'result' : 'results' }} for "{{ lastAiQuery }}"
        </p>
        <div v-if="aiResults.length" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          <div
            v-for="r in aiResults" :key="r.property.id"
            class="rounded-3xl overflow-hidden border-2 border-brand-100 dark:border-brand-900 bg-white dark:bg-gray-900 hover:shadow-card-hover hover:-translate-y-1 transition-all duration-300"
          >
            <div class="aspect-video bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
              <img v-if="r.property.primary_image" :src="r.property.primary_image" class="w-full h-full object-cover" :alt="r.property.name" />
              <img v-else :src="propertyFallbackImage(r.property.id)" class="w-full h-full object-cover" :alt="r.property.name" loading="lazy" />
            </div>
            <div class="p-5">
              <h3 class="font-bold text-gray-900 dark:text-white mb-1">{{ r.property.name }}</h3>
              <p class="text-sm text-gray-500 dark:text-gray-400 mb-3">{{ r.property.town }}, {{ r.property.county }}</p>
              <div class="flex items-start gap-1.5 p-2.5 rounded-lg bg-brand-50 dark:bg-brand-950 mb-3">
                <span class="text-xs flex-shrink-0">✨</span>
                <p class="text-xs text-brand-700 dark:text-brand-400">{{ r.explanation }}</p>
              </div>
              <p class="font-black text-brand-600 dark:text-brand-400">{{ r.property.min_rent ? `From KES ${r.property.min_rent.toLocaleString()}` : 'Contact for pricing' }}</p>
            </div>
          </div>
        </div>
        <p v-else class="text-center py-10 text-gray-400">No matches found for that search — try adjusting your description.</p>
      </div>

      <div v-show="!aiResults" v-reveal="'up'" class="grid sm:grid-cols-2 md:grid-cols-4 gap-3 items-end">
        <input v-model="filters.county" placeholder="County" class="input" @keyup.enter="load" />
        <input v-model="filters.town" placeholder="Town" class="input" @keyup.enter="load" />
        <select v-model="filters.bedrooms" class="input">
          <option value="">Any bedrooms</option>
          <option v-for="n in [1,2,3,4,5]" :key="n" :value="n">{{ n }}+ bedrooms</option>
        </select>
        <button class="btn-primary bg-brand-600 hover:bg-brand-700 justify-center" @click="load">Search</button>
      </div>

      <div v-show="!aiResults" v-reveal="'up'" class="mt-5 max-w-md">
        <PriceRangeSlider v-model="priceRange" :max="300000" :step="2500" />
      </div>

      <div v-show="!aiResults" class="flex justify-end items-center gap-3 mt-4">
        <button class="fx-look" :class="{ on: showSaved }" :aria-pressed="showSaved" @click="showSaved = !showSaved">♥ Saved ({{ fav.count.value }})</button>
        <div class="inline-flex rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <button class="px-4 py-2 text-sm font-semibold" :class="view === 'list' ? 'bg-brand-600 text-white' : 'bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-300'" @click="view = 'list'">List</button>
          <button class="px-4 py-2 text-sm font-semibold" :class="view === 'map' ? 'bg-brand-600 text-white' : 'bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-300'" @click="view = 'map'">Map</button>
        </div>
      </div>
    </section>

    <section v-if="!aiResults && view === 'map'" class="max-w-7xl mx-auto px-6 pb-24">
      <div class="h-[520px] rounded-3xl overflow-hidden border border-gray-100 dark:border-gray-800">
        <GoogleMapView :markers="mapMarkers" cluster show-near-me @location-found="onLocationFound" />
      </div>
      <p v-if="userLocation" class="text-xs text-gray-400 mt-3 text-center">
        Showing distances from your current location. List view is now sorted nearest first.
      </p>
    </section>

    <section v-else-if="!aiResults" class="max-w-7xl mx-auto px-6 pb-24">
      <div v-if="loading" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <div v-for="i in 6" :key="i" class="h-72 rounded-3xl bg-gray-100 dark:bg-gray-800 animate-pulse" />
      </div>
      <div v-else-if="properties.length === 0" class="text-center py-20 text-gray-400">
        No properties match your search yet — try adjusting your filters.
      </div>
      <div v-else class="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <div
          v-for="(p, i) in shownProperties" :key="p.id" v-reveal="'up'" :style="{ transitionDelay: `${(i % 6) * 60}ms` }"
          class="rounded-3xl overflow-hidden border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 hover:shadow-card-hover hover:-translate-y-1 transition-all duration-300 cursor-pointer group"
          @click="openProperty(p)"
        >
          <div class="aspect-video bg-gray-100 dark:bg-gray-800 flex items-center justify-center relative overflow-hidden">
            <FavButton :saved="fav.has(p.id)" @toggle="toggleFav(p.id)" />
            <img v-if="p.primary_image" :src="p.primary_image" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" :alt="p.name" />
            <img v-else :src="propertyFallbackImage(p.id)" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" :alt="p.name" loading="lazy" />
          </div>
          <div class="p-5">
            <div class="flex items-center justify-between mb-1">
              <h3 class="font-bold text-gray-900 dark:text-white">{{ p.name }}</h3>
              <span class="text-xs px-2 py-0.5 rounded-full bg-brand-50 dark:bg-brand-950 text-brand-700 dark:text-brand-400 font-semibold capitalize">{{ p.property_type }}</span>
            </div>
            <p class="text-sm text-gray-500 dark:text-gray-400 mb-3">
              {{ p.estate ? `${p.estate}, ` : '' }}{{ p.town }}, {{ p.county }}
              <span v-if="distanceFor(p) !== null" class="text-brand-600 dark:text-brand-400 font-medium">· {{ distanceFor(p)!.toFixed(1) }} km away</span>
            </p>
            <div class="flex items-center justify-between">
              <p class="font-black text-brand-600 dark:text-brand-400">{{ p.min_rent ? `From KES ${p.min_rent.toLocaleString()}` : 'Contact for pricing' }}</p>
              <span class="text-xs text-gray-400">{{ p.vacant_units_count }} vacant</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { propertiesApi, aiApi } from '@/api/services'
import { propertyFallbackImage } from '@/utils/stockImages'
import GoogleMapView from '@/components/public/GoogleMapView.vue'
import FavButton from '@/components/public/FavButton.vue'
import { useFavorites } from '@/composables/useFavorites'
import { useToastStore } from '@/stores/toasts'
import { useAuthStore } from '@/stores/auth'
import PriceRangeSlider from '@/components/public/PriceRangeSlider.vue'
import type { MapMarker } from '@/components/public/GoogleMapView.vue'
import { haversineKm } from '@/utils/geo'
import type { Property } from '@/types'
const router = useRouter()
const auth = useAuthStore()
/** Open a house: tenants go straight to its page (units + Apply to Rent); visitors sign in first and come back to it. */
function openProperty(p: { id: string }) {
  const target = `/tenant/properties/${p.id}`
  if (!auth.isAuthenticated) return router.push({ path: '/login', query: { redirect: target } })
  if (auth.user?.role === 'tenant') return router.push(target)
  toast.push('Tenants rent homes', { body: 'Sign in with a tenant account to apply for this home.', tone: 'info' })
}

const route = useRoute()
const properties = ref<Property[]>([])
const loading = ref(true)
const toast = useToastStore()
const view = ref<'list' | 'map'>('list')
const fav = useFavorites('property')
const showSaved = ref(false)
const userLocation = ref<{ lat: number; lng: number } | null>(null)
const priceRange = ref<[number, number]>([0, 300000])
const PRICE_MAX = 300000
const filters = ref<{ county: string; town: string; bedrooms: string }>({
  county: (route.query.county as string) || '', town: '', bedrooms: '',
})

const mapMarkers = computed<MapMarker[]>(() =>
  properties.value
    .filter((p) => p.latitude && p.longitude)
    .map((p) => ({
      id: p.id,
      lat: Number(p.latitude),
      lng: Number(p.longitude),
      title: p.name,
      subtitle: `${p.town}, ${p.county}${p.min_rent ? ` · From KES ${p.min_rent.toLocaleString()}` : ''}`,
    }))
)

function distanceFor(p: Property): number | null {
  if (!userLocation.value || !p.latitude || !p.longitude) return null
  return haversineKm(userLocation.value, { lat: Number(p.latitude), lng: Number(p.longitude) })
}

const shownProperties = computed(() => (showSaved.value ? sortedProperties.value.filter((p: any) => fav.has(p.id)) : sortedProperties.value))
function toggleFav(id: string) { const on = fav.toggle(id); toast.push(on ? 'Saved' : 'Removed from saved', { tone: 'info', ms: 1800 }) }
const sortedProperties = computed(() => {
  if (!userLocation.value) return properties.value
  return [...properties.value].sort((a, b) => {
    const da = distanceFor(a)
    const db = distanceFor(b)
    if (da === null) return 1
    if (db === null) return -1
    return da - db
  })
})

function onLocationFound(location: { lat: number; lng: number }) {
  userLocation.value = location
}

async function load() {
  loading.value = true
  try {
    const params: Record<string, unknown> = {}
    if (filters.value.county) params.county = filters.value.county
    if (filters.value.town) params.town = filters.value.town
    if (filters.value.bedrooms) params.bedrooms = filters.value.bedrooms
    if (priceRange.value[0] > 0) params.min_rent = priceRange.value[0]
    if (priceRange.value[1] < PRICE_MAX) params.max_rent = priceRange.value[1]
    const { data } = await propertiesApi.list(params)
    properties.value = data.data?.results || data.data || []
  } catch {
    properties.value = []
  } finally {
    loading.value = false
  }
}

const aiQuery = ref('')
const aiLoading = ref(false)
const aiError = ref('')
const aiResults = ref<{ property: Property; explanation: string }[] | null>(null)
const lastAiQuery = ref('')

async function runAiSearch() {
  if (!aiQuery.value.trim()) return
  aiLoading.value = true
  aiError.value = ''
  try {
    const { data } = await aiApi.propertySearch(aiQuery.value)
    const results = (data as any).data?.results || []
    const hydrated = await Promise.all(
      results.map(async (r: { property_id: string; explanation: string }) => {
        try {
          const { data: propData } = await propertiesApi.get(r.property_id)
          return { property: (propData as any).data, explanation: r.explanation }
        } catch {
          return null
        }
      })
    )
    aiResults.value = hydrated.filter((h): h is { property: Property; explanation: string } => h !== null)
    lastAiQuery.value = aiQuery.value
  } catch (e: any) {
    if (e?.response?.status === 503) {
      aiError.value = 'AI search is not available right now. Try the filters below instead.'
    } else {
      aiError.value = 'Search failed. Please try again.'
    }
  } finally {
    aiLoading.value = false
  }
}

function clearAiSearch() {
  aiResults.value = null
  aiQuery.value = ''
  aiError.value = ''
}

onMounted(load)

let priceDebounce: ReturnType<typeof setTimeout> | null = null
watch(priceRange, () => {
  if (priceDebounce) clearTimeout(priceDebounce)
  priceDebounce = setTimeout(load, 500)
})
</script>
