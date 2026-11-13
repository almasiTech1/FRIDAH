<template>
  <div class="space-y-5">
    <div>
      <h1 class="page-title">Reconciliation & Settlement</h1>
      <p class="text-sm text-gray-500 mt-0.5">Check that the platform's books agree with each other and with the Safaricom statement.</p>
    </div>

    <!-- Settlement position -->
    <section class="card card-body space-y-3" aria-labelledby="st-title">
      <div class="flex items-end justify-between flex-wrap gap-3">
        <h2 id="st-title" class="font-semibold text-gray-900">Settlement position</h2>
        <form class="flex gap-2 items-end" @submit.prevent="loadSettlement">
          <div><label class="text-xs text-gray-600" for="st-from">From</label><input id="st-from" v-model="range.start" type="date" class="input" /></div>
          <div><label class="text-xs text-gray-600" for="st-to">To</label><input id="st-to" v-model="range.end" type="date" class="input" /></div>
          <button class="btn bg-gray-900 text-white">Update</button>
        </form>
      </div>
      <div v-if="settlement" class="grid grid-cols-2 md:grid-cols-4 gap-3 stagger">
        <div v-for="c in cards" :key="c.label" class="rounded-lg bg-gray-50 p-3">
          <p class="text-xs text-gray-500">{{ c.label }}</p><p class="text-lg font-black" :class="c.cls">{{ formatKES(c.value) }}</p>
        </div>
      </div>
      <p v-else-if="settlementError" class="text-sm text-red-600" role="alert">{{ settlementError }}</p>
    </section>

    <!-- Run checks -->
    <div class="grid md:grid-cols-2 gap-5">
      <form class="card card-body space-y-3" @submit.prevent="runInternal">
        <h2 class="font-semibold text-gray-900">Internal books check</h2>
        <p class="text-xs text-gray-500">Every completed payment must have exactly one wallet credit of the right size. Also lists stuck, disputed and unpaid-refund items. Runs automatically every day for yesterday.</p>
        <div class="grid grid-cols-2 gap-2">
          <div><label class="text-xs text-gray-600" for="in-from">From</label><input id="in-from" v-model="internal.start" type="date" class="input" required /></div>
          <div><label class="text-xs text-gray-600" for="in-to">To</label><input id="in-to" v-model="internal.end" type="date" class="input" required /></div>
        </div>
        <button class="btn bg-gray-900 text-white" :disabled="busy">Run check</button>
      </form>

      <form class="card card-body space-y-3" @submit.prevent="uploadStatement">
        <h2 class="font-semibold text-gray-900">Safaricom statement</h2>
        <p class="text-xs text-gray-500">Upload the M-Pesa statement as CSV (needs Receipt and Paid-in/Amount columns). Lines are matched by receipt number.</p>
        <div><label class="text-xs text-gray-600" for="stmt-file">Statement CSV</label><input id="stmt-file" type="file" accept=".csv,text/csv" class="input" required @change="onFile" /></div>
        <div class="grid grid-cols-2 gap-2">
          <div><label class="text-xs text-gray-600" for="sm-from">Statement from</label><input id="sm-from" v-model="stmt.start" type="date" class="input" required /></div>
          <div><label class="text-xs text-gray-600" for="sm-to">Statement to</label><input id="sm-to" v-model="stmt.end" type="date" class="input" required /></div>
        </div>
        <button class="btn bg-gray-900 text-white" :disabled="busy || !file">Upload & reconcile</button>
      </form>
    </div>
    <p v-if="notice" class="text-sm text-emerald-700" role="status">{{ notice }}</p>
    <p v-if="error" class="text-sm text-red-600" role="alert">{{ error }}</p>

    <!-- Runs -->
    <div class="card overflow-x-auto">
      <table class="w-full">
        <thead class="bg-gray-50 border-b"><tr>
          <th class="table-th">When</th><th class="table-th">Type</th><th class="table-th">Period</th>
          <th class="table-th text-right">Checked</th><th class="table-th text-right">Matched</th><th class="table-th text-right">Open issues</th><th class="table-th"></th>
        </tr></thead>
        <tbody>
          <tr v-for="r in runs" :key="r.id" class="table-tr">
            <td class="table-td text-xs">{{ formatDate(r.created_at) }}</td>
            <td class="table-td text-xs">{{ r.source === 'statement' ? `Statement ${r.file_name}` : 'Internal check' }}</td>
            <td class="table-td text-xs">{{ formatDate(r.period_start) }} – {{ formatDate(r.period_end) }}</td>
            <td class="table-td text-right">{{ r.rows_checked }}</td><td class="table-td text-right">{{ r.matched }}</td>
            <td class="table-td text-right"><span class="badge" :class="r.open_issues ? 'badge-red' : 'badge-green'">{{ r.open_issues }}</span></td>
            <td class="table-td text-right"><button class="btn-outline border-gray-200 text-xs" @click="openRun(r.id)">{{ selected === r.id ? 'Hide' : 'View' }}</button></td>
          </tr>
          <tr v-if="!runs.length"><td colspan="7" class="p-8 text-center text-gray-400">No reconciliation runs yet.</td></tr>
        </tbody>
      </table>
    </div>

    <section v-if="selected" class="card card-body space-y-3" aria-label="Run details">
      <h2 class="font-semibold text-gray-900">Items</h2>
      <p v-if="!items.length" class="text-sm text-emerald-700">Everything in this run reconciles.</p>
      <div v-for="i in items" :key="i.id" class="border border-gray-100 rounded-lg p-3">
        <div class="flex items-start justify-between gap-3 flex-wrap">
          <div>
            <span class="badge" :class="i.resolved ? 'badge-green' : 'badge-red'">{{ i.kind_label }}</span>
            <p class="text-sm text-gray-700 mt-1">{{ i.note }}</p>
            <p class="text-xs text-gray-500">
              <template v-if="i.receipt">Receipt {{ i.receipt }} · </template>
              <template v-if="i.expected_amount !== null">Platform {{ formatKES(i.expected_amount) }} · </template>
              <template v-if="i.actual_amount !== null">Other side {{ formatKES(i.actual_amount) }}</template>
            </p>
            <p v-if="i.resolved" class="text-xs text-emerald-700 mt-1">Resolved: {{ i.resolution_note }}</p>
          </div>
          <button v-if="!i.resolved" class="btn-outline border-gray-200 text-xs" @click="resolving = resolving === i.id ? null : i.id; note = ''">Resolve</button>
        </div>
        <form v-if="resolving === i.id" class="mt-2 flex gap-2" @submit.prevent="resolve(i)">
          <label class="sr-only" :for="`rs-${i.id}`">Resolution note</label>
          <input :id="`rs-${i.id}`" v-model="note" class="input flex-1" required placeholder="What was done / why this is fine (required)" />
          <button class="btn bg-gray-900 text-white" :disabled="!note.trim()">Mark resolved</button>
        </form>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { reconciliationApi } from '@/api/services'
