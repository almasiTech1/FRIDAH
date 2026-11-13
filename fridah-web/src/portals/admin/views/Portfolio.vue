<template>
  <div class="space-y-5">
    <div>
      <h1 class="page-title">Portfolio Overview</h1>
      <p class="text-sm text-gray-500 mt-0.5">Occupancy, collections and arrears across the platform.</p>
    </div>

    <form class="card card-body grid grid-cols-2 md:grid-cols-5 gap-3 items-end" @submit.prevent="load">
      <div><label class="text-xs font-medium text-gray-600" for="f-county">County</label>
        <input id="f-county" v-model="filters.county" class="input" placeholder="All" /></div>
      <div><label class="text-xs font-medium text-gray-600" for="f-type">Property type</label>
        <select id="f-type" v-model="filters.property_type" class="input">
          <option value="">All</option><option value="apartment">Apartment</option><option value="house">House</option>
          <option value="commercial">Commercial</option><option value="hostel">Hostel</option>
        </select></div>
      <div><label class="text-xs font-medium text-gray-600" for="f-from">Due from</label>
        <input id="f-from" v-model="filters.date_from" type="date" class="input" /></div>
      <div><label class="text-xs font-medium text-gray-600" for="f-to">Due to</label>
        <input id="f-to" v-model="filters.date_to" type="date" class="input" /></div>
      <div class="flex gap-2">
        <button class="btn bg-gray-900 text-white" :disabled="loading">Apply</button>
        <button type="button" class="btn-outline border-gray-200" @click="reset">Reset</button>
      </div>
    </form>

    <div v-if="loading" class="grid grid-cols-2 md:grid-cols-4 gap-3" aria-busy="true">
      <div v-for="i in 4" :key="i" class="card animate-pulse h-24 bg-gray-100 rounded-xl" />
    </div>
    <div v-else-if="error" class="card card-body text-center text-red-600" role="alert">{{ error }}</div>

    <template v-else-if="d">
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3 stagger">
        <div class="card card-body"><p class="text-xs text-gray-400">Properties</p><p class="text-2xl font-black">{{ d.properties.total }}</p>
          <p v-if="d.properties.oldest_pending_days !== null" class="text-xs text-orange-600">Oldest pending approval: {{ d.properties.oldest_pending_days }}d</p></div>
        <div class="card card-body"><p class="text-xs text-gray-400">Occupancy</p><p class="text-2xl font-black">{{ d.units.occupancy_rate }}%</p>
          <p class="text-xs text-gray-500">{{ d.units.occupied }} of {{ d.units.total }} units</p></div>
        <div class="card card-body"><p class="text-xs text-gray-400">Collection rate</p><p class="text-2xl font-black">{{ d.collections.collection_rate }}%</p>
          <p class="text-xs text-gray-500">{{ formatKES(d.collections.collected) }} of {{ formatKES(d.collections.billed) }}</p></div>
        <div class="card card-body"><p class="text-xs text-gray-400">Arrears</p><p class="text-2xl font-black text-red-600">{{ formatKES(d.collections.arrears_total) }}</p>
          <p class="text-xs text-gray-500">{{ d.failed_payments_30d }} failed payments (30d)</p></div>
      </div>

      <div class="grid md:grid-cols-2 gap-5">
        <div class="card card-body">
          <h2 class="font-semibold text-gray-900 mb-3">Arrears ageing</h2>
          <div v-for="b in ageing" :key="b.key" class="mb-3">
            <div class="flex justify-between text-xs text-gray-600 mb-1"><span>{{ b.label }}</span><span>{{ formatKES(b.value) }}</span></div>
            <div class="progress" role="img" :aria-label="`${b.label}: ${formatKES(b.value)}`">
              <div class="progress-bar bg-red-400" :style="{ width: b.pct + '%' }" />
            </div>
          </div>
        </div>
        <div class="card card-body">
          <h2 class="font-semibold text-gray-900 mb-3">Approval pipeline</h2>
          <ul class="text-sm space-y-1.5">
            <li v-for="(n, state) in d.properties.by_review_state" :key="state" class="flex justify-between">
              <span class="badge" :class="statusColor(String(state))">{{ reviewStateLabel(String(state)) }}</span><strong>{{ n }}</strong>
            </li>
          </ul>
        </div>
      </div>

      <div class="grid md:grid-cols-2 gap-5">
        <div class="card overflow-x-auto">
          <h2 class="font-semibold text-gray-900 p-5 pb-0">Top arrears properties</h2>
          <table class="w-full"><tbody>
            <tr v-for="r in d.top_arrears_properties" :key="r.property" class="table-tr">
              <td class="table-td">{{ r.name }}</td><td class="table-td text-right font-semibold text-red-600">{{ formatKES(r.arrears) }}</td>
            </tr>
            <tr v-if="!d.top_arrears_properties.length"><td class="p-6 text-center text-gray-400">No arrears.</td></tr>
          </tbody></table>
        </div>
        <div class="card overflow-x-auto">
          <h2 class="font-semibold text-gray-900 p-5 pb-0">By county</h2>
          <table class="w-full"><tbody>
            <tr v-for="c in d.by_county" :key="c.county" class="table-tr">
              <td class="table-td">{{ c.county }}</td><td class="table-td text-right">{{ c.properties }} properties · {{ c.units }} units</td>
            </tr>
          </tbody></table>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { portfolioApi } from '@/api/services'
import { formatKES, statusColor, reviewStateLabel } from '@/utils/formatters'

const d = ref<any | null>(null)
const loading = ref(true)
const error = ref('')
const blank = () => ({ county: '', property_type: '', date_from: '', date_to: '' })
const filters = ref(blank())

const ageing = computed(() => {
  const a = d.value?.collections.arrears_ageing || {}
  const rows = [['0_30', '0–30 days'], ['31_60', '31–60 days'], ['61_90', '61–90 days'], ['90_plus', '90+ days']]
  const max = Math.max(1, ...rows.map(([k]) => Number(a[k] || 0)))
  return rows.map(([k, label]) => ({ key: k, label, value: a[k] || 0, pct: Math.round((Number(a[k] || 0) / max) * 100) }))
})

async function load() {
  loading.value = true; error.value = ''
  const params = Object.fromEntries(Object.entries(filters.value).filter(([, v]) => v))
  try { d.value = ((await portfolioApi.overview(params)).data as any).data }
  catch { error.value = 'Could not load the portfolio overview.' } finally { loading.value = false }
}
const reset = () => { filters.value = blank(); load() }
onMounted(load)
</script>
