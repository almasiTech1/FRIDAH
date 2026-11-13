<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="page-title">My Invoices</h1>
      <div class="flex gap-2">
        <select v-model="filter" class="input w-auto text-sm">
          <option value="">All</option>
          <option value="pending">Pending</option>
          <option value="overdue">Overdue</option>
          <option value="paid">Paid</option>
        </select>
      </div>
    </div>

    <TableToolbar v-model="q" :count="rows.length" :total="filtered.length" :rows="rows" title="My invoices" />
    <div class="card overflow-x-auto">
      <div v-if="loading" class="p-8 text-center text-gray-400">Loading invoices…</div>
      <table v-else-if="filtered.length" class="w-full">
        <thead class="bg-gray-50 border-b border-gray-100">
          <tr>
            <th class="table-th">Invoice #</th>
            <th class="table-th">Type</th>
            <th class="table-th">Period</th>
            <th class="table-th">Amount</th>
            <th class="table-th">Balance</th>
            <th class="table-th">Due</th>
            <th class="table-th">Status</th>
            <th class="table-th">Action</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="inv in rows" :key="inv.id" class="table-tr">
            <td class="table-td font-mono text-xs text-gray-600">{{ inv.invoice_number }}</td>
            <td class="table-td capitalize">{{ inv.invoice_type }}</td>
            <td class="table-td">{{ formatDate(inv.period_start) }}</td>
            <td class="table-td font-medium">{{ formatKES(inv.amount) }}</td>
            <td class="table-td" :class="inv.balance > 0 ? 'text-red-600 font-medium' : 'text-green-600'">{{ formatKES(inv.balance) }}</td>
            <td class="table-td">{{ formatDate(inv.due_date) }}</td>
            <td class="table-td"><span :class="statusColor(inv.status)" class="badge">{{ inv.status }}</span></td>
            <td class="table-td"><div class="flex items-center gap-2 flex-wrap">
              <ExportMenu compact label="Invoice" :formats="['pdf', 'docx']" :handler="(f: any) => exportInvoice(f, inv as any)" />
              <button
                v-if="inv.status !== 'paid' && inv.status !== 'cancelled'"
                class="btn-primary bg-tenant-600 hover:bg-tenant-700 text-xs py-1.5 px-3"
                @click="payInvoice(inv)"
              >Pay</button>
              <a v-if="inv.pdf_receipt" :href="inv.pdf_receipt" target="_blank" class="btn-ghost text-xs py-1.5 px-3">Receipt</a>
            </div></td>
          </tr>
        </tbody>
      </table>
      <div v-else class="p-10 text-center text-gray-400 text-sm">No invoices found.</div>
    </div>

    <MpesaPayModal
      v-model="showPayModal"
      :amount="selectedInvoice?.balance || 0"
      :invoice-id="selectedInvoice?.id"
      accent-bg="bg-tenant-600 hover:bg-tenant-700"
      description="Rent payment"
      @paid="loadInvoices"
    />
  </div>
</template>

<script setup lang="ts">
import ExportMenu from '@/components/ui/ExportMenu.vue'
import { exportInvoice } from '@/utils/exporters'
import { useRowSearch } from '@/composables/useRowSearch'
import TableToolbar from '@/components/ui/TableToolbar.vue'
import { ref, computed, onMounted } from 'vue'
import { rentalsApi } from '@/api/services'
import MpesaPayModal from '@/components/common/MpesaPayModal.vue'
import { formatKES, formatDate, statusColor } from '@/utils/formatters'
import type { Invoice } from '@/types'

const invoices = ref<Invoice[]>([])
const loading = ref(true)
const filter = ref('')
const showPayModal = ref(false)
const selectedInvoice = ref<Invoice | null>(null)


const filtered = computed(() =>
  filter.value ? invoices.value.filter(i => i.status === filter.value) : invoices.value
)
const { q, rows } = useRowSearch(() => filtered.value as any[], 'my-invoices')

async function loadInvoices() {
  loading.value = true
  try {
    const { data } = await rentalsApi.invoices()
    invoices.value = data.data?.results || data.data || []
  } catch {
    invoices.value = [
      { id: '1', invoice_number: 'INV-DEMO001', lease: '', tenant: '', tenant_name: '', invoice_type: 'rent', amount: 25000, amount_paid: 0, balance: 25000, period_start: '2026-07-01', period_end: '2026-07-31', due_date: '2026-07-05', status: 'pending', is_overdue: false, created_at: new Date().toISOString() },
    ]
  } finally {
    loading.value = false
  }
}

function payInvoice(inv: Invoice) {
  selectedInvoice.value = inv
  showPayModal.value = true
}

onMounted(loadInvoices)
</script>
