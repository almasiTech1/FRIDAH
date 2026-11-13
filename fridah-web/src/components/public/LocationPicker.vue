<template>
  <div v-if="hasKey" class="fx-picker">
    <div class="flex items-center justify-between gap-2 mb-2">
      <p class="text-xs text-gray-500">Click the map or drag the pin to the exact entrance.</p>
      <button type="button" class="text-xs font-semibold text-brand-600 hover:underline disabled:opacity-50" :disabled="locating" @click="useMyLocation">
        {{ locating ? 'Locating…' : '📍 Use my location' }}
      </button>
    </div>
    <div class="h-56 rounded-2xl overflow-hidden border border-gray-200 dark:border-gray-700">
      <GoogleMap :api-key="apiKey" :center="center" :zoom="point ? 16 : 11" :style="{ width: '100%', height: '100%' }" @click="onMapClick">
        <Marker v-if="point" :options="{ position: point, draggable: true }" @dragend="onDragEnd" />
      </GoogleMap>
    </div>
    <p v-if="point" class="text-xs text-emerald-600 dark:text-emerald-400 mt-1.5">📍 Pinned at {{ point.lat.toFixed(5) }}, {{ point.lng.toFixed(5) }}</p>
    <p v-else class="text-xs text-gray-400 mt-1.5">No pin yet — pick an address above or click the map.</p>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { GoogleMap, Marker } from 'vue3-google-map'

const props = defineProps<{ lat?: number | null; lng?: number | null }>()
const emit = defineEmits<{ (e: 'update', p: { lat: number; lng: number }): void }>()

const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string | undefined
const hasKey = Boolean(apiKey)
const locating = ref(false)
const NAIROBI = { lat: -1.286389, lng: 36.817223 }

const point = computed(() => (props.lat != null && props.lng != null && Number.isFinite(Number(props.lat)) && Number.isFinite(Number(props.lng)) ? { lat: Number(props.lat), lng: Number(props.lng) } : null))
const center = computed(() => point.value ?? NAIROBI)

const round6 = (n: number) => Math.round(n * 1e6) / 1e6
function set(lat: number, lng: number) {
  if (!Number.isFinite(lat) || !Number.isFinite(lng) || Math.abs(lat) > 90 || Math.abs(lng) > 180) return
  emit('update', { lat: round6(lat), lng: round6(lng) })
}
function onMapClick(e: google.maps.MapMouseEvent) { if (e.latLng) set(e.latLng.lat(), e.latLng.lng()) }
function onDragEnd(e: google.maps.MapMouseEvent) { if (e.latLng) set(e.latLng.lat(), e.latLng.lng()) }
function useMyLocation() {
  if (!navigator.geolocation) return
  locating.value = true
  navigator.geolocation.getCurrentPosition(
    (pos) => { locating.value = false; set(pos.coords.latitude, pos.coords.longitude) },
    () => { locating.value = false },
    { enableHighAccuracy: true, timeout: 10000 },
  )
}
</script>
