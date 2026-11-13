<template>
  <div class="max-w-4xl mx-auto px-6 py-12">
    <h1 class="text-2xl font-black text-gray-900 dark:text-white mb-6">My Bookings</h1>

    <div class="flex gap-2 mb-6">
      <button
        v-for="f in filters" :key="f.value"
        class="px-3 py-1.5 rounded-full text-xs font-semibold transition-colors"
        :class="filter === f.value ? 'bg-brand-600 text-white' : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'"
        @click="filter = f.value"
      >{{ f.label }}</button>
    </div>

    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="h-24 rounded-2xl bg-gray-100 dark:bg-gray-800 animate-pulse" />
    </div>

    <div v-else-if="!filtered.length" class="text-center py-16 text-gray-400">
      <p class="mb-3">No bookings here yet.</p>
      <RouterLink to="/hotels" class="btn-primary bg-brand-600 hover:bg-brand-700 inline-flex">Browse Stays</RouterLink>
    </div>

    <div v-else class="space-y-3">
      <RouterLink
        v-for="b in filtered" :key="b.id" :to="`/bookings/${b.id}`"
        class="block rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 hover:shadow-md transition-shadow"
      >
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="font-bold text-gray-900 dark:text-white">{{ b.listing_name }}</p>
            <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{{ b.room_type_name }}</p>
            <p class="text-sm text-gray-500 dark:text-gray-400 mt-2">{{ formatDate(b.check_in_date) }} &rarr; {{ formatDate(b.check_out_date) }} &middot; {{ b.nights }} night(s)</p>
          </div>
          <div class="text-right shrink-0">
            <span class="badge text-xs" :class="statusBadge(b.status)">{{ b.status.replace('_', ' ') }}</span>
            <p class="font-bold text-gray-900 dark:text-white mt-2">{{ formatKES(b.total_amount) }}</p>
          </div>
        </div>
        <div v-if="b.status === 'confirmed' || b.status === 'checked_in'" class="mt-3 pt-3 border-t border-gray-50 dark:border-gray-800">
          <button
            class="text-xs font-semibold text-red-600 hover:underline"
            @click.stop.prevent="cancel(b)"
          >Cancel booking</button>
        </div>
      </RouterLink>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { bookingsApi } from '@/api/services'
import { formatKES, formatDate } from '@/utils/formatters'
import type { Booking } from '@/types'

const bookings = ref<Booking[]>([])
const loading = ref(true)
const filter = ref('all')

const filters = [
  { value: 'all', label: 'All' },
  { value: 'upcoming', label: 'Upcoming' },
  { value: 'past', label: 'Past' },
  { value: 'cancelled', label: 'Cancelled' },
]

const filtered = computed(() => {
  const today = new Date().toISOString().slice(0, 10)
  if (filter.value === 'upcoming') return bookings.value.filter((b) => b.check_out_date >= today && b.status !== 'cancelled')
  if (filter.value === 'past') return bookings.value.filter((b) => b.check_out_date < today && b.status !== 'cancelled')
  if (filter.value === 'cancelled') return bookings.value.filter((b) => b.status === 'cancelled')
  return bookings.value
})

function statusBadge(status: string) {
  return {
    pending_payment: 'badge-yellow', confirmed: 'badge-green', checked_in: 'badge-green',
    checked_out: 'badge-gray', cancelled: 'badge-red',
  }[status] || 'badge-gray'
}

async function load() {
  loading.value = true
  try {
    const { data } = await bookingsApi.bookings()
    bookings.value = ((data as any).results || (data as any).data || []).sort(
      (a: Booking, b: Booking) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )
  } catch { bookings.value = [] } finally { loading.value = false }
}

async function cancel(b: Booking) {
  const reason = window.prompt('Reason for cancelling (optional):') || ''
  if (!window.confirm('Cancel this booking? This cannot be undone.')) return
  await bookingsApi.cancelBooking(b.id, reason)
  await load()
}

onMounted(load)
</script>
