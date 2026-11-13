<template>
  <div class="space-y-5">
    <h1 class="page-title">Maintenance Requests</h1>
    <div class="flex gap-2">
      <select v-model="statusFilter" class="input w-auto text-sm">
        <option value="">All</option><option value="open">Open</option><option value="assigned">Assigned</option>
        <option value="in_progress">In Progress</option><option value="resolved">Resolved</option>
      </select>
    </div>
    <div v-if="loading" class="text-center py-10 text-gray-400">Loading…</div>
    <div v-else-if="!filtered.length" class="card card-body text-center py-10 text-gray-400">No maintenance requests.</div>
    <div v-else class="space-y-3">
      <div v-for="req in filtered" :key="req.id" class="card card-body">
        <div class="flex items-start justify-between gap-3">
          <div class="flex-1">
            <div class="flex items-center gap-2 flex-wrap">
              <p class="font-medium text-gray-900 text-sm">{{ req.title }}</p>
              <span :class="priorityBadge(req.priority)" class="badge">{{ req.priority }}</span>
              <span :class="statusColor(req.status)" class="badge">{{ req.status.replace('_',' ') }}</span>
            </div>
            <p class="text-xs text-gray-500 mt-0.5">{{ req.property_name }} — Unit {{ req.unit_number }} · {{ req.tenant_name }}</p>
            <p class="text-sm text-gray-600 mt-2">{{ req.description }}</p>
          </div>
          <div v-if="req.status === 'open'" class="flex-shrink-0">
            <button class="btn-primary bg-landlord-600 hover:bg-landlord-700 text-xs" @click="openAssign(req.id)">Assign Provider</button>
          </div>
        </div>
        <div v-if="assigning === req.id" class="mt-3 pt-3 border-t border-gray-50 flex gap-2">
          <input v-model="providerId" class="input flex-1 text-sm" placeholder="Provider UUID"/>
          <button class="btn-primary bg-landlord-600 hover:bg-landlord-700 text-sm" @click="assign(req.id)">Assign</button>
        </div>
      </div>
    </div>
    <p v-if="actionError" class="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg p-3">{{ actionError }}</p>
  </div>
</template>
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { rentalsApi } from '@/api/services'
import { statusColor } from '@/utils/formatters'
import type { MaintenanceRequest } from '@/types'
const requests = ref<MaintenanceRequest[]>([]); const loading = ref(true)
const statusFilter = ref(''); const assigning = ref(''); const providerId = ref('')
const actionError = ref('')
const filtered = computed(() => statusFilter.value ? requests.value.filter(r => r.status === statusFilter.value) : requests.value)
const priorityBadge = (p: string) => ({ low:'badge-gray', medium:'badge-blue', high:'badge-yellow', urgent:'badge-red' }[p] || 'badge-gray')
async function load() {
  try { const { data } = await rentalsApi.maintenanceList(); requests.value = data.data?.results || data.data || [] }
  catch (e: any) { requests.value = []; actionError.value = e?.response?.data?.error?.message || 'Failed to load maintenance requests.' }
  finally { loading.value = false }
}
function openAssign(id: string) { assigning.value = assigning.value === id ? '' : id; providerId.value = '' }
async function assign(id: string) {
  actionError.value = ''
  try { await rentalsApi.assignMaintenance(id, providerId.value); assigning.value = ''; await load() }
  catch (e: any) { actionError.value = e?.response?.data?.error?.message || 'Failed to assign provider - check the UUID is correct.' }
}
onMounted(load)
</script>
