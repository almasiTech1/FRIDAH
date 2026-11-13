<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between flex-wrap gap-3">
      <h1 class="page-title">Room Types</h1>
      <div class="flex gap-2">
        <select v-model="selectedListing" class="input text-sm w-48">
          <option value="">Select listing…</option>
          <option v-for="l in listings" :key="l.id" :value="l.id">{{ l.name }}</option>
        </select>
        <button class="btn-primary bg-hotel-600 hover:bg-hotel-700" @click="showForm = !showForm" :disabled="!selectedListing">+ Add Room</button>
      </div>
    </div>

    <div v-if="showForm && selectedListing" class="card card-body space-y-4">
      <h2 class="section-title">New Room Type</h2>
      <div class="grid grid-cols-2 gap-4">
        <div><label class="label">Name</label><input v-model="form.name" class="input" placeholder="Deluxe Room"/></div>
        <div><label class="label">Max Occupancy</label><input v-model.number="form.max_occupancy" class="input" type="number" min="1"/></div>
        <div><label class="label">Price Per Night (KES)</label><input v-model.number="form.price_per_night" class="input" type="number" min="1"/></div>
        <div><label class="label">Total Rooms</label><input v-model.number="form.total_rooms" class="input" type="number" min="1"/></div>
      </div>
      <div><label class="label">Description</label><textarea v-model="form.description" class="input resize-none" rows="2"/></div>
      <div class="flex gap-3">
        <button class="btn-outline border-gray-200" @click="showForm = false">Cancel</button>
        <button class="btn-primary bg-hotel-600 hover:bg-hotel-700" :disabled="saving" @click="addRoom">
          <span v-if="saving" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"/>
          <span v-else>Add Room Type</span>
        </button>
      </div>
    </div>

    <div v-if="loadingRooms" class="text-center py-8 text-gray-400">Loading rooms…</div>
    <div v-else-if="!selectedListing" class="card card-body text-center py-12 text-gray-400">
      <p class="text-3xl mb-3">🛏️</p><p>Select a listing to view its room types.</p>
    </div>
    <div v-else-if="!rooms.length" class="card card-body text-center py-10 text-gray-400">No room types yet for this listing.</div>
    <div v-else class="space-y-3">
      <div v-for="r in rooms" :key="r.id" class="card card-body flex items-center gap-4">
        <div class="flex-1">
          <p class="font-semibold text-gray-900">{{ r.name }}</p>
          <div class="flex gap-3 mt-1 text-xs text-gray-500 flex-wrap">
            <span>👥 Max {{ r.max_occupancy }} guests</span>
            <span>🏷️ {{ formatKES(r.price_per_night) }}/night</span>
            <span>🛏️ {{ r.total_rooms }} rooms</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { bookingsApi } from '@/api/services'
import { formatKES } from '@/utils/formatters'
import type { Listing, RoomType } from '@/types'
const listings = ref<Listing[]>([])
const rooms = ref<RoomType[]>([])
const selectedListing = ref('')
const loading = ref(true); const loadingRooms = ref(false); const showForm = ref(false); const saving = ref(false)
const form = ref({ name: '', max_occupancy: 2, price_per_night: 3500, total_rooms: 1, description: '' })
async function loadListings() { try { const { data } = await bookingsApi.listings(); listings.value = data.data?.results || data.data || [] } finally { loading.value = false } }
async function loadRooms() {
  if (!selectedListing.value) { rooms.value = []; return }
  loadingRooms.value = true
  try { const { data } = await bookingsApi.roomTypes(selectedListing.value); rooms.value = data.data?.results || data.data || [] }
  catch { rooms.value = [] } finally { loadingRooms.value = false }
}
async function addRoom() {
  saving.value = true
  try { await bookingsApi.createRoomType(selectedListing.value, form.value as any); showForm.value = false; await loadRooms() }
  finally { saving.value = false }
}
watch(selectedListing, loadRooms)
onMounted(loadListings)
</script>
