<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="page-title">Leases</h1>
      <button class="btn-primary bg-landlord-600 hover:bg-landlord-700" @click="showForm = !showForm">+ New Lease</button>
    </div>
    <div v-if="showForm" class="card card-body space-y-4">
      <h2 class="section-title">Create Lease</h2>
      <div class="grid grid-cols-2 gap-4">
        <div><label class="label">Tenant Phone / Email</label><input v-model="form.tenant_search" class="input" placeholder="Search by email…"/></div>
        <div><label class="label">Unit ID</label><input v-model="form.unit" class="input" placeholder="Unit UUID"/></div>
        <div><label class="label">Start Date</label><input v-model="form.start_date" class="input" type="date"/></div>
        <div><label class="label">End Date (optional)</label><input v-model="form.end_date" class="input" type="date"/></div>
        <div><label class="label">Monthly Rent (KES)</label><input v-model.number="form.rent_amount" class="input" type="number"/></div>
        <div><label class="label">Deposit (KES)</label><input v-model.number="form.deposit_amount" class="input" type="number"/></div>
        <div><label class="label">Rent Due Day</label><input v-model.number="form.rent_due_day" class="input" type="number" min="1" max="28"/></div>
      </div>
      <div class="flex gap-3">
        <button class="btn-outline border-gray-200" @click="showForm = false">Cancel</button>
        <button class="btn-primary bg-landlord-600 hover:bg-landlord-700" :disabled="saving" @click="create">
          <span v-if="saving" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"/>
          <span v-else>Create Lease</span>
        </button>
      </div>
    </div>
    <TableToolbar v-model="q" :count="rows.length" :total="leases.length" :rows="rows" title="Leases" />
    <div class="card overflow-x-auto">
      <div v-if="loading" class="p-8 text-center text-gray-400">Loading…</div>
      <table v-else-if="leases.length" class="w-full">
        <thead class="bg-gray-50 border-b"><tr>
          <th class="table-th">Tenant</th><th class="table-th">Property</th><th class="table-th">Unit</th>
          <th class="table-th">Rent</th><th class="table-th">Start</th><th class="table-th">Status</th><th class="table-th">Action</th>
        </tr></thead>
        <tbody>
          <tr v-for="l in rows" :key="l.id" class="table-tr">
            <td class="table-td font-medium">{{ l.tenant_name }}</td>
            <td class="table-td text-xs">{{ l.property_name }}</td>
            <td class="table-td">{{ l.unit_number }}</td>
            <td class="table-td font-medium">{{ formatKES(l.rent_amount) }}</td>
            <td class="table-td">{{ formatDate(l.start_date) }}</td>
            <td class="table-td"><span :class="statusColor(l.status)" class="badge">{{ l.status }}</span></td>
            <td class="table-td">
              <button v-if="l.status === 'pending'" class="btn-primary bg-landlord-600 hover:bg-landlord-700 text-xs py-1 px-2" @click="activate(l.id)">Activate</button>
              <button v-if="l.status === 'active'" class="btn-primary bg-red-600 hover:bg-red-700 text-xs py-1 px-2" @click="terminate(l.id)">Terminate</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="p-10 text-center text-gray-400">No leases yet.</div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { useRowSearch } from '@/composables/useRowSearch'
import TableToolbar from '@/components/ui/TableToolbar.vue'
import { ref, onMounted } from 'vue'
import { rentalsApi } from '@/api/services'
import { formatKES, formatDate, statusColor } from '@/utils/formatters'
import type { Lease } from '@/types'
const leases = ref<Lease[]>([])
const { q, rows } = useRowSearch(() => leases.value as any[], 'leases')
const loading = ref(true); const showForm = ref(false); const saving = ref(false)
const form = ref({ tenant_search:'', unit:'', start_date:'', end_date:'', rent_amount:0, deposit_amount:0, rent_due_day:5, tenant:'' })
async function load() {
  try { const { data } = await rentalsApi.leases(); leases.value = data.data?.results || data.data || [] }
  catch { leases.value = [] } finally { loading.value = false }
}
async function create() { saving.value = true; try { await rentalsApi.createLease(form.value as any); showForm.value = false; await load() } finally { saving.value = false } }
async function activate(id: string) { await rentalsApi.activateLease(id); await load() }
async function terminate(id: string) { if (!confirm('Terminate this lease?')) return; await rentalsApi.terminateLease(id, 'Terminated by landlord'); await load() }
onMounted(load)
</script>
