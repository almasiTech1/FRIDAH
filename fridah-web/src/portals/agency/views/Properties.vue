<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="page-title">Managed Properties</h1>
      <button class="btn-primary bg-agency-600 hover:bg-agency-700" @click="showAssign = !showAssign">+ Assign Property</button>
    </div>

    <!-- Assign form -->
    <div v-if="showAssign" class="card card-body space-y-4">
      <h2 class="section-title">Assign a Property to This Agency</h2>
      <p class="text-xs text-gray-400">
        The property owner must have already listed the property on FRIDAH. Assignment takes effect immediately
        (only the property owner or an admin can do this without a signed agreement).
      </p>
      <div class="grid grid-cols-2 gap-4">
        <div><label class="label">Property ID</label><input v-model="assignForm.property_id" class="input" placeholder="UUID of the property"/></div>
        <div><label class="label">Start Date</label><input v-model="assignForm.start_date" type="date" class="input"/></div>
        <div><label class="label">Management Fee %</label><input v-model.number="assignForm.management_fee_percent" type="number" step="0.1" class="input"/></div>
        <div><label class="label">Payout Rule</label>
          <select v-model="assignForm.payout_rule" class="input">
            <option value="owner_direct">Owner receives rent directly</option>
            <option value="agency_collects">Agency collects, then remits</option>
          </select>
        </div>
      </div>
      <div class="flex gap-3">
        <button class="btn-outline border-gray-200" @click="showAssign = false">Cancel</button>
        <button class="btn-primary bg-agency-600 hover:bg-agency-700" :disabled="assigning" @click="assign">
          <span v-if="assigning" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"/>
          <span v-else>Assign</span>
        </button>
      </div>
      <p v-if="assignError" class="text-sm text-red-600">{{ assignError }}</p>
    </div>

    <!-- List -->
    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="card animate-pulse h-20 bg-gray-100 rounded-xl"/>
    </div>
    <div v-else-if="assignments.length" class="space-y-3">
      <div v-for="a in assignments" :key="a.id" class="card card-body">
        <div class="flex items-start gap-4 flex-wrap">
          <div class="w-11 h-11 rounded-xl bg-agency-50 flex items-center justify-center text-xl flex-shrink-0">
            {{ a.item_type === 'listing' ? '🏨' : '🏢' }}
          </div>
          <div class="flex-1 min-w-[220px]">
            <div class="flex items-center gap-2 flex-wrap">
              <p class="font-semibold text-gray-900">{{ a.property_name || a.listing_name }}</p>
              <span :class="statusColor(a.status)" class="badge">{{ a.status.replace('_',' ') }}</span>
              <span class="badge badge-gray">{{ a.item_type === 'listing' ? 'Hotel / short-stay' : 'Rental property' }}</span>
            </div>
            <p class="text-xs text-gray-500 mt-0.5">{{ a.location }} · Fee {{ a.management_fee_percent }}% · {{ a.payout_rule === 'agency_collects' ? 'Agency collects' : 'Owner receives directly' }} · Since {{ formatDate(a.start_date) }}</p>
          </div>
          <div class="flex items-center gap-2 flex-shrink-0">
            <RouterLink :to="a.item_type === 'listing' ? `/agency/statements?listing=${a.listing}` : `/agency/statements?property=${a.property}`" class="btn-outline border-gray-200 text-xs">Statements</RouterLink>
            <button v-if="a.status === 'active'" class="btn-outline border-red-200 text-red-600 text-xs" @click="endAssignment(a.id)">End</button>
          </div>
        </div>

        <!-- Registered owner of the property -->
        <div class="mt-4 pt-4 border-t border-gray-100 flex items-center gap-3 flex-wrap">
          <div class="w-9 h-9 rounded-full bg-gray-100 text-gray-600 flex items-center justify-center text-sm font-bold flex-shrink-0">
            {{ (a.owner_name || '?')[0]?.toUpperCase() }}
          </div>
          <div class="flex-1 min-w-[200px]">
            <p class="text-[11px] uppercase tracking-wide text-gray-400 font-semibold">Property owner (registered on FRIDAH)</p>
            <p class="text-sm font-semibold text-gray-900">{{ a.owner_name }}</p>
          </div>
          <div class="flex items-center gap-4 text-xs text-gray-500">
            <a v-if="a.owner_phone" :href="`tel:${a.owner_phone}`" class="hover:text-agency-600">📞 {{ a.owner_phone }}</a>
            <a v-if="a.owner_email" :href="`mailto:${a.owner_email}`" class="hover:text-agency-600">✉️ {{ a.owner_email }}</a>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="card card-body text-center py-12 text-gray-400">No properties assigned yet.</div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { agencyApi } from '@/api/services'
import { statusColor, formatDate } from '@/utils/formatters'
import { useAuthStore } from '@/stores/auth'
import type { PropertyManagementAssignment } from '@/types'

const auth = useAuthStore()
const assignments = ref<PropertyManagementAssignment[]>([])
const loading = ref(true)
const showAssign = ref(false)
const assigning = ref(false)
const assignError = ref('')

const assignForm = ref({
  property_id: '', start_date: new Date().toISOString().slice(0, 10),
  management_fee_percent: 5, payout_rule: 'owner_direct' as 'owner_direct' | 'agency_collects',
})

async function load() {
  loading.value = true
  try {
    if (!auth.agencies.length) await auth.fetchAgencies()
    const agencyId = auth.agencies[0]?.id
    if (!agencyId) { assignments.value = []; return }
    const { data } = await agencyApi.assignments({ agency: agencyId })
    assignments.value = (data as any).data?.results || (data as any).data || []
  } finally {
    loading.value = false
  }
}

async function assign() {
  assigning.value = true; assignError.value = ''
  try {
    const agencyId = auth.agencies[0]?.id
    if (!agencyId) throw new Error('No agency found')
    await agencyApi.assignProperty({ ...assignForm.value, agency_id: agencyId })
    showAssign.value = false
    await load()
  } catch (e: any) {
    assignError.value = e?.response?.data?.error?.message || 'Failed to assign property.'
  } finally {
    assigning.value = false
  }
}

async function endAssignment(id: string) {
  if (!confirm('End this management assignment?')) return
  await agencyApi.endAssignment(id, 'Ended from agency portal')
  await load()
}

onMounted(load)
</script>
