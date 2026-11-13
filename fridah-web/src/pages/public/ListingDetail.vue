<template>
  <div>
    <div v-if="loading" class="max-w-6xl mx-auto px-6 pt-16">
      <div class="h-96 rounded-3xl bg-gray-100 dark:bg-gray-800 animate-pulse" />
    </div>

    <template v-else-if="listing">
      <!-- Photo gallery -->
      <section class="max-w-6xl mx-auto px-6 pt-10">
        <button class="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1 mb-4" @click="router.back()">&larr; Back</button>

        <div v-reveal="'zoom'" class="grid grid-cols-4 grid-rows-2 gap-2 rounded-3xl overflow-hidden h-96">
          <div
            v-if="gallery.length" class="col-span-2 row-span-2 bg-gray-100 dark:bg-gray-800 cursor-pointer overflow-hidden group"
            @click="lightboxIndex = 0"
          >
            <img :src="gallery[0]" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" alt="" />
          </div>
          <div v-else class="col-span-2 row-span-2 bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-5xl">🏨</div>
          <div
            v-for="(img, i) in gallery.slice(1, 5)" :key="i"
            class="bg-gray-100 dark:bg-gray-800 cursor-pointer relative overflow-hidden group"
            @click="lightboxIndex = i + 1"
          >
            <img :src="img" class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700" alt="" loading="lazy" />
            <div v-if="i === 3 && gallery.length > 5" class="absolute inset-0 bg-black/50 flex items-center justify-center text-white font-bold">
              +{{ gallery.length - 5 }} more
            </div>
          </div>
        </div>

        <!-- Lightbox -->
        <div v-if="lightboxIndex !== null" class="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-6 lightbox-in" @click.self="lightboxIndex = null">
          <button class="absolute top-6 right-6 text-white text-2xl" @click="lightboxIndex = null">&times;</button>
          <button v-if="gallery.length > 1" class="absolute left-6 text-white text-3xl" @click="lightboxIndex = ((lightboxIndex! - 1) + gallery.length) % gallery.length">&larr;</button>
          <img :src="gallery[lightboxIndex]" class="max-h-[85vh] max-w-[85vw] object-contain rounded-xl" />
          <button v-if="gallery.length > 1" class="absolute right-6 text-white text-3xl" @click="lightboxIndex = (lightboxIndex! + 1) % gallery.length">&rarr;</button>
        </div>
      </section>

      <section class="max-w-6xl mx-auto px-6 py-10 grid lg:grid-cols-3 gap-10">
        <div class="lg:col-span-2 space-y-8">
          <div>
            <div class="flex items-center gap-2 mb-1">
              <span class="text-xs px-2 py-0.5 rounded-full bg-brand-50 dark:bg-brand-950 text-brand-700 dark:text-brand-400 font-semibold capitalize">{{ listing.listing_type.replace('_',' ') }}</span>
            </div>
            <h1 class="text-2xl md:text-3xl font-black text-gray-900 dark:text-white">{{ listing.name }}</h1>
            <p class="text-gray-500 dark:text-gray-400 mt-1">{{ listing.address_detail ? listing.address_detail + ', ' : '' }}{{ listing.town }}, {{ listing.county }}</p>
          </div>

          <p v-if="listing.description" class="text-gray-600 dark:text-gray-300 leading-relaxed">{{ listing.description }}</p>

          <div>
            <h2 class="font-bold text-gray-900 dark:text-white mb-3">Location</h2>
            <LocationMap :lat="listing.latitude" :lng="listing.longitude" :title="listing.name"
              :address-text="[listing.address_detail, listing.town, listing.county].filter(Boolean).join(', ')" />
          </div>

          <div>
            <h2 class="font-bold text-gray-900 dark:text-white mb-3">Amenities</h2>
            <div v-if="listing.amenities?.length" class="grid grid-cols-2 sm:grid-cols-3 gap-2">
              <span v-for="a in listing.amenities" :key="a" class="text-sm text-gray-600 dark:text-gray-300 flex items-center gap-2">
                <Check class="w-4 h-4 text-brand-600" /> {{ a }}
              </span>
            </div>
            <p v-else class="text-sm text-gray-400">No amenities listed.</p>
          </div>

          <div class="grid grid-cols-2 gap-4 text-sm">
            <div class="p-4 rounded-xl bg-gray-50 dark:bg-gray-900">
              <p class="text-gray-400 text-xs mb-1">Check-in</p>
              <p class="font-semibold text-gray-900 dark:text-white">{{ listing.check_in_time }}</p>
            </div>
            <div class="p-4 rounded-xl bg-gray-50 dark:bg-gray-900">
              <p class="text-gray-400 text-xs mb-1">Check-out</p>
              <p class="font-semibold text-gray-900 dark:text-white">{{ listing.check_out_time }}</p>
            </div>
          </div>

          <div v-if="listing.cancellation_policy">
            <h2 class="font-bold text-gray-900 dark:text-white mb-2">Cancellation Policy</h2>
            <p class="text-sm text-gray-600 dark:text-gray-300">{{ listing.cancellation_policy }}</p>
          </div>
        </div>

        <!-- Booking widget -->
        <div class="lg:col-span-1">
          <div class="card p-5 sticky top-6 space-y-4">
            <h2 class="section-title">Select dates</h2>
            <div class="grid grid-cols-2 gap-3">
              <div><label class="label">Check-in</label><input v-model="dates.check_in" type="date" class="input" :min="today" @change="checkAvailability" /></div>
              <div><label class="label">Check-out</label><input v-model="dates.check_out" type="date" class="input" :min="dates.check_in || today" @change="checkAvailability" /></div>
            </div>
            <div><label class="label">Guests</label><input v-model.number="numGuests" type="number" min="1" class="input" /></div>

            <div v-if="!listing.room_types?.length" class="text-sm text-gray-400 py-4 text-center">No room types listed yet.</div>
            <div v-else class="space-y-3">
              <div
                v-for="rt in listing.room_types" :key="rt.id"
                class="p-4 rounded-xl border-2 cursor-pointer transition-colors"
                :class="selectedRoomType === rt.id ? 'border-brand-500 bg-brand-50/50 dark:bg-brand-950/30' : 'border-gray-100 dark:border-gray-800'"
                @click="selectedRoomType = rt.id"
              >
                <div class="flex items-center justify-between">
                  <p class="font-semibold text-gray-900 dark:text-white text-sm">{{ rt.name }}</p>
                  <p class="text-brand-600 dark:text-brand-400 font-bold text-sm">{{ formatKES(rt.price_per_night) }}<span class="text-gray-400 font-normal">/night</span></p>
                </div>
                <p class="text-xs text-gray-500 mt-1">Sleeps {{ rt.max_occupancy }}</p>
                <p v-if="availability[rt.id] !== undefined" class="text-xs mt-1 font-semibold" :class="availability[rt.id] > 0 ? 'text-green-600' : 'text-red-500'">
                  {{ availability[rt.id] > 0 ? `${availability[rt.id]} room(s) available` : 'Fully booked for these dates' }}
                </p>
              </div>
            </div>

            <div v-if="nights > 0 && selectedRoomTypeObj" class="pt-3 border-t border-gray-100 dark:border-gray-800 space-y-1 text-sm">
              <div class="flex justify-between text-gray-500"><span>{{ formatKES(selectedRoomTypeObj.price_per_night) }} &times; {{ nights }} night(s)</span><span>{{ formatKES(selectedRoomTypeObj.price_per_night * nights) }}</span></div>
              <div class="flex justify-between font-bold text-gray-900 dark:text-white pt-1"><span>Total</span><span>{{ formatKES(selectedRoomTypeObj.price_per_night * nights) }}</span></div>
            </div>

            <p v-if="bookError" class="text-xs text-red-600">{{ bookError }}</p>
            <button
              class="btn-primary bg-brand-600 hover:bg-brand-700 w-full justify-center"
              :disabled="!canBook || booking"
              @click="book"
            >
              <span v-if="booking" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
              <span v-else>{{ auth.isAuthenticated ? 'Book Now' : 'Log in to Book' }}</span>
            </button>
          </div>
        </div>
      </section>
    </template>

    <div v-else class="max-w-6xl mx-auto px-6 py-20 text-center text-gray-400">Listing not found.</div>
  </div>