import { formatKES, formatDate } from '@/utils/formatters'

const iso = (d: Date) => d.toISOString().slice(0, 10)
const today = new Date(); const monthAgo = new Date(Date.now() - 29 * 86400000); const yesterday = new Date(Date.now() - 86400000)
const range = ref({ start: iso(monthAgo), end: iso(today) })
const internal = ref({ start: iso(yesterday), end: iso(yesterday) })
const stmt = ref({ start: iso(monthAgo), end: iso(today) })
const file = ref<File | null>(null)
const settlement = ref<any | null>(null)
const settlementError = ref('')
const runs = ref<any[]>([])
const selected = ref<string | null>(null)
const items = ref<any[]>([])
const resolving = ref<string | null>(null)
const note = ref('')
const busy = ref(false)
const notice = ref('')
const error = ref('')

const cards = computed(() => settlement.value ? [
  { label: 'Collected', value: settlement.value.gross_collected },
  { label: 'Platform commission', value: settlement.value.platform_commission },
  { label: 'Credited to recipients', value: settlement.value.credited_to_recipients },
  { label: 'Owed in wallets now', value: settlement.value.wallet_liability },
  { label: 'Refunds approved', value: settlement.value.refunds_approved },
  { label: 'Refunds awaiting payout', value: settlement.value.refunds_awaiting_payout, cls: 'text-amber-600' },
  { label: 'Payouts sent to recipients', value: settlement.value.payouts_sent_to_recipients },
  { label: 'Recovered from wallets', value: settlement.value.recovered_from_recipient_wallets },
] : [])

const list = (res: any) => res.data?.data?.results || res.data?.results || []
async function loadSettlement() {
  settlementError.value = ''
  try { settlement.value = ((await reconciliationApi.settlement(range.value)).data as any).data }
  catch { settlement.value = null; settlementError.value = 'Could not load the settlement position.' }
}
async function loadRuns() { try { runs.value = list(await reconciliationApi.runs()) } catch { runs.value = [] } }
async function openRun(id: string) {
  if (selected.value === id) { selected.value = null; return }
  selected.value = id; items.value = []
  try { items.value = ((await reconciliationApi.run(id)).data as any).data.items } catch { error.value = 'Could not load the run.' }
}
const onFile = (e: Event) => { file.value = (e.target as HTMLInputElement).files?.[0] || null }
const fail = (e: any) => { error.value = e?.response?.data?.error?.message || e?.response?.data?.detail || 'That failed.' }

async function runInternal() {
  busy.value = true; error.value = ''; notice.value = ''
  try {
    const d: any = ((await reconciliationApi.runInternal(internal.value.start, internal.value.end)).data as any).data
    notice.value = `Checked ${d.rows_checked} payments: ${d.issues} issue(s).`
    await loadRuns(); await openRun(d.id)
  } catch (e) { fail(e) } finally { busy.value = false }
}
async function uploadStatement() {
  if (!file.value) return
  busy.value = true; error.value = ''; notice.value = ''
  try {
    const d: any = ((await reconciliationApi.uploadStatement(file.value, stmt.value.start, stmt.value.end)).data as any).data
    notice.value = `Statement checked: ${d.matched} matched, ${d.issues} issue(s)${d.skipped_lines ? `, ${d.skipped_lines} non-receipt line(s) skipped` : ''}.`
    await loadRuns(); selected.value = null; await openRun(d.id)
  } catch (e) { fail(e) } finally { busy.value = false }
}
async function resolve(i: any) {
  error.value = ''
  try {
    await reconciliationApi.resolveItem(i.id, note.value.trim())
    resolving.value = null
    if (selected.value) items.value = ((await reconciliationApi.run(selected.value)).data as any).data.items
    await loadRuns()
  } catch (e) { fail(e) }
}

onMounted(async () => { await Promise.all([loadSettlement(), loadRuns()]) })
</script>
