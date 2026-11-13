<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between flex-wrap gap-3">
      <h1 class="page-title">Bookings</h1>
      <select v-model="statusFilter" class="input w-auto text-sm">
        <option value="">All</option>
        <option value="pending_payment">Pending Payment</option>
        <option value="confirmed">Confirmed</option>
        <option value="checked_in">Checked In</option>
        <option value="checked_out">Checked Out</option>
        <option value="cancelled">Cancelled</option>
      </select>
    </div>

    <TableToolbar v-model="q" :count="rows.length" :total="filtered.length" :rows="rows" title="Bookings" />
    <div class="card overflow-x-auto">
      <div v-if="loading" class="p-8 text-center text-gray-400">Loading…</div>
      <table v-else-if="filtered.length" class="w-full">
        <thead class="bg-gray-50 border-b border-gray-100"><tr>
          <th class="table-th">Ref</th>
          <th class="table-th">Guest</th>
          <th class="table-th">Room</th>
          <th class="table-th">Check-in</th>
          <th class="table-th">Check-out</th>
          <th class="table-th">Nights</th>
          <th class="table-th">Amount</th>
          <th class="table-th">Status</th>
          <th class="table-th">Actions</th>
        </tr></thead>
        <tbody>
          <tr v-for="b in rows" :key="b.id" class="table-tr">
            <td class="table-td font-mono text-xs font-medium">{{ b.booking_reference }}</td>
            <td class="table-td">
              <p class="font-medium text-sm">{{ b.guest_name }}</p>
              <p class="text-xs text-gray-400">{{ b.num_guests }} guest(s)</p>
            </td>
            <td class="table-td text-xs">{{ b.room_type_name }}</td>
            <td class="table-td text-xs">{{ formatDate(b.check_in_date) }}</td>
            <td class="table-td text-xs">{{ formatDate(b.check_out_date) }}</td>
            <td class="table-td text-center">{{ b.nights }}</td>
            <td class="table-td font-medium">{{ formatKES(b.total_amount) }}</td>
            <td class="table-td"><span :class="statusColor(b.status)" class="badge text-xs">{{ b.status.replace('_',' ') }}</span></td>
            <td class="table-td">
              <div class="flex gap-1 flex-wrap">
                <button v-if="b.status === 'confirmed'" class="btn-primary bg-hotel-600 hover:bg-hotel-700 text-xs py-1 px-2" @click="doCheckIn(b.id)">Check In</button>
                <button v-if="b.status === 'checked_in'" class="btn-primary bg-green-600 hover:bg-green-700 text-xs py-1 px-2" @click="doCheckOut(b.id)">Check Out</button>
                <button v-if="b.status === 'confirmed'" class="btn-primary bg-red-600 hover:bg-red-700 text-xs py-1 px-2" @click="doCancel(b.id)">Cancel</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="p-10 text-center text-gray-400">
        <p class="text-3xl mb-3">📅</p>
        <p>No bookings found.</p>
      </div>
    </div>
    <p v-if="actionError" class="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg p-3">{{ actionError }}</p>
  </div>
</template>
<script setup lang="ts">
import { useRowSearch } from '@/composables/useRowSearch'
import TableToolbar from '@/components/ui/TableToolbar.vue'
import { ref, computed, onMounted } from 'vue'
import { bookingsApi } from '@/api/services'
import { formatKES, formatDate, statusColor } from '@/utils/formatters'
import type { Booking } from '@/types'
const bookings = ref<Booking[]>([])
const loading = ref(true)
const statusFilter = ref('')
const actionError = ref('')
const filtered = computed(() => statusFilter.value ? bookings.value.filter(b => b.status === statusFilter.value) : bookings.value)
const { q, rows } = useRowSearch(() => filtered.value as any[], 'bookings')
async function load() {
  try { const { data } = await bookingsApi.bookings(); bookings.value = data.data?.results || data.data || [] }
  catch (e: any) { bookings.value = []; actionError.value = e?.response?.data?.error?.message || 'Failed to load bookings.' }
  finally { loading.value = false }
}
async function doCheckIn(id: string) {
  actionError.value = ''
  try { await bookingsApi.checkIn(id); await load() }
  catch (e: any) { actionError.value = e?.response?.data?.error?.message || 'Check-in failed.' }
}
async function doCheckOut(id: string) {
  actionError.value = ''
  try { await bookingsApi.checkOut(id); await load() }
  catch (e: any) { actionError.value = e?.response?.data?.error?.message || 'Check-out failed.' }
}
async function doCancel(id: string) {
  if (!confirm('Cancel this booking?')) return
  actionError.value = ''
  try { await bookingsApi.cancelBooking(id, 'Cancelled by host'); await load() }
  catch (e: any) { actionError.value = e?.response?.data?.error?.message || 'Cancellation failed.' }
}
onMounted(load)
</script>
