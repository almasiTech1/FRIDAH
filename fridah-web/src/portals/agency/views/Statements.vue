<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="page-title">Owner Statements</h1>
      <button class="btn-primary bg-agency-600 hover:bg-agency-700" @click="showGenerate = !showGenerate">+ Generate Statement</button>
    </div>

    <div v-if="showGenerate" class="card card-body space-y-4">
      <h2 class="section-title">Generate a Statement</h2>
      <div class="grid grid-cols-3 gap-4">
        <div><label class="label">Property / Listing</label>
          <select v-model="genForm.target" class="input">
            <option value="" disabled>Select what to generate for…</option>
            <option v-for="t in targets" :key="t.value" :value="t.value">{{ t.label }}</option>
          </select>
        </div>
        <div><label class="label">Period Start</label><input v-model="genForm.period_start" type="date" class="input"/></div>
        <div><label class="label">Period End</label><input v-model="genForm.period_end" type="date" class="input"/></div>
      </div>
      <div class="flex gap-3">
        <button class="btn-outline border-gray-200" @click="showGenerate = false">Cancel</button>
        <button class="btn-primary bg-agency-600 hover:bg-agency-700" :disabled="generating" @click="generate">
          <span v-if="generating" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"/>
          <span v-else>Generate</span>
        </button>
      </div>
      <p v-if="genError" class="text-sm text-red-600">{{ genError }}</p>
    </div>

    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="card animate-pulse h-24 bg-gray-100 rounded-xl"/>
    </div>
    <div v-else-if="statements.length" class="space-y-3">
      <div v-for="s in statements" :key="s.id" class="card card-body">
        <div class="flex items-center justify-between flex-wrap gap-2">
          <div>
            <div class="flex items-center gap-3 flex-wrap">
              <p class="font-semibold text-gray-900">{{ s.property_name || s.listing_name }}</p>
              <span :class="statusColor(s.status)" class="badge">{{ s.status }}</span>
            </div>
            <p class="text-xs text-gray-500 mt-0.5">{{ formatDate(s.period_start) }} – {{ formatDate(s.period_end) }} · Owner: {{ s.owner_name }}</p>
          </div>
          <div class="flex gap-2">
            <button v-if="s.status === 'draft'" class="btn-outline border-gray-200 text-xs" @click="issue(s.id)">Issue</button>
            <button v-if="s.status === 'issued'" class="btn-primary bg-emerald-600 hover:bg-emerald-700 text-xs" @click="payout(s.id)">Pay Owner</button>
          </div>
        </div>
        <div class="grid grid-cols-3 md:grid-cols-6 gap-3 mt-4 text-center">
          <div><p class="text-xs text-gray-400">Gross</p><p class="text-sm font-bold">{{ formatKES(s.gross_rent_collected) }}</p></div>
          <div><p class="text-xs text-gray-400">Vacancy</p><p class="text-sm font-bold text-orange-500">{{ formatKES(s.vacancy_loss) }}</p></div>
          <div><p class="text-xs text-gray-400">Arrears</p><p class="text-sm font-bold text-red-500">{{ formatKES(s.arrears) }}</p></div>
          <div><p class="text-xs text-gray-400">Commission</p><p class="text-sm font-bold text-agency-600">{{ formatKES(s.agency_commission) }}</p></div>
          <div><p class="text-xs text-gray-400">Expenses</p><p class="text-sm font-bold text-orange-500">{{ formatKES(s.approved_expenses) }}</p></div>
          <div><p class="text-xs text-gray-400">Net Payable</p><p class="text-base font-black text-emerald-600">{{ formatKES(s.net_payable) }}</p></div>
        </div>
      </div>
    </div>
    <div v-else class="card card-body text-center py-12 text-gray-400">No statements yet.</div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { agencyApi } from '@/api/services'
import { statusColor, formatDate, formatKES } from '@/utils/formatters'
import { useAuthStore } from '@/stores/auth'
import type { OwnerStatement, PropertyManagementAssignment } from '@/types'

const route = useRoute()
const auth = useAuthStore()
const targets = ref<{ value: string; label: string }[]>([])
const statements = ref<OwnerStatement[]>([])
const loading = ref(true)
const showGenerate = ref(false)
const generating = ref(false)
const genError = ref('')

const genForm = ref({
  target: route.query.property ? `property:${route.query.property}` : route.query.listing ? `listing:${route.query.listing}` : '',
  period_start: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().slice(0, 10),
  period_end: new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0).toISOString().slice(0, 10),
})

async function loadTargets() {
  if (!auth.agencies.length) await auth.fetchAgencies()
  const agencyId = auth.agencies[0]?.id
  if (!agencyId) return
  const { data } = await agencyApi.assignments({ agency: agencyId })
  const rows: PropertyManagementAssignment[] = (data as any).data?.results || (data as any).results || (data as any).data || []
  targets.value = rows.filter((a) => a.status === 'active').map((a) => ({
    value: a.item_type === 'listing' ? `listing:${a.listing}` : `property:${a.property}`,
    label: `${a.item_type === 'listing' ? '🏨' : '🏢'} ${a.property_name || a.listing_name} — owner: ${a.owner_name}`,
  }))
}

async function load() {
  loading.value = true
  try {
    const params: Record<string, unknown> = {}
    if (route.query.property) params.property = route.query.property
    if (route.query.listing) params.listing = route.query.listing
    const { data } = await agencyApi.statements(params)
    statements.value = (data as any).data?.results || (data as any).data || []
  } finally {
    loading.value = false
  }
}

async function generate() {
  generating.value = true; genError.value = ''
  try {
    const [kind, id] = genForm.value.target.split(':')
    if (!id) throw new Error('Select a property or listing first.')
    if (kind === 'listing') await agencyApi.generateListingStatement(id, genForm.value.period_start, genForm.value.period_end)
    else await agencyApi.generateStatement(id, genForm.value.period_start, genForm.value.period_end)
    showGenerate.value = false
    await load()
  } catch (e: any) {
    genError.value = e?.response?.data?.error?.message || e?.message || 'Failed to generate statement.'
  } finally {
    generating.value = false
  }
}

async function issue(id: string) {
  await agencyApi.issueStatement(id)
  await load()
}

async function payout(id: string) {
  if (!confirm('Send M-Pesa payout for the net payable amount to the owner?')) return
  try {
    await agencyApi.executePayout(id)
    await load()
  } catch (e: any) {
    alert(e?.response?.data?.error?.message || 'Payout failed to initiate.')
  }
}

onMounted(() => { load(); loadTargets() })
</script>
