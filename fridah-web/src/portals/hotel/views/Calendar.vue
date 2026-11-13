<template>
  <div class="space-y-5">
    <div class="page-header">
      <h1 class="page-title">Availability Calendar</h1>
      <div class="flex gap-2 items-center">
        <select v-model="selectedListingId" class="input w-56" @change="load">
          <option value="">Choose a listing…</option>
          <option v-for="l in listings" :key="l.id" :value="l.id">{{ l.name }}</option>
        </select>
        <button class="btn-outline text-xs" @click="shiftMonth(-1)">‹ Prev</button>
        <span class="text-sm font-semibold w-28 text-center">{{ monthLabel }}</span>
        <button class="btn-outline text-xs" @click="shiftMonth(1)">Next ›</button>
      </div>
    </div>

    <div v-if="loading" class="card card-body animate-pulse h-64" />
    <div v-else-if="calendar" class="card overflow-x-auto">
      <table class="w-full">
        <thead class="bg-gray-50 dark:bg-gray-800/50 border-b dark:border-gray-800">
          <tr>
            <th class="table-th sticky left-0 bg-gray-50 dark:bg-gray-800/50">Room Type</th>
            <th v-for="d in calendar.days" :key="d.date" class="table-th text-center !px-2">
              {{ new Date(d.date).getDate() }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="rt in roomTypeNames" :key="rt" class="table-tr">
            <td class="table-td font-medium sticky left-0 bg-white dark:bg-gray-900">{{ rt }}</td>
            <td v-for="d in calendar.days" :key="d.date" class="table-td text-center !px-1">
              <span
                class="inline-flex items-center justify-center w-7 h-7 rounded-lg text-xs font-bold"
                :class="cellClass(d, rt)"
                :title="cellTitle(d, rt)"
              >
                {{ availableFor(d, rt) }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
      <div class="p-4 flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400 border-t dark:border-gray-800">
        <span class="flex items-center gap-1"><span class="w-3 h-3 rounded bg-emerald-100 dark:bg-emerald-950 inline-block"/> Available</span>
        <span class="flex items-center gap-1"><span class="w-3 h-3 rounded bg-amber-100 dark:bg-amber-950 inline-block"/> Limited</span>
        <span class="flex items-center gap-1"><span class="w-3 h-3 rounded bg-red-100 dark:bg-red-950 inline-block"/> Fully booked</span>
      </div>
    </div>
    <div v-else class="card card-body text-center py-12 text-gray-400 dark:text-gray-500">Choose a listing to see its calendar.</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { bookingsApi } from '@/api/services'

interface RoomTypeDay { room_type_id: string; room_type_name: string; total_rooms: number; booked_rooms: number; available_rooms: number }
interface CalendarDay { date: string; room_types: RoomTypeDay[] }
interface CalendarData { listing_name: string; days: CalendarDay[] }

const listings = ref<{ id: string; name: string }[]>([])
const selectedListingId = ref('')
const calendar = ref<CalendarData | null>(null)
const loading = ref(false)
const monthOffset = ref(0)

const monthLabel = computed(() => {
  const d = new Date()
  d.setMonth(d.getMonth() + monthOffset.value)
  return d.toLocaleDateString('en-KE', { month: 'long', year: 'numeric' })
})

const roomTypeNames = computed(() => {
  if (!calendar.value?.days.length) return []
  return calendar.value.days[0].room_types.map(rt => rt.room_type_name)
})

function availableFor(day: CalendarDay, roomTypeName: string) {
  return day.room_types.find(rt => rt.room_type_name === roomTypeName)?.available_rooms ?? '—'
}

function cellClass(day: CalendarDay, roomTypeName: string) {
  const rt = day.room_types.find(r => r.room_type_name === roomTypeName)
  if (!rt || rt.total_rooms === 0) return 'bg-gray-50 dark:bg-gray-800 text-gray-300'
  if (rt.available_rooms === 0) return 'bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-400'
  if (rt.available_rooms <= rt.total_rooms * 0.3) return 'bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-400'
  return 'bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-400'
}

function cellTitle(day: CalendarDay, roomTypeName: string) {
  const rt = day.room_types.find(r => r.room_type_name === roomTypeName)
  if (!rt) return ''
  return `${rt.available_rooms}/${rt.total_rooms} available on ${day.date}`
}

function shiftMonth(delta: number) {
  monthOffset.value += delta
  load()
}

async function loadListings() {
  const { data } = await bookingsApi.listings()
  listings.value = data.data?.results || data.data || []
}

async function load() {
  if (!selectedListingId.value) return
  loading.value = true
  try {
    const start = new Date()
    start.setMonth(start.getMonth() + monthOffset.value, 1)
    const end = new Date(start)
    end.setMonth(end.getMonth() + 1)
    const fmt = (d: Date) => d.toISOString().slice(0, 10)
    const { data } = await bookingsApi.availabilityCalendar(selectedListingId.value, fmt(start), fmt(end))
    calendar.value = data.data
  } finally { loading.value = false }
}

onMounted(loadListings)
</script>
