<template>
  <div>
    <label v-if="label" class="label">{{ label }}</label>

    <!-- Google's place-search widget (needs the "Places API (New)" enabled on your key) -->
    <div v-if="hasKey && !failed" ref="host" class="fx-place-host" />

    <!-- No key, or Google refused the request: plain typing still works, and the pin can be set on the map -->
    <input v-else v-model="query" type="text" class="input" :placeholder="placeholder || 'Start typing an address…'" @input="onManualInput" />

    <p v-if="hasKey && !failed && !ready" class="text-xs text-gray-400 mt-1">Loading address search…</p>
    <p v-if="!hasKey" class="text-xs text-gray-400 mt-1">Address search unavailable — Google Maps API key not configured. Enter details manually below.</p>
    <p v-else-if="failed" class="text-xs text-amber-600 mt-1">Address search is unavailable right now. Type the address and place the pin on the map instead.</p>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { usePlacesLibrary, hasGoogleMapsApiKey } from '@/composables/useGoogleMapsApi'

export interface PlaceSelection {
  formattedAddress: string
  lat: number
  lng: number
  county: string
  town: string
}

const props = defineProps<{ label?: string; placeholder?: string; modelValue?: string }>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'place-selected', place: PlaceSelection): void
  (e: 'cleared'): void
}>()

const host = ref<HTMLElement | null>(null)
const query = ref(props.modelValue || '')
const ready = ref(false)
const failed = ref(false)
const hasKey = hasGoogleMapsApiKey()
let element: google.maps.places.PlaceAutocompleteElement | null = null

// The database stores 6 decimals (about 10 cm); Google sends ~15.
const round6 = (n: number) => Math.round(n * 1e6) / 1e6
const num = (v: unknown) => (typeof v === 'function' ? (v as () => number)() : Number(v))

watch(() => props.modelValue, (v) => {
  if (v === undefined || v === query.value) return
  query.value = v
  if (element && element.value !== v) element.value = v
})

function onManualInput() {
  emit('update:modelValue', query.value)
  if (query.value === '') emit('cleared')
}

function component(list: google.maps.places.AddressComponent[] | undefined, type: string) {
  return list?.find((c) => c.types.includes(type))?.longText || ''
}

async function onSelect(event: Event) {
  try {
    const place = (event as google.maps.places.PlacePredictionSelectEvent).placePrediction.toPlace()
    await place.fetchFields({ fields: ['formattedAddress', 'location', 'addressComponents'] })
    const loc = place.location
    if (!loc) return
    const county = component(place.addressComponents, 'administrative_area_level_1')
    const town = component(place.addressComponents, 'locality') || component(place.addressComponents, 'administrative_area_level_2')
    query.value = place.formattedAddress || query.value
    emit('update:modelValue', query.value)
    emit('place-selected', { formattedAddress: place.formattedAddress || '', lat: round6(num(loc.lat)), lng: round6(num(loc.lng)), county, town })
  } catch {
    failed.value = true                                   // e.g. the Places API (New) is not enabled for this key
  }
}

function onTyping() {
  if (!element) return
  query.value = element.value
  emit('update:modelValue', query.value)
  if (query.value === '') emit('cleared')
}

onMounted(async () => {
  if (!hasKey) return
  try {
    const places = await usePlacesLibrary()
    if (!places || !host.value) return
    element = new places.PlaceAutocompleteElement({ includedRegionCodes: ['ke'] })
    element.placeholder = props.placeholder || 'Start typing an address…'
    if (query.value) element.value = query.value
    element.addEventListener('gmp-select', onSelect)
    element.addEventListener('gmp-error', () => { failed.value = true })
    element.addEventListener('input', onTyping)
    host.value.appendChild(element)
    ready.value = true
  } catch {
    failed.value = true
  }
})

onBeforeUnmount(() => {
  element?.removeEventListener('gmp-select', onSelect)
  element?.removeEventListener('input', onTyping)
  element?.remove()
  element = null
})
</script>

<style scoped>
.fx-place-host :deep(gmp-place-autocomplete) { display: block; width: 100%; color-scheme: light; border-radius: 14px; }
:global(html.dark) .fx-place-host :deep(gmp-place-autocomplete) { color-scheme: dark; }
</style>
