<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="page-title">Invoices</h1>
      <select v-model="filter" class="input w-auto text-sm">
        <option value="">All</option><option value="pending">Pending</option><option value="overdue">Overdue</option><option value="paid">Paid</option>
      </select>
    </div>
    <TableToolbar v-model="q" :count="rows.length" :total="filtered.length" :rows="rows" title="Invoices" />
    <div class="card overflow-x-auto">
      <div v-if="loading" class="p-8 text-center text-gray-400">Loading…</div>
      <table v-else-if="filtered.length" class="w-full">
        <thead class="bg-gray-50 border-b"><tr>
          <th class="table-th">Invoice</th><th class="table-th">Tenant</th><th class="table-th">Type</th>
          <th class="table-th">Amount</th><th class="table-th">Balance</th><th class="table-th">Due</th><th class="table-th">Status</th><th class="table-th"><span class="sr-only">Actions</span></th>
        </tr></thead>
        <tbody>
          <tr v-for="inv in rows" :key="inv.id" class="table-tr">
            <td class="table-td font-mono text-xs">{{ inv.invoice_number }}</td>
            <td class="table-td font-medium">{{ inv.tenant_name }}</td>
            <td class="table-td capitalize text-xs">{{ inv.invoice_type }}<span v-if="(inv as any).amenity_name" class="block text-gray-400 normal-case">{{ (inv as any).amenity_name }}</span></td>
            <td class="table-td">{{ formatKES(inv.amount) }}</td>
            <td class="table-td" :class="inv.balance > 0 ? 'text-red-600 font-medium' : 'text-green-600'">{{ formatKES(inv.balance) }}</td>
            <td class="table-td">{{ formatDate(inv.due_date) }}</td>
            <td class="table-td"><span :class="statusColor(inv.status)" class="badge">{{ inv.status }}</span></td>
          <td class="table-td"><div class="flex items-center gap-2">
            <ExportMenu compact label="Invoice" :formats="['pdf', 'docx']" :handler="(f: any) => exportInvoice(f, inv as any)" />
            <button v-if="canWaive(inv)" class="btn-outline border-gray-200 text-xs" @click="startWaive(inv)">Waive</button>
          </div></td>
          </tr>
        </tbody>
      </table>
      <div v-else class="p-10 text-center text-gray-400">No invoices found.</div>
    </div>

    <form v-if="waiving" class="card card-body space-y-2" @submit.prevent="submitWaive">
      <label class="text-sm font-medium text-gray-700" for="waive-reason">
        Why are you waiving {{ (waiving as any).invoice_number }}? (recorded permanently)
      </label>
      <input id="waive-reason" v-model="reason" class="input" required placeholder="e.g. Water outage in March" />
      <p v-if="waiveError" class="text-sm text-red-600" role="alert">{{ waiveError }}</p>
      <div class="flex gap-2">
        <button class="btn bg-gray-900 text-white" :disabled="!reason.trim()">Waive invoice</button>
        <button type="button" class="btn-outline border-gray-200" @click="waiving = null">Cancel</button>
      </div>
    </form>
  </div>
</template>
<script setup lang="ts">
import ExportMenu from '@/components/ui/ExportMenu.vue'
import { exportInvoice } from '@/utils/exporters'
import { useRowSearch } from '@/composables/useRowSearch'
import TableToolbar from '@/components/ui/TableToolbar.vue'
import { ref, computed, onMounted } from 'vue'
import { rentalsApi, amenityApi } from '@/api/services'
import { formatKES, formatDate, statusColor } from '@/utils/formatters'
import type { Invoice } from '@/types'
const invoices = ref<Invoice[]>([]); const loading = ref(true); const filter = ref('')
const filtered = computed(() => filter.value ? invoices.value.filter(i => i.status === filter.value) : invoices.value)
const { q, rows } = useRowSearch(() => filtered.value as any[], 'invoices')
const waiving = ref<Invoice | null>(null); const reason = ref(''); const waiveError = ref('')
const canWaive = (inv: any) => inv.invoice_type === 'amenity' && !['paid', 'cancelled'].includes(inv.status) && Number(inv.amount_paid) === 0
function startWaive(inv: Invoice) { waiving.value = inv; reason.value = ''; waiveError.value = '' }
async function submitWaive() {
  if (!waiving.value) return
  try {
    await amenityApi.waiveInvoice(waiving.value.id, reason.value.trim())
    waiving.value = null
    await load()
  } catch (e: any) { waiveError.value = e?.response?.data?.error?.message || e?.response?.data?.detail || 'Could not waive this invoice.' }
}
async function load() {
  try { const { data } = await rentalsApi.invoices(); invoices.value = data.data?.results || data.data || [] }
  catch { invoices.value = [] } finally { loading.value = false }
}
onMounted(load)
</script>
