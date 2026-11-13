<template>
  <div class="space-y-5">
    <div>
      <h1 class="page-title">Tax Configuration</h1>
      <p class="text-sm text-gray-500 mt-0.5">Tax types and effective-dated rules used to estimate landlords' tax.</p>
    </div>

    <div class="rounded-xl border border-amber-200 bg-amber-50 text-amber-900 text-sm p-4" role="note">
      Fridah ships with <strong>no tax rates</strong>. Tax treatment depends on taxpayer type, income type, thresholds,
      exemptions and current law. Have every rule validated by a qualified Kenyan tax adviser against current KRA guidance,
      then record the reviewer and date. A new rate is a <em>new rule version</em>; old versions are never edited, so past
      figures stay reproducible.
    </div>

    <div class="grid md:grid-cols-2 gap-5">
      <form class="card card-body space-y-3" @submit.prevent="addType">
        <h2 class="font-semibold text-gray-900">Add tax type</h2>
        <div><label class="text-xs font-medium text-gray-600" for="tt-code">Code</label>
          <input id="tt-code" v-model="typeForm.code" class="input" required pattern="[a-z0-9-]+" placeholder="rental-income" /></div>
        <div><label class="text-xs font-medium text-gray-600" for="tt-name">Name</label>
          <input id="tt-name" v-model="typeForm.name" class="input" required /></div>
        <button class="btn bg-gray-900 text-white" :disabled="saving">Add type</button>
        <ul class="text-sm text-gray-600 divide-y divide-gray-100">
          <li v-for="t in types" :key="t.id" class="py-1.5">{{ t.name }} <span class="text-gray-400">({{ t.code }})</span></li>
        </ul>
      </form>

      <form class="card card-body grid grid-cols-2 gap-3" @submit.prevent="addRule">
        <h2 class="font-semibold text-gray-900 col-span-2">Add rule version</h2>
        <div class="col-span-2"><label class="text-xs font-medium text-gray-600" for="r-type">Tax type</label>
          <select id="r-type" v-model="ruleForm.tax_type" class="input" required>
            <option value="" disabled>Choose…</option>
            <option v-for="t in types" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select></div>
        <div><label class="text-xs font-medium text-gray-600" for="r-method">Method</label>
          <select id="r-method" v-model="ruleForm.method" class="input">
            <option value="percent_of_gross">% of gross income</option>
            <option value="percent_of_net">% after allowable expenses</option>
            <option value="flat">Flat amount</option>
          </select></div>
        <div><label class="text-xs font-medium text-gray-600" for="r-rate">Rate (%)</label>
          <input id="r-rate" v-model="ruleForm.rate" type="number" step="0.0001" min="0" class="input" /></div>
        <div><label class="text-xs font-medium text-gray-600" for="r-from">Effective from</label>
          <input id="r-from" v-model="ruleForm.effective_from" type="date" class="input" required /></div>
        <div><label class="text-xs font-medium text-gray-600" for="r-to">Effective to (optional)</label>
          <input id="r-to" v-model="ruleForm.effective_to" type="date" class="input" /></div>
        <div><label class="text-xs font-medium text-gray-600" for="r-thr">Threshold (KES)</label>
          <input id="r-thr" v-model="ruleForm.annual_threshold" type="number" min="0" step="0.01" class="input" /></div>
        <div><label class="text-xs font-medium text-gray-600" for="r-src">Source reference</label>
          <input id="r-src" v-model="ruleForm.source_reference" class="input" placeholder="KRA guidance / Finance Act" /></div>
        <div><label class="text-xs font-medium text-gray-600" for="r-by">Reviewed by (adviser)</label>
          <input id="r-by" v-model="ruleForm.professional_reviewed_by" class="input" /></div>
        <div><label class="text-xs font-medium text-gray-600" for="r-on">Reviewed on</label>
          <input id="r-on" v-model="ruleForm.professional_reviewed_on" type="date" class="input" /></div>
        <button class="btn bg-gray-900 text-white col-span-2 justify-center" :disabled="saving">Create rule</button>
      </form>
    </div>
    <p v-if="error" class="text-sm text-red-600" role="alert">{{ error }}</p>

    <div class="card overflow-x-auto">
      <table class="w-full text-sm">
        <thead><tr>
          <th class="table-th">Type</th><th class="table-th">Version</th><th class="table-th">Method</th>
          <th class="table-th">Rate</th><th class="table-th">Effective</th><th class="table-th">Review</th>
        </tr></thead>
        <tbody>
          <tr v-for="r in rules" :key="r.id" class="table-tr">
            <td class="table-td">{{ r.tax_type_code }}</td>
            <td class="table-td">v{{ r.version }}</td>
            <td class="table-td">{{ r.method.replace(/_/g, ' ') }}</td>
            <td class="table-td">{{ r.method === 'flat' ? formatKES(r.flat_amount) : `${Number(r.rate)}%` }}</td>
            <td class="table-td">{{ formatDate(r.effective_from) }}{{ r.effective_to ? ` – ${formatDate(r.effective_to)}` : ' onward' }}</td>
            <td class="table-td">
              <span v-if="r.is_professionally_reviewed" class="badge badge-green">Reviewed · {{ r.professional_reviewed_by }}</span>
              <span v-else class="badge badge-yellow">Not professionally reviewed</span>
            </td>
          </tr>
          <tr v-if="!rules.length"><td colspan="6" class="p-8 text-center text-gray-400">No rules configured.</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { taxApi } from '@/api/services'
import { formatDate, formatKES } from '@/utils/formatters'

const types = ref<any[]>([])
const rules = ref<any[]>([])
const saving = ref(false)
const error = ref('')
const typeForm = ref({ code: '', name: '' })
const blankRule = () => ({
  tax_type: '', method: 'percent_of_gross', rate: '0', effective_from: '', effective_to: '', annual_threshold: '0',
  source_reference: '', professional_reviewed_by: '', professional_reviewed_on: '',
})
const ruleForm = ref(blankRule())
const list = (res: any) => res.data?.data?.results || res.data?.results || res.data?.data || []

async function load() {
  try { types.value = list(await taxApi.types()) } catch { types.value = [] }
  try { rules.value = list(await taxApi.rules()) } catch { rules.value = [] }
}
const fail = (e: any) => {
  const d = e?.response?.data
  error.value = d?.error?.message || (d && typeof d === 'object' ? Object.values(d).flat().join(' ') : '') || 'Could not save.'
}
async function addType() {
  saving.value = true; error.value = ''
  try { await taxApi.createType(typeForm.value); typeForm.value = { code: '', name: '' }; await load() }
  catch (e) { fail(e) } finally { saving.value = false }
}
async function addRule() {
  saving.value = true; error.value = ''
  const body: Record<string, unknown> = { ...ruleForm.value }
  for (const k of ['effective_to', 'professional_reviewed_on']) if (!body[k]) delete body[k]
  try { await taxApi.createRule(body); ruleForm.value = blankRule(); await load() }
  catch (e) { fail(e) } finally { saving.value = false }
}
onMounted(load)
</script>