</template>
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Check } from 'lucide-vue-next'
import { bookingsApi } from '@/api/services'
import { useAuthStore } from '@/stores/auth'
import { formatKES } from '@/utils/formatters'
import LocationMap from '@/components/public/LocationMap.vue'
import { galleryFallbackImages } from '@/utils/stockImages'
import type { Listing } from '@/types'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const listing = ref<Listing | null>(null)
const loading = ref(true)
const lightboxIndex = ref<number | null>(null)
const selectedRoomType = ref('')
const numGuests = ref(1)
const dates = ref({ check_in: '', check_out: '' })
const availability = ref<Record<string, number>>({})
const booking = ref(false)
const bookError = ref('')

const today = new Date().toISOString().slice(0, 10)

const gallery = computed(() => {
  const imgs = listing.value?.images?.map((i) => i.image) || []
  if (imgs.length) return imgs
  if (listing.value?.primary_image) return [listing.value.primary_image]
  // Host hasn't uploaded photos yet - show representative stock photos instead of an empty box
  return listing.value ? galleryFallbackImages(listing.value.id, 'listing') : []
})

const selectedRoomTypeObj = computed(() => listing.value?.room_types?.find((r) => r.id === selectedRoomType.value))

const nights = computed(() => {
  if (!dates.value.check_in || !dates.value.check_out) return 0
  const diff = (new Date(dates.value.check_out).getTime() - new Date(dates.value.check_in).getTime()) / 86400000
  return diff > 0 ? diff : 0
})

