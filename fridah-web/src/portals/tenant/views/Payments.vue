<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="page-title">Payment History</h1>
      <button class="btn-primary bg-tenant-600 hover:bg-tenant-700" @click="showPay = true">+ Make Payment</button>
    </div>
    <p v-if="refundNotice" class="text-sm text-emerald-700" role="status">{{ refundNotice }}</p>
    <TableToolbar v-model="q" :count="rows.length" :total="payments.length" :rows="rows" title="Payment history" />
    <div class="card overflow-x-auto">
      <div v-if="loading" class="p-8 text-center text-gray-400">Loading…</div>
      <table v-else-if="payments.length" class="w-full">
        <thead class="bg-gray-50 border-b border-gray-100"><tr>
          <th class="table-th">Reference</th><th class="table-th">Amount</th>
          <th class="table-th">Method</th><th class="table-th">Status</th><th class="table-th">Date</th><th class="table-th"><span class="sr-only">Actions</span></th>
        </tr></thead>
        <tbody>
          <template v-for="p in rows" :key="p.id"><tr class="table-tr">
            <td class="table-td font-mono text-xs">{{ p.reference }}</td>
            <td class="table-td font-medium">{{ formatKES(p.amount) }}</td>
            <td class="table-td capitalize text-xs">{{ p.method.replace('_',' ') }}</td>
            <td class="table-td"><span :class="statusColor(p.status)" class="badge">{{ p.status }}</span></td>
            <td class="table-td">{{ formatDate(p.created_at) }}</td>
            <td class="table-td text-right">
              <button v-if="refundable(p)" class="btn-outline border-gray-200 text-xs" @click="refundFor = refundFor === p.id ? null : p.id">Request refund</button>
            </td>
          </tr>
          <tr v-if="refundFor === p.id"><td colspan="6" class="px-5 pb-4">
            <RefundRequestForm :payment="p" @done="onRefunded" @cancel="refundFor = null" />
          </td></tr></template>
        </tbody>
      </table>
      <div v-else class="p-10 text-center text-gray-400">No payments yet.</div>
    </div>
    <MpesaPayModal v-model="showPay" :amount="payAmount" accent-bg="bg-tenant-600 hover:bg-tenant-700" description="Manual payment" @paid="load" />
  </div>
</template>
<script setup lang="ts">
import { useRowSearch } from '@/composables/useRowSearch'
import TableToolbar from '@/components/ui/TableToolbar.vue'
import { ref, onMounted } from 'vue'
import { paymentsApi } from '@/api/services'
import MpesaPayModal from '@/components/common/MpesaPayModal.vue'
import RefundRequestForm from '@/components/common/RefundRequestForm.vue'
import { formatKES, formatDate, statusColor } from '@/utils/formatters'
import type { Payment } from '@/types'
const payments = ref<Payment[]>([])
const { q, rows } = useRowSearch(() => payments.value as any[], 'payments')
const loading = ref(true)
const showPay = ref(false)
const refundFor = ref<string | null>(null)
const refundNotice = ref('')
const refundable = (p: any) => p.status === 'completed' && Number(p.amount) - Number(p.refunded_amount || 0) > 0
function onRefunded() { refundFor.value = null; refundNotice.value = 'Refund request sent. Track it under My Refunds.' }
const payAmount = ref(1000)
async function load() {
  try { const { data } = await paymentsApi.list(); payments.value = data.data?.results || data.data || [] }
  catch { payments.value = [] } finally { loading.value = false }
}
onMounted(load)
</script>
