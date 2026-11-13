<template>
  <div class="space-y-5">
    <h1 class="page-title">Payment Transactions</h1>

    <div v-if="disputed.length" class="rounded-xl border border-red-200 bg-red-50 p-4 space-y-3" role="region" aria-label="Disputed payments">
      <p class="text-sm font-semibold text-red-800">{{ disputed.length }} disputed payment{{ disputed.length === 1 ? '' : 's' }} need a decision</p>
      <p class="text-xs text-red-700">The amount M-Pesa reported did not match the amount requested, so nothing was applied.
        Check the Safaricom statement, then confirm (applies the payment once) or void (credits nothing).</p>
      <div v-for="p in disputed" :key="p.id" class="bg-white rounded-lg p-3 border border-red-100">
        <div class="flex items-center justify-between flex-wrap gap-2 text-sm">
          <span><span class="font-mono text-xs">{{ p.reference }}</span> · {{ p.payer_name }} · expected <strong>{{ formatKES(p.amount) }}</strong></span>
          <span class="text-xs text-red-700">{{ p.failure_reason }}</span>
        </div>
        <form class="mt-2 flex gap-2 flex-wrap" @submit.prevent>
          <label class="sr-only" :for="`d-${p.id}`">Reason</label>
          <input :id="`d-${p.id}`" v-model="reasons[p.id]" class="input flex-1 min-w-[12rem]" placeholder="Reason (required, recorded permanently)" />
          <button class="btn bg-emerald-600 text-white" :disabled="!reasons[p.id]?.trim() || busy === p.id" @click="resolve(p, 'confirm')">Confirm payment</button>
          <button class="btn-outline border-red-200 text-red-600" :disabled="!reasons[p.id]?.trim() || busy === p.id" @click="resolve(p, 'void')">Void</button>
        </form>
      </div>
      <p v-if="resolveError" class="text-sm text-red-700" role="alert">{{ resolveError }}</p>
    </div>
    <TableToolbar v-model="q" :count="rows.length" :total="payments.length" :rows="rows" title="Payment transactions" />
    <div class="card overflow-x-auto">
      <div v-if="loading" class="p-8 text-center text-gray-400">Loading…</div>
      <table v-else-if="payments.length" class="w-full">
        <thead class="bg-gray-50 border-b"><tr>
          <th class="table-th">Reference</th><th class="table-th">Payer</th><th class="table-th">Amount</th>
          <th class="table-th">Method</th><th class="table-th">Status</th><th class="table-th">Date</th><th class="table-th"><span class="sr-only">Actions</span></th>
        </tr></thead>
        <tbody>
          <template v-for="p in rows" :key="p.id"><tr class="table-tr">
            <td class="table-td font-mono text-xs">{{ p.reference }}</td>
            <td class="table-td text-sm">{{ p.payer_name }}</td>
            <td class="table-td font-medium">{{ formatKES(p.amount) }}</td>
            <td class="table-td text-xs capitalize">{{ p.method.replace('_',' ') }}</td>
            <td class="table-td"><span :class="statusColor(p.status)" class="badge">{{ p.status }}</span></td>
            <td class="table-td text-xs">{{ formatDate(p.created_at) }}</td>
            <td class="table-td text-right">
              <button v-if="refundable(p)" class="btn-outline border-gray-200 text-xs" @click="refundFor = refundFor === p.id ? null : p.id">Refund / reverse</button>
            </td>
          </tr>
          <tr v-if="refundFor === p.id"><td colspan="7" class="px-5 pb-4">
            <RefundRequestForm :payment="p" can-reverse @done="onRefunded" @cancel="refundFor = null" />
          </td></tr></template>
        </tbody>
      </table>
      <div v-else class="p-10 text-center text-gray-400">No transactions found.</div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { useRowSearch } from '@/composables/useRowSearch'
import TableToolbar from '@/components/ui/TableToolbar.vue'
import { ref, computed, onMounted } from 'vue'
import { paymentsApi } from '@/api/services'
import RefundRequestForm from '@/components/common/RefundRequestForm.vue'
import { formatKES, formatDate, statusColor } from '@/utils/formatters'
import type { Payment } from '@/types'
const payments = ref<Payment[]>([]); const loading = ref(true)
const { q, rows } = useRowSearch(() => payments.value as any[], 'transactions')
const refundFor = ref<string | null>(null)
const refundable = (p: any) => p.status === 'completed' && Number(p.amount) - Number(p.refunded_amount || 0) > 0
function onRefunded() { refundFor.value = null; load() }
const reasons = ref<Record<string, string>>({}); const busy = ref<string | null>(null); const resolveError = ref('')
const disputed = computed(() => payments.value.filter((p: any) => p.status === 'disputed') as any[])
async function load() {
  try { const { data } = await paymentsApi.list(); payments.value = data.data?.results || data.data || [] }
  catch { payments.value = [] } finally { loading.value = false }
}
async function resolve(p: any, action: 'confirm' | 'void') {
  busy.value = p.id; resolveError.value = ''
  try { await paymentsApi.resolveDispute(p.id, action, reasons.value[p.id].trim()); await load() }
  catch (e: any) { resolveError.value = e?.response?.data?.error?.message || 'Could not resolve this payment.' }
  finally { busy.value = null }
}
onMounted(load)
</script>
