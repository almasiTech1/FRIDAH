<template>
  <div class="space-y-5">
    <div class="page-header">
      <h1 class="page-title">{{ $t('nav.renewals') }}</h1>
    </div>

    <div class="card overflow-x-auto">
      <div v-if="loading" class="p-8 text-center text-gray-400 dark:text-gray-500">{{ $t('common.loading') }}</div>
      <table v-else-if="renewals.length" class="w-full">
        <thead class="bg-gray-50 dark:bg-gray-800/50 border-b dark:border-gray-800"><tr>
          <th class="table-th">Tenant</th><th class="table-th">Unit</th>
          <th class="table-th">Current Rent</th><th class="table-th">{{ $t('renewal.proposedRent') }}</th>
          <th class="table-th">{{ $t('renewal.proposedTerm') }}</th><th class="table-th">Status</th><th class="table-th">Action</th>
        </tr></thead>
        <tbody>
          <tr v-for="r in renewals" :key="r.id" class="table-tr">
            <td class="table-td font-medium">{{ r.tenant_name }}</td>
            <td class="table-td">{{ r.property_name }} - {{ r.unit_number }}</td>
            <td class="table-td">{{ formatKES(r.current_rent_amount) }}</td>
            <td class="table-td">
              <input v-if="editingId === r.id" v-model.number="editForm.proposed_rent_amount" type="number" class="input py-1 text-sm w-28" />
              <span v-else class="font-medium">{{ formatKES(r.proposed_rent_amount) }}</span>
            </td>
            <td class="table-td text-xs">
              <template v-if="editingId === r.id">
                <input v-model="editForm.proposed_start_date" type="date" class="input py-1 text-xs mb-1" />
                <input v-model="editForm.proposed_end_date" type="date" class="input py-1 text-xs" />
              </template>
              <template v-else>{{ formatDate(r.proposed_start_date) }} - {{ formatDate(r.proposed_end_date) }}</template>
            </td>
            <td class="table-td"><span :class="statusColor(r.status)" class="badge">{{ r.status }}</span></td>
            <td class="table-td">
              <div v-if="r.status === 'pending'" class="flex gap-1">
                <template v-if="editingId === r.id">
                  <button class="btn-primary bg-landlord-600 hover:bg-landlord-700 text-xs py-1 px-2" @click="saveEdit(r.id)">{{ $t('common.save') }}</button>
                  <button class="btn-outline text-xs py-1 px-2" @click="editingId = null">{{ $t('common.cancel') }}</button>
                </template>
                <button v-else class="btn-outline text-xs py-1 px-2" @click="startEdit(r)">Edit offer</button>
              </div>
              <span v-else class="text-xs text-gray-400 dark:text-gray-500">—</span>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="p-10 text-center text-gray-400 dark:text-gray-500">No renewal offers yet - these are created automatically 60 days before a lease ends.</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { renewalsApi } from '@/api/services'
import { formatKES, formatDate, statusColor } from '@/utils/formatters'

interface Renewal {
  id: string; tenant_name: string; unit_number: string; property_name: string
  current_rent_amount: number; proposed_rent_amount: number
  proposed_start_date: string; proposed_end_date: string; status: string
}

const renewals = ref<Renewal[]>([])
const loading = ref(true)
const editingId = ref<string | null>(null)
const editForm = ref({ proposed_start_date: '', proposed_end_date: '', proposed_rent_amount: 0 })

async function load() {
  loading.value = true
  try {
    const { data } = await renewalsApi.list()
    renewals.value = data.data?.results || data.data || []
  } catch { renewals.value = [] } finally { loading.value = false }
}

function startEdit(r: Renewal) {
  editingId.value = r.id
  editForm.value = {
    proposed_start_date: r.proposed_start_date,
    proposed_end_date: r.proposed_end_date,
    proposed_rent_amount: r.proposed_rent_amount,
  }
}

async function saveEdit(id: string) {
  await renewalsApi.updateOffer(id, editForm.value)
  editingId.value = null
  await load()
}

onMounted(load)
</script>
