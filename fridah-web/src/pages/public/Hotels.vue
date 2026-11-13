<template>
  <div>
    <section class="max-w-7xl mx-auto px-6 pt-16 pb-10">
      <p v-reveal="'fade'" class="text-brand-600 dark:text-brand-400 font-semibold text-sm uppercase tracking-widest mb-3">Hotels &amp; BnBs</p>
      <h1 v-reveal="'up'" class="text-3xl md:text-4xl font-black text-gray-900 dark:text-white mb-6">Book your stay in Kenya</h1>

      <div v-reveal="'up'" class="grid sm:grid-cols-2 md:grid-cols-4 gap-3">
        <input v-model="filters.town" placeholder="Town" class="input" @keyup.enter="load" />
        <select v-model="filters.listing_type" class="input">
          <option value="">Any type</option>
          <option value="hotel">Hotel</option>
          <option value="bnb">BnB</option>
          <option value="apartment_stay">Apartment Stay</option>
          <option value="villa">Villa</option>
        </select>
        <div class="hidden md:block" />
        <button class="btn-primary bg-brand-600 hover:bg-brand-700 justify-center" @click="load">Search</button>
      </div>

      <div class="flex justify-end items-center gap-3 mt-4">
        <button class="fx-look" :class="{ on: showSaved }" :aria-pressed="showSaved" @click="showSaved = !showSaved">♥ Saved ({{ fav.count.value }})</button>
        <div class="inline-flex rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <button class="px-4 py-2 text-sm font-semibold" :class="view === 'list' ? 'bg-brand-600 text-white' : 'bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-300'" @click="view = 'list'">List</button>
          <button class="px-4 py-2 text-sm font-semibold" :class="view === 'map' ? 'bg-brand-600 text-white' : 'bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-300'" @click="view = 'map'">Map</button>
        </div>
      </div>
    </section>

    <section v-if="view === 'map'" class="max-w-7xl mx-auto px-6 pb-24">
      <div class="h-[520px] rounded-3xl overflow-hidden border border-gray-100 dark:border-gray-800">
        <GoogleMapView :markers="mapMarkers" cluster show-near-me @location-found="onLocationFound" />
      </div>
      <p v-if="userLocation" class="text-xs text-gray-400 mt-3 text-center">
        Showing distances from your current location. List view is now sorted nearest first.
      </p>
    </section>

    <section v-else class="max-w-7xl mx-auto px-6 pb-24">
      <div v-if="loading" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <div v-for="i in 6" :key="i" class="h-72 rounded-3xl bg-gray-100 dark:bg-gray-800 animate-pulse" />
      </div>
      <div v-else-if="listings.length === 0" class="text-center py-20 text-gray-400">
        No hotels or BnBs match your search yet.
      </div>
      <div v-else class="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <div
          v-for="(l, i) in shownListings" :key="l.id" v-reveal="'up'" :style="{ transitionDelay: `${(i % 6) * 60}ms` }"
          class="rounded-3xl overflow-hidden border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 hover:shadow-card-hover hover:-translate-y-1 transition-all duration-300 cursor-pointer group"
          @click="router.push(`/hotels/${l.id}`)"
        >
          <div class="aspect-video bg-gray-100 dark:bg-gray-800 flex items-center justify-center relative overflow-hidden">
            <img v-if="l.primary_image" :src="l.primary_image" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" :alt="l.name" />
            <img v-else :src="listingFallbackImage(l.id)" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" :alt="l.name" loading="lazy" />
            <FavButton :saved="fav.has(l.id)" @toggle="toggleFav(l.id)" />
            <span class="absolute top-3 left-3 text-xs px-2 py-0.5 rounded-full bg-white/90 dark:bg-gray-900/90 font-semibold capitalize">{{ l.listing_type.replace('_',' ') }}</span>
          </div>
          <div class="p-5">
            <h3 class="font-bold text-gray-900 dark:text-white mb-1">{{ l.name }}</h3>
            <p class="text-sm text-gray-500 dark:text-gray-400 mb-3">
              {{ l.town }}, {{ l.county }}
              <span v-if="distanceFor(l) !== null" class="text-brand-600 dark:text-brand-400 font-medium">· {{ distanceFor(l)!.toFixed(1) }} km away</span>
            </p>
            <div class="flex flex-wrap gap-1.5 mb-4">
              <span v-for="a in l.amenities.slice(0, 3)" :key="a" class="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300">{{ a }}</span>
            </div>
            <div class="flex items-center justify-between">
              <p class="font-black text-brand-600 dark:text-brand-400">{{ l.min_price ? `From KES ${l.min_price.toLocaleString()}/night` : 'Contact for pricing' }}</p>
              <RouterLink :to="`/hotels/${l.id}`" class="btn-outline text-xs py-1.5 px-3" @click.stop>Book Now</RouterLink>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { bookingsApi } from '@/api/services'
import { listingFallbackImage } from '@/utils/stockImages'
import GoogleMapView from '@/components/public/GoogleMapView.vue'
import FavButton from '@/components/public/FavButton.vue'
import { useFavorites } from '@/composables/useFavorites'
import { useToastStore } from '@/stores/toasts'
import type { MapMarker } from '@/components/public/GoogleMapView.vue'
import { haversineKm } from '@/utils/geo'
import type { Listing } from '@/types'
const router = useRouter()

const listings = ref<Listing[]>([])
const loading = ref(true)
const toast = useToastStore()
const view = ref<'list' | 'map'>('list')
const fav = useFavorites('listing')
const showSaved = ref(false)
const userLocation = ref<{ lat: number; lng: number } | null>(null)
const filters = ref({ town: '', listing_type: '' })

const mapMarkers = computed<MapMarker[]>(() =>
  listings.value
    .filter((l) => l.latitude && l.longitude)
    .map((l) => ({
      id: l.id,
      lat: Number(l.latitude),
      lng: Number(l.longitude),
      title: l.name,
      subtitle: `${l.town}, ${l.county}${l.min_price ? ` · From KES ${l.min_price.toLocaleString()}/night` : ''}`,
    }))
)

function distanceFor(l: Listing): number | null {
  if (!userLocation.value || !l.latitude || !l.longitude) return null
  return haversineKm(userLocation.value, { lat: Number(l.latitude), lng: Number(l.longitude) })
}

const shownListings = computed(() => (showSaved.value ? sortedListings.value.filter((l: any) => fav.has(l.id)) : sortedListings.value))
function toggleFav(id: string) { const on = fav.toggle(id); toast.push(on ? 'Saved' : 'Removed from saved', { tone: 'info', ms: 1800 }) }
const sortedListings = computed(() => {
  if (!userLocation.value) return listings.value
  return [...listings.value].sort((a, b) => {
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
    if (filters.value.town) params.town = filters.value.town
    if (filters.value.listing_type) params.listing_type = filters.value.listing_type
    const { data } = await bookingsApi.listings(params)
    listings.value = (data as any).data?.results || (data as any).data || []
  } catch {
    listings.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
