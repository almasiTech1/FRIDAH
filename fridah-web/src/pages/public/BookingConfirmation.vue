<template>
  <div class="max-w-2xl mx-auto px-6 py-16">
    <div v-if="loading" class="h-64 rounded-3xl bg-gray-100 dark:bg-gray-800 animate-pulse" />

    <template v-else-if="booking">
      <div class="text-center mb-8">
        <div class="w-16 h-16 rounded-full bg-green-100 dark:bg-green-950 flex items-center justify-center mx-auto mb-4">
          <Check class="w-8 h-8 text-green-600" />
        </div>
        <h1 class="text-2xl font-black text-gray-900 dark:text-white">Booking Requested</h1>
        <p class="text-gray-500 dark:text-gray-400 mt-1">Reference: <span class="font-mono font-semibold">{{ booking.booking_reference }}</span></p>
      </div>

      <div class="card p-6 space-y-4">
        <div class="flex justify-between items-center pb-4 border-b border-gray-100 dark:border-gray-800">
          <div>
            <p class="font-bold text-gray-900 dark:text-white">{{ booking.listing_name }}</p>
            <p class="text-sm text-gray-500">{{ booking.room_type_name }}</p>
          </div>
          <span class="badge" :class="statusBadge(booking.status)">{{ booking.status.replace('_', ' ') }}</span>
        </div>

        <div class="grid grid-cols-2 gap-4 text-sm">
          <div><p class="text-gray-400 text-xs mb-1">Check-in</p><p class="font-semibold text-gray-900 dark:text-white">{{ formatDate(booking.check_in_date) }}</p></div>
          <div><p class="text-gray-400 text-xs mb-1">Check-out</p><p class="font-semibold text-gray-900 dark:text-white">{{ formatDate(booking.check_out_date) }}</p></div>
          <div><p class="text-gray-400 text-xs mb-1">Guests</p><p class="font-semibold text-gray-900 dark:text-white">{{ booking.num_guests }}</p></div>
          <div><p class="text-gray-400 text-xs mb-1">Nights</p><p class="font-semibold text-gray-900 dark:text-white">{{ booking.nights }}</p></div>
        </div>

        <div class="pt-4 border-t border-gray-100 dark:border-gray-800 flex justify-between items-center">
          <span class="text-sm text-gray-500">Total amount</span>
          <span class="text-xl font-black text-gray-900 dark:text-white">{{ formatKES(booking.total_amount) }}</span>
        </div>

        <p v-if="booking.status === 'pending_payment'" class="text-xs text-amber-600 bg-amber-50 dark:bg-amber-950 p-3 rounded-xl">
          Your booking is reserved pending payment. Complete payment from your dashboard to confirm it.
        </p>
      </div>

      <div class="flex gap-3 mt-6">
        <router-link to="/" class="btn-outline border-gray-200 flex-1 justify-center">Back to Home</router-link>
        <router-link to="/hotels" class="btn-primary bg-brand-600 hover:bg-brand-700 flex-1 justify-center">Browse More Stays</router-link>
      </div>
    </template>

    <div v-else class="text-center py-20 text-gray-400">Booking not found.</div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Check } from 'lucide-vue-next'
import { bookingsApi } from '@/api/services'
import { formatKES, formatDate } from '@/utils/formatters'
import type { Booking } from '@/types'

const route = useRoute()
const booking = ref<Booking | null>(null)
const loading = ref(true)

function statusBadge(status: string) {
  return {
    pending_payment: 'badge-yellow', confirmed: 'badge-green', checked_in: 'badge-green',
    checked_out: 'badge-gray', cancelled: 'badge-red',
  }[status] || 'badge-gray'
}

onMounted(async () => {
  try {
    const { data } = await bookingsApi.getBooking(route.params.id as string)
    booking.value = (data as any).data || data
  } catch {
    booking.value = null
  } finally {
    loading.value = false
  }
})
</script>
