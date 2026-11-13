<template>
  <div class="space-y-5">
    <div class="flex items-start justify-between flex-wrap gap-3">
      <div>
        <h1 class="page-title">Tax Records</h1>
        <p class="text-sm text-gray-500 mt-0.5">Track estimated and paid tax on your rental income, per property.</p>
      </div>
      <div class="flex items-center gap-2">
        <label class="sr-only" for="tax-year">Year</label>
        <select id="tax-year" v-model="year" class="input !w-28" @change="load">
          <option v-for="y in years" :key="y" :value="y">{{ y }}</option>
        </select>
        <button class="btn-outline border-gray-200" :disabled="exporting" @click="exportCsv">
          {{ exporting ? 'Preparing…' : 'Export CSV' }}
        </button>
      </div>
    </div>

    <div class="rounded-xl border border-amber-200 bg-amber-50 text-amber-900 text-sm p-4" role="note">
      <strong>Estimates only.</strong> Figures marked “Estimate” are calculated from your statements using the rules
      Fridah has configured. They are <strong>not</strong> official KRA assessments. Confirm your actual liability with
      KRA or a qualified tax adviser before filing.
    </div>

    <!-- New estimate -->
    <form class="card card-body grid md:grid-cols-4 gap-3 items-end" @submit.prevent="createEstimate">
      <div class="md:col-span-2">
        <label class="text-xs font-medium text-gray-600" for="est-st">Statement</label>
        <select id="est-st" v-model="est.statement" class="input" required>
          <option value="" disabled>Choose an issued statement…</option>
          <option v-for="s in statements" :key="s.id" :value="s.id">
            {{ s.property_name }} · {{ formatDate(s.period_start) }} – {{ formatDate(s.period_end) }}
          </option>
        </select>
      </div>
      <div>
        <label class="text-xs font-medium text-gray-600" for="est-type">Tax type</label>
        <select id="est-type" v-model="est.tax_type" class="input" required>
          <option value="" disabled>Choose…</option>
          <option v-for="t in types" :key="t.id" :value="t.code">{{ t.name }}</option>
        </select>
      </div>
      <button class="btn bg-gray-900 text-white justify-center" :disabled="saving || !est.statement || !est.tax_type">
        {{ saving ? 'Calculating…' : 'Calculate estimate' }}
      </button>
      <p v-if="formError" class="md:col-span-4 text-sm text-red-600" role="alert">{{ formError }}</p>
      <p v-if="!types.length" class="md:col-span-4 text-xs text-gray-500">
        No tax types are configured yet. An administrator must set up and professionally validate the rules first.
      </p>
    </form>

    <!-- Summary -->
    <div v-if="summary.length" class="card overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="text-left text-xs text-gray-500">
            <th class="table-th">Property</th><th class="table-th">Tax</th><th class="table-th text-right">Gross</th>
            <th class="table-th text-right">Calculated</th><th class="table-th text-right">Paid</th>
            <th class="table-th text-right">Balance</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in summary" :key="`${r.property}-${r.tax_type}`" class="table-tr">
            <td class="table-td">{{ r.property_name || '—' }}</td>
            <td class="table-td">{{ r.tax_type }}
              <span v-if="r.estimate_only_records" class="badge badge-yellow ml-1">{{ r.estimate_only_records }} estimate</span></td>
            <td class="table-td text-right">{{ formatKES(r.gross_income) }}</td>
            <td class="table-td text-right">{{ formatKES(r.calculated) }}</td>
            <td class="table-td text-right">{{ formatKES(r.paid) }}</td>
            <td class="table-td text-right font-semibold">{{ formatKES(r.balance_due) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="loading" class="space-y-3" aria-busy="true">
      <div v-for="i in 2" :key="i" class="card animate-pulse h-24 bg-gray-100 rounded-xl" />
    </div>
    <div v-else-if="!records.length" class="card card-body text-center py-12 text-gray-400">
      No tax records for {{ year }} yet. Calculate an estimate from an issued statement above.
    </div>

    <div v-else class="space-y-3 stagger">
      <div v-for="r in records" :key="r.id" class="card card-body">
        <div class="flex items-center justify-between flex-wrap gap-2">
          <div>
            <div class="flex items-center gap-2 flex-wrap">
              <p class="font-semibold text-gray-900">{{ r.property_name }} · {{ r.tax_type_name }}</p>
              <span class="badge" :class="statusColor(r.status)">{{ r.is_estimate ? 'Estimate' : r.status }}</span>
              <span v-if="r.rule_version" class="badge badge-gray">rule v{{ r.rule_version }}</span>
            </div>
            <p class="text-xs text-gray-500 mt-0.5">{{ formatDate(r.period_start) }} – {{ formatDate(r.period_end) }}
              <template v-if="r.reference"> · Ref {{ r.reference }}</template></p>
          </div>
          <div class="text-right">
            <p class="text-xs text-gray-400">Balance due</p>
            <p class="text-lg font-black text-gray-900">{{ formatKES(r.balance_due) }}</p>
          </div>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3 text-center">
          <div><p class="text-xs text-gray-400">Gross income</p><p class="text-sm font-bold">{{ formatKES(r.gross_income) }}</p></div>
          <div><p class="text-xs text-gray-400">Allowable expenses</p><p class="text-sm font-bold">{{ formatKES(r.allowable_expenses) }}</p></div>
          <div><p class="text-xs text-gray-400">Calculated</p><p class="text-sm font-bold">{{ formatKES(r.calculated_amount) }}</p></div>
          <div><p class="text-xs text-gray-400">Paid</p><p class="text-sm font-bold text-emerald-600">{{ formatKES(r.amount_paid) }}</p></div>
        </div>
        <div class="flex gap-2 mt-3 flex-wrap">
          <button class="btn-outline border-gray-200 text-xs" @click="open = open === r.id ? null : r.id">
            {{ open === r.id ? 'Hide working' : 'Show working' }}
          </button>
          <button v-if="r.status !== 'paid'" class="btn-outline border-emerald-200 text-emerald-700 text-xs" @click="startPay(r)">
            Record payment
          </button>
        </div>

        <ul v-if="open === r.id" class="mt-3 text-xs text-gray-600 list-disc pl-5 space-y-0.5">
          <li v-for="(step, i) in r.calculation_breakdown?.steps || []" :key="i">{{ step }}</li>
          <li v-if="r.label" class="text-amber-700 font-medium list-none -ml-5 mt-2">{{ r.label }}</li>
        </ul>

        <form v-if="payFor?.id === r.id" class="mt-3 grid md:grid-cols-4 gap-2 items-end" @submit.prevent="submitPayment">
          <div><label class="text-xs text-gray-600" :for="`pa-${r.id}`">Amount paid (KES)</label>
            <input :id="`pa-${r.id}`" v-model="pay.amount" type="number" min="0" step="0.01" class="input" required /></div>
          <div><label class="text-xs text-gray-600" :for="`pr-${r.id}`">KRA reference</label>
            <input :id="`pr-${r.id}`" v-model="pay.reference" class="input" placeholder="e.g. payment reference" /></div>
          <div><label class="text-xs text-gray-600" :for="`pn-${r.id}`">Note</label>
            <input :id="`pn-${r.id}`" v-model="pay.reason" class="input" required placeholder="e.g. Paid via iTax" /></div>
          <div class="flex gap-2">
            <button class="btn bg-gray-900 text-white" :disabled="saving">Save</button>
            <button type="button" class="btn-outline border-gray-200" @click="payFor = null">Cancel</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { taxApi, agencyApi } from '@/api/services'
import { statusColor, formatDate, formatKES } from '@/utils/formatters'

const now = new Date().getFullYear()
const years = [now, now - 1, now - 2, now - 3]
const year = ref(String(now))
const records = ref<any[]>([])
const summary = ref<any[]>([])
const types = ref<any[]>([])
const statements = ref<any[]>([])
const loading = ref(true)
const saving = ref(false)
const exporting = ref(false)
const formError = ref('')
const open = ref<string | null>(null)
const est = ref({ statement: '', tax_type: '' })
const payFor = ref<any | null>(null)
const pay = ref({ amount: '', reference: '', reason: '' })

const list = (res: any) => res.data?.data?.results || res.data?.results || res.data?.data || []

async function load() {
  loading.value = true
  try {
    const [r, s] = await Promise.all([taxApi.records({ year: year.value }), taxApi.summary({ year: year.value })])
    records.value = list(r)
    summary.value = (s.data as any).data?.rows || []
  } catch { records.value = []; summary.value = [] } finally { loading.value = false }
}

async function loadLookups() {
  try { types.value = list(await taxApi.types()).filter((t: any) => t.is_active) } catch { types.value = [] }
  try { statements.value = list(await agencyApi.statements()) } catch { statements.value = [] }
}

async function createEstimate() {
  saving.value = true; formError.value = ''
  try {
    await taxApi.estimate(est.value)
    est.value = { statement: '', tax_type: '' }
    await load()
  } catch (e: any) {
    formError.value = e?.response?.data?.error?.message || 'Could not calculate an estimate.'
  } finally { saving.value = false }
}

function startPay(r: any) {
  payFor.value = r
  pay.value = { amount: String(r.calculated_amount), reference: r.reference || '', reason: '' }
}

async function submitPayment() {
  if (!payFor.value) return
  saving.value = true; formError.value = ''
  try {
    await taxApi.adjust(payFor.value.id, {
      amount_paid: pay.value.amount, reference: pay.value.reference, status: 'paid', reason: pay.value.reason,
    })
    payFor.value = null
    await load()
  } catch (e: any) {
    formError.value = e?.response?.data?.error?.message || e?.response?.data?.detail || 'Could not save the payment.'
  } finally { saving.value = false }
}

async function exportCsv() {
  exporting.value = true
  try {
    const res = await taxApi.exportCsv(year.value)
    const url = URL.createObjectURL(res.data as Blob)
    const a = document.createElement('a')
    a.href = url; a.download = `fridah-tax-records-${year.value}.csv`; a.click()
    URL.revokeObjectURL(url)
  } catch { formError.value = 'Export failed. Please try again.' } finally { exporting.value = false }
}

onMounted(async () => { await Promise.all([load(), loadLookups()]) })
</script>
