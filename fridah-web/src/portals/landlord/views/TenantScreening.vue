<template>
  <div class="space-y-5">
    <div class="page-header"><h1 class="page-title">Tenant Screening</h1></div>

    <div class="card card-body">
      <label class="label">Select tenant (from your leases)</label>
      <select v-model="selectedTenantId" class="input" @change="lookup">
        <option value="">Choose a tenant…</option>
        <option v-for="t in tenants" :key="t.id" :value="t.id">{{ t.name }} - {{ t.unit }}</option>
      </select>
    </div>

    <div v-if="loading" class="card card-body animate-pulse h-32" />

    <template v-else-if="selectedTenantId">
      <div class="card card-body">
        <h2 class="section-title">{{ $t('riskScore.title') }}</h2>
        <div v-if="riskScore" class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="stat-card !p-4">
            <p class="text-3xl font-black" :class="riskScoreColor(riskScore.score)">{{ riskScore.score }}<span class="text-sm text-gray-400">/10</span></p>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Risk score</p>
          </div>
          <div><p class="text-gray-500 dark:text-gray-400 text-sm">{{ $t('riskScore.onTimeRate') }}</p><p class="font-semibold">{{ riskScore.on_time_payment_rate }}%</p></div>
          <div><p class="text-gray-500 dark:text-gray-400 text-sm">{{ $t('riskScore.kycVerified') }}</p><p class="font-semibold">{{ riskScore.is_kyc_verified ? 'Yes' : 'No' }}</p></div>
          <div><p class="text-gray-500 dark:text-gray-400 text-sm">{{ $t('riskScore.monthsOnPlatform') }}</p><p class="font-semibold">{{ riskScore.months_on_platform }}</p></div>
        </div>
        <button class="btn-outline mt-4 text-xs" :disabled="recalculating" @click="recalculate">Recalculate now</button>
      </div>

      <div class="card card-body">
        <div class="flex items-center justify-between mb-4">
          <h2 class="section-title mb-0">{{ $t('nav.blacklist') }}</h2>
          <button class="btn-outline text-xs" @click="showFlagForm = !showFlagForm">{{ $t('blacklist.flagTenant') }}</button>
        </div>

        <div v-if="showFlagForm" class="space-y-3 mb-5 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-xl">
          <div>
            <label class="label">{{ $t('blacklist.reason') }}</label>
            <select v-model="flagForm.reason" class="input">
              <option value="non_payment">Non-payment of rent</option>
              <option value="property_damage">Property damage</option>
              <option value="lease_violation">Lease violation</option>
              <option value="abandonment">Abandoned unit without notice</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div><label class="label">{{ $t('blacklist.details') }}</label><textarea v-model="flagForm.details" class="input" rows="2"/></div>
          <div><label class="label">{{ $t('blacklist.amountOwed') }} (optional)</label><input v-model.number="flagForm.amount_owed" type="number" class="input"/></div>
          <button class="btn-primary bg-red-600 hover:bg-red-700" :disabled="flagging" @click="submitFlag">Submit flag</button>
        </div>

        <div v-if="flags.length" class="space-y-3">
          <div v-for="f in flags" :key="f.id" class="p-4 border border-gray-100 dark:border-gray-800 rounded-xl">
            <div class="flex items-center justify-between">
              <span class="badge-red badge">{{ f.reason.replace('_', ' ') }}</span>
              <span class="text-xs text-gray-400">{{ formatDate(f.created_at) }}</span>
            </div>
            <p class="text-sm text-gray-700 dark:text-gray-300 mt-2">{{ f.details }}</p>
            <p v-if="f.amount_owed" class="text-sm font-medium mt-1">Amount owed: {{ formatKES(f.amount_owed) }}</p>
          </div>
        </div>
        <p v-else class="text-sm text-gray-400 dark:text-gray-500">No active blacklist flags for this tenant.</p>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { rentalsApi, riskScoreApi, blacklistApi } from '@/api/services'
import { formatKES, formatDate } from '@/utils/formatters'

const tenants = ref<{ id: string; name: string; unit: string }[]>([])
const selectedTenantId = ref('')
const loading = ref(false)
const riskScore = ref<any>(null)
const flags = ref<any[]>([])
const recalculating = ref(false)
const showFlagForm = ref(false)
const flagging = ref(false)
const flagForm = ref({ reason: 'non_payment', details: '', amount_owed: undefined as number | undefined })

function riskScoreColor(score: number) {
  if (score >= 7) return 'text-emerald-600 dark:text-emerald-400'
  if (score >= 4) return 'text-amber-600 dark:text-amber-400'
  return 'text-red-600 dark:text-red-400'
}

async function loadTenants() {
  const { data } = await rentalsApi.leases()
  const leases = data.data?.results || data.data || []
  const seen = new Set<string>()
  tenants.value = leases
    .filter((l: any) => { if (seen.has(l.tenant)) return false; seen.add(l.tenant); return true })
    .map((l: any) => ({ id: l.tenant, name: l.tenant_name, unit: `${l.property_name} - ${l.unit_number}` }))
}

async function lookup() {
  if (!selectedTenantId.value) return
  loading.value = true
  try {
    const [riskRes, flagsRes] = await Promise.all([
      riskScoreApi.get(selectedTenantId.value),
      blacklistApi.check(selectedTenantId.value),
    ])
    riskScore.value = riskRes.data.data
    flags.value = flagsRes.data.data?.flags || []
  } finally { loading.value = false }
}

async function recalculate() {
  recalculating.value = true
  try {
    const { data } = await riskScoreApi.recalculate(selectedTenantId.value)
    riskScore.value = data.data
  } finally { recalculating.value = false }
}

async function submitFlag() {
  flagging.value = true
  try {
    await blacklistApi.flag({ tenant: selectedTenantId.value, ...flagForm.value })
    showFlagForm.value = false
    flagForm.value = { reason: 'non_payment', details: '', amount_owed: undefined }
    await lookup()
  } finally { flagging.value = false }
}

onMounted(loadTenants)
</script>
