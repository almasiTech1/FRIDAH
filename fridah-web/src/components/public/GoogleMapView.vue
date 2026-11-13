<template>
  <div class="relative w-full h-full rounded-2xl overflow-hidden">
    <template v-if="apiKey">
      <button
        v-if="showNearMe"
        class="absolute top-3 left-3 z-10 flex items-center gap-1.5 bg-white dark:bg-gray-900 shadow-lg rounded-full px-3.5 py-2 text-xs font-semibold text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors disabled:opacity-60"
        :disabled="locating"
        @click="findNearMe"
      >
        <span v-if="locating" class="w-3 h-3 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
        <span v-else>📍</span>
        {{ locating ? 'Locating…' : 'Near me' }}
      </button>
      <GoogleMap
        :api-key="apiKey"
        :center="mapCenter"
        :zoom="mapZoom"
        :style="{ width: '100%', height: '100%' }"
        :styles="isDark ? darkMapStyles : []"
        :disable-default-ui="minimal"
      >
        <Marker
          v-if="userLocation"
          :options="{
            position: userLocation,
            icon: { path: 0, scale: 8, fillColor: '#0d9488', fillOpacity: 1, strokeColor: '#fff', strokeWeight: 2 },
            zIndex: 999,
          }"
        />
        <MarkerCluster v-if="cluster">
          <Marker
            v-for="m in markers" :key="m.id"
            :options="{ position: { lat: m.lat, lng: m.lng }, title: m.title }"
            @click="() => onMarkerClick(m)"
          />
        </MarkerCluster>
        <template v-else>
          <Marker
            v-for="m in markers" :key="m.id"
            :options="{ position: { lat: m.lat, lng: m.lng }, title: m.title }"
            @click="() => onMarkerClick(m)"
          />
        </template>
        <InfoWindow v-if="activeMarker" :options="{ position: { lat: activeMarker.lat, lng: activeMarker.lng } }" @closeclick="activeMarker = null">
          <div class="p-1 max-w-[220px]">
            <p class="font-semibold text-sm text-gray-900">{{ activeMarker.title }}</p>
            <p v-if="activeMarker.subtitle" class="text-xs text-gray-500 mt-0.5">{{ activeMarker.subtitle }}</p>
            <div class="flex items-center gap-3 mt-2">
              <RouterLink v-if="activeMarker.to" :to="activeMarker.to" class="text-xs font-semibold text-brand-600 hover:underline">
                View details →
              </RouterLink>
              <a
                :href="`https://www.google.com/maps/dir/?api=1&destination=${activeMarker.lat},${activeMarker.lng}`"
                target="_blank" rel="noopener"
                class="text-xs font-semibold text-gray-500 hover:text-gray-700 flex items-center gap-1"
              >
                🧭 Directions
              </a>
            </div>
          </div>
        </InfoWindow>
      </GoogleMap>
    </template>

    <!-- Graceful fallback when no API key is configured -->
    <div v-else class="w-full h-full flex flex-col items-center justify-center gap-2 bg-gray-100 dark:bg-gray-800 text-center p-6">
      <span class="text-3xl">🗺️</span>
      <p class="text-sm font-medium text-gray-500 dark:text-gray-400">Map unavailable</p>
      <p class="text-xs text-gray-400 dark:text-gray-500 max-w-[220px]">
        Set <code class="px-1 py-0.5 rounded bg-gray-200 dark:bg-gray-700">VITE_GOOGLE_MAPS_API_KEY</code> to enable interactive maps.
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { GoogleMap, Marker, MarkerCluster, InfoWindow } from 'vue3-google-map'
import { useThemeStore } from '@/stores/theme'

export interface MapMarker {
  id: string
  lat: number
  lng: number
  title: string
  subtitle?: string
  to?: string
}

const props = withDefaults(defineProps<{
  markers: MapMarker[]
  center?: { lat: number; lng: number }
  zoom?: number
  cluster?: boolean
  minimal?: boolean
  showNearMe?: boolean
}>(), {
  center: () => ({ lat: -1.286389, lng: 36.817223 }), // Nairobi
  zoom: 12,
  cluster: false,
  minimal: false,
  showNearMe: false,
})

const emit = defineEmits<{
  (e: 'location-found', location: { lat: number; lng: number }): void
}>()

const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string | undefined
const theme = useThemeStore()
const isDark = computed(() => theme.isDark)
const activeMarker = ref<MapMarker | null>(null)
const userLocation = ref<{ lat: number; lng: number } | null>(null)
const locating = ref(false)

// Once the user locates themselves, recenter/zoom the map on them instead of the default center.
const mapCenter = computed(() => userLocation.value || props.center)
const mapZoom = computed(() => (userLocation.value ? 13 : props.zoom))

function onMarkerClick(m: MapMarker) {
  activeMarker.value = m
}

function findNearMe() {
  if (!navigator.geolocation) return
  locating.value = true
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const location = { lat: pos.coords.latitude, lng: pos.coords.longitude }
      userLocation.value = location
      locating.value = false
      emit('location-found', location)
    },
    () => {
      locating.value = false
    },
    { enableHighAccuracy: true, timeout: 10000 }
  )
}

// icon.path: 0 = google.maps.SymbolPath.CIRCLE (numeric literal used since `google` isn't
// guaranteed loaded at module-eval time, only once the map itself has mounted).
const darkMapStyles = [
  { elementType: 'geometry', stylers: [{ color: '#1f2530' }] },
  { elementType: 'labels.text.stroke', stylers: [{ color: '#1f2530' }] },
  { elementType: 'labels.text.fill', stylers: [{ color: '#9099ab' }] },
  { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#2a3140' }] },
  { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#0d1520' }] },
  { featureType: 'poi', elementType: 'labels', stylers: [{ visibility: 'off' }] },
]
</script>
