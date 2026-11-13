<template>
  <section v-if="hasPoint || addressText" class="fx-locmap">
    <div v-if="hasPoint && hasKey" class="h-64 rounded-2xl overflow-hidden border border-gray-100 dark:border-gray-800">
      <GoogleMapView :markers="[{ id: 'here', lat: point!.lat, lng: point!.lng, title: title || 'Location', subtitle: addressText }]"
        :center="point!" :zoom="15" />
    </div>
    <div v-else class="p-4 rounded-2xl bg-gray-50 dark:bg-gray-900 text-sm text-gray-600 dark:text-gray-300 flex items-start gap-2">
      <span>📍</span><span>{{ addressText || 'Location on request' }}</span>
    </div>
    <div class="flex flex-wrap gap-2 mt-3">
      <a :href="directionsUrl" target="_blank" rel="noopener" class="btn-primary text-xs py-2 px-4">🧭 Get directions</a>
      <a :href="openUrl" target="_blank" rel="noopener" class="btn-outline text-xs py-2 px-4">Open in Google Maps</a>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import GoogleMapView from '@/components/public/GoogleMapView.vue'
import { hasGoogleMapsApiKey } from '@/composables/useGoogleMapsApi'

/** One place on a map with directions. Works without an API key too (plain Google Maps links from the address). */
const props = defineProps<{ lat?: number | string | null; lng?: number | string | null; title?: string; addressText?: string }>()
const hasKey = hasGoogleMapsApiKey()

const point = computed(() => {
  const lat = Number(props.lat), lng = Number(props.lng)
  if (props.lat == null || props.lng == null || props.lat === '' || props.lng === '') return null
  return Number.isFinite(lat) && Number.isFinite(lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180 ? { lat, lng } : null
})
const hasPoint = computed(() => !!point.value)
const where = computed(() => (point.value ? `${point.value.lat},${point.value.lng}` : encodeURIComponent(props.addressText || '')))
const directionsUrl = computed(() => `https://www.google.com/maps/dir/?api=1&destination=${where.value}`)
const openUrl = computed(() => `https://www.google.com/maps/search/?api=1&query=${where.value}`)
</script>
