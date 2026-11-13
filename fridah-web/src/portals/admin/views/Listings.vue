<template>
  <div class="space-y-5">
    <h1 class="page-title">Hotel/BnB Listings</h1>
    <div class="card overflow-x-auto">
      <div v-if="loading" class="p-8 text-center text-gray-400">Loading…</div>
      <table v-else-if="listings.length" class="w-full">
        <thead class="bg-gray-50 border-b"><tr>
          <th class="table-th">Listing</th><th class="table-th">Host</th><th class="table-th">Type</th>
          <th class="table-th">Location</th><th class="table-th">Status</th><th class="table-th">Actions</th>
        </tr></thead>
        <tbody>
          <tr v-for="l in listings" :key="l.id" class="table-tr">
            <td class="table-td font-medium">{{ l.name }}</td>
            <td class="table-td text-xs">{{ l.host_name }}</td>
            <td class="table-td text-xs capitalize">{{ l.listing_type }}</td>
            <td class="table-td text-xs">{{ l.town }}, {{ l.county }}</td>
            <td class="table-td"><span :class="statusColor(l.status)" class="badge">{{ l.status.replace('_',' ') }}</span></td>
            <td class="table-td flex gap-1">
              <button v-if="l.status === 'pending_approval'" class="btn-primary bg-green-600 hover:bg-green-700 text-xs py-1 px-2" @click="approveListing(l.id,'approve')">Approve</button>
              <button v-if="l.status === 'active'" class="btn-primary bg-yellow-600 hover:bg-yellow-700 text-xs py-1 px-2" @click="approveListing(l.id,'suspend')">Suspend</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="p-10 text-center text-gray-400">No listings found.</div>
    </div>
    <p v-if="actionError" class="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg p-3">{{ actionError }}</p>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { bookingsApi } from '@/api/services'
import { statusColor } from '@/utils/formatters'
import type { Listing } from '@/types'
const listings = ref<Listing[]>([]); const loading = ref(true)
const actionError = ref('')
async function load() {
  try { const { data } = await bookingsApi.listings(); listings.value = data.data?.results || data.data || [] }
  catch (e: any) { listings.value = []; actionError.value = e?.response?.data?.error?.message || 'Failed to load listings.' }
  finally { loading.value = false }
}
async function approveListing(id: string, action: string) {
  actionError.value = ''
  try { await bookingsApi.approveListing(id, action); await load() }
  catch (e: any) {
    actionError.value = e?.response?.status === 403
      ? "You don't have admin permission for this action. (Is your account's role actually set to admin?)"
      : e?.response?.data?.error?.message || e?.message || 'Action failed - please try again.'
  }
}
onMounted(load)
</script>
