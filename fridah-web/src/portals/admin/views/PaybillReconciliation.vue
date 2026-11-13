<template>
  <div class="space-y-5">
    <div class="page-header">
      <h1 class="page-title">Paybill Reconciliation</h1>
      <select v-model="statusFilter" class="input w-48" @change="load">
        <option value="">All statuses</option>
        <option value="unmatched">Unmatched</option>
        <option value="matched">Matched</option>
        <option value="duplicate">Duplicate</option>
      </select>
    </div>

    <div class="card overflow-x-auto">
      <div v-if="loading" class="p-8 text-center text-gray-400 dark:text-gray-500">Loading…</div>
      <table v-else-if="transactions.length" class="w-full">
        <thead class="bg-gray-50 dark:bg-gray-800/50 border-b dark:border-gray-800"><tr>
          <th class="table-th">Receipt</th><th class="table-th">Amount</th><th class="table-th">Account Ref</th>
          <th class="table-th">Payer</th><th class="table-th">Status</th><th class="table-th">Action</th>
        </tr></thead>
        <tbody>
          <tr v-for="t in transactions" :key="t.id" class="table-tr">
            <td class="table-td font-mono text-xs">{{ t.mpesa_receipt_number }}</td>
            <td class="table-td font-medium">{{ formatKES(t.amount) }}</td>
            <td class="table-td font-mono text-xs">{{ t.bill_ref_number || '—' }}</td>
            <td class="table-td text-sm">{{ t.payer_name }} ({{ t.msisdn }})</td>
            <td class="table-td"><span :class="statusColor(t.match_status)" class="badge">{{ t.match_status }}</span></td>
            <td class="table-td">
              <div v-if="t.match_status === 'unmatched'" class="flex gap-1">
                <input v-model="reconcileForm[t.id]" placeholder="Invoice ID" class="input py-1 text-xs w-32" />
                <button class="btn-primary bg-adminc-600 hover:bg-adminc-700 text-xs py-1 px-2" @click="reconcile(t.id)">Match</button>
              </div>
              <span v-else class="text-xs text-gray-400 dark:text-gray-500">—</span>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="p-10 text-center text-gray-400 dark:text-gray-500">No paybill transactions found.</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { paymentsApi } from '@/api/services'
import { formatKES, statusColor } from '@/utils/formatters'

const transactions = ref<any[]>([])
const loading = ref(true)
const statusFilter = ref('unmatched')
const reconcileForm = ref<Record<string, string>>({})

async function load() {
  loading.value = true
  try {
    const { data } = await paymentsApi.paybillTransactions(statusFilter.value ? { match_status: statusFilter.value } : {})
    transactions.value = data.data?.results || data.data || []
  } catch { transactions.value = [] } finally { loading.value = false }
}

async function reconcile(transactionId: string) {
  const invoiceId = reconcileForm.value[transactionId]
  if (!invoiceId) return
  await paymentsApi.reconcilePaybillTransaction(transactionId, invoiceId)
  await load()
}

onMounted(load)
</script>