const canBook = computed(() =>
  !!selectedRoomType.value && nights.value > 0 &&
  (availability.value[selectedRoomType.value] === undefined || availability.value[selectedRoomType.value] > 0)
)

async function checkAvailability() {
  if (!dates.value.check_in || !dates.value.check_out || !listing.value?.room_types?.length) return
  for (const rt of listing.value.room_types) {
    try {
      const { data } = await bookingsApi.checkAvailability(rt.id, dates.value.check_in, dates.value.check_out)
      availability.value[rt.id] = (data as any).data?.available_rooms ?? (data as any).available_rooms ?? 0
    } catch { /* leave unset if the check fails - booking still allowed, just unconfirmed */ }
  }
}

async function book() {
  if (!auth.isAuthenticated) {
    router.push({ path: '/login', query: { redirect: route.fullPath } })
    return
  }
  bookError.value = ''
  booking.value = true
  try {
    const { data } = await bookingsApi.createBooking({
      listing: listing.value!.id,
      room_type: selectedRoomType.value,
      check_in_date: dates.value.check_in,
      check_out_date: dates.value.check_out,
      num_guests: numGuests.value,
      num_rooms: 1,
    } as any)
    const created = (data as any).data || data
    router.push(`/bookings/${created.id}`)
  } catch (e: any) {
    bookError.value = e?.response?.data?.error?.message || 'Failed to create booking. Please try again.'
  } finally {
    booking.value = false
  }
}

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await bookingsApi.getListing(route.params.id as string)
    listing.value = (data as any).data || data
  } catch {
    listing.value = null
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.lightbox-in { animation: lightbox-fade .25s ease-out; }
@keyframes lightbox-fade { from { opacity: 0 } to { opacity: 1 } }
</style>
