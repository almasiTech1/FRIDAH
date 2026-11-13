<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="page-title">Units</h1>
      <button class="btn-primary bg-landlord-600 hover:bg-landlord-700" @click="showForm = !showForm">+ Add Unit</button>
    </div>
    <div v-if="showForm" class="card card-body space-y-4">
      <h2 class="section-title">New Unit</h2>
      <div class="grid grid-cols-2 gap-4">
        <div><label class="label">Property</label>
          <select v-model="form.property" class="input">
            <option v-for="p in properties" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </div>
        <div><label class="label">Unit Number</label><input v-model="form.unit_number" class="input" placeholder="A1"/></div>
        <div><label class="label">Bedrooms</label><input v-model.number="form.bedrooms" class="input" type="number" min="0"/></div>
        <div><label class="label">Bathrooms</label><input v-model.number="form.bathrooms" class="input" type="number" min="1"/></div>
        <div><label class="label">Rent (KES)</label><input v-model.number="form.rent_amount" class="input" type="number"/></div>
        <div><label class="label">Deposit (KES)</label><input v-model.number="form.deposit_amount" class="input" type="number"/></div>
        <div><label class="label">Floor</label><input v-model="form.floor" class="input" placeholder="Ground"/></div>
        <div><label class="label">Size (sqm)</label><input v-model.number="form.size_sqm" class="input" type="number"/></div>
      </div>
      <div class="flex gap-3">
        <button class="btn-outline border-gray-200" @click="showForm = false">Cancel</button>
        <button class="btn-primary bg-landlord-600 hover:bg-landlord-700" :disabled="saving" @click="addUnit">
          <span v-if="saving" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"/>
          <span v-else>Add Unit</span>
        </button>
      </div>
    </div>
    <TableToolbar v-model="q" :count="rows.length" :total="units.length" :rows="rows" title="Units" />
    <div class="card overflow-x-auto">
      <div v-if="loading" class="p-8 text-center text-gray-400">Loading…</div>
      <table v-else-if="units.length" class="w-full">
        <thead class="bg-gray-50 border-b border-gray-100"><tr>
          <th class="table-th">Unit</th><th class="table-th">Property</th><th class="table-th">Beds</th>
          <th class="table-th">Rent</th><th class="table-th">Deposit</th><th class="table-th">Status</th>
        </tr></thead>
        <tbody>
          <tr v-for="u in rows" :key="u.id" class="table-tr">
            <td class="table-td font-medium">{{ u.unit_number }}</td>
            <td class="table-td text-xs text-gray-500">{{ u.property_name }}</td>
            <td class="table-td">{{ u.bedrooms }}BR / {{ u.bathrooms }}BA</td>
            <td class="table-td font-medium">{{ formatKES(u.rent_amount) }}</td>
            <td class="table-td">{{ formatKES(u.deposit_amount) }}</td>
            <td class="table-td"><span :class="unitStatus(u.status)" class="badge">{{ u.status }}</span></td>
          </tr>
        </tbody>
      </table>
      <div v-else class="p-10 text-center text-gray-400">No units yet.</div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { useRowSearch } from '@/composables/useRowSearch'
import TableToolbar from '@/components/ui/TableToolbar.vue'
import { ref, onMounted } from 'vue'
import { propertiesApi } from '@/api/services'
import { formatKES } from '@/utils/formatters'
import type { Unit, Property } from '@/types'
const units = ref<Unit[]>([]); const properties = ref<Property[]>([])
const { q, rows } = useRowSearch(() => units.value as any[], 'units')
const loading = ref(true); const showForm = ref(false); const saving = ref(false)
const form = ref({ property:'', unit_number:'', bedrooms:1, bathrooms:1, rent_amount:0, deposit_amount:0, floor:'', size_sqm:0 })
const unitStatus = (s: string) => ({ vacant:'badge-green', occupied:'badge-blue', maintenance:'badge-yellow', reserved:'badge-gray' }[s] || 'badge-gray')
async function load() {
  loading.value = true
  try {
    const [pRes] = await Promise.all([propertiesApi.list()])
    properties.value = pRes.data.data?.results || pRes.data.data || []
    const all: Unit[] = []
    for (const p of properties.value) {
      try { const { data } = await propertiesApi.units(p.id); const items = data.data?.results || data.data || []; all.push(...items) } catch (e) { console.error(`Failed to load units for property ${p.id}:`, e) }
    }
    units.value = all
  } finally { loading.value = false }
}
async function addUnit() {
  if (!form.value.property) return
  saving.value = true
  try { await propertiesApi.createUnit(form.value.property, form.value as any); showForm.value = false; await load() }
  finally { saving.value = false }
}
onMounted(load)
</script>
