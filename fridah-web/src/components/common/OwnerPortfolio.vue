<template>
  <div class="space-y-5">
    <div class="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <h1 class="page-title">Managed Properties &amp; Revenue</h1>
        <p class="text-sm text-gray-500 mt-0.5">Everything you own — who manages it, who is in it, and what it earned.</p>
      </div>
      <div class="flex items-center gap-2 flex-wrap">
        <select v-model="preset" class="input !w-auto text-sm" @change="onPreset">
          <option value="this_month">This month</option>
          <option value="last_month">Last month</option>
          <option value="last_90">Last 90 days</option>
          <option value="this_year">This year</option>
          <option value="custom">Custom range…</option>
        </select>
        <template v-if="preset === 'custom'">
          <input v-model="start" type="date" class="input !w-auto text-sm" @change="load" />
          <span class="text-gray-400 text-sm">to</span>
          <input v-model="end" type="date" class="input !w-auto text-sm" @change="load" />
        </template>
      </div>
    </div>

    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="card animate-pulse h-28 bg-gray-100 rounded-xl" />
    </div>

    <template v-else-if="data">
      <!-- Totals -->
      <div v-reveal="'up'" class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="card card-body"><p class="text-xs text-gray-400">Revenue collected</p><p class="text-xl font-black mt-1">{{ formatKES(data.totals.revenue_collected) }}</p><p class="text-[11px] text-gray-400 mt-0.5">{{ formatDate(data.period_start) }} – {{ formatDate(data.period_end) }}</p></div>
        <div class="card card-body"><p class="text-xs text-gray-400">Agency fees (est.)</p><p class="text-xl font-black mt-1 text-orange-500">{{ formatKES(data.totals.agency_fees) }}</p></div>
        <div class="card card-body"><p class="text-xs text-gray-400">Net to you (est.)</p><p class="text-xl font-black mt-1 text-emerald-600">{{ formatKES(data.totals.net_to_owner) }}</p></div>
        <div class="card card-body"><p class="text-xs text-gray-400">Agency-managed</p><p class="text-xl font-black mt-1">{{ data.totals.agency_managed }} <span class="text-sm font-medium text-gray-400">of {{ data.totals.agency_managed + data.totals.self_managed }}</span></p></div>
      </div>
      <p class="text-[11px] text-gray-400 -mt-2">Fees and net are estimates from each agency's agreed percentage. Your issued Statements are the authoritative figures.</p>

      <div class="flex items-center gap-2 text-sm">
        <button v-for="f in filters" :key="f.key" class="px-3 py-1.5 rounded-full border transition-colors"
          :class="filter === f.key ? 'bg-gray-900 text-white border-gray-900' : 'border-gray-200 text-gray-600 hover:bg-gray-50'"
          @click="filter = f.key">{{ f.label }}</button>
      </div>

      <div v-if="!shownProperties.length && !shownListings.length" class="card card-body text-center py-12 text-gray-400">
        Nothing to show here yet. Properties and listings you own will appear here, with the agency managing each one.
      </div>

      <!-- Rental properties -->
      <div v-for="(p, i) in shownProperties" :key="p.id" v-reveal="'up'" :style="{ transitionDelay: `${(i % 4) * 60}ms` }" class="card card-body">
        <div class="flex items-start gap-4 flex-wrap">
          <div class="w-11 h-11 rounded-xl bg-gray-100 flex items-center justify-center text-xl flex-shrink-0">🏢</div>
          <div class="flex-1 min-w-[220px]">
            <div class="flex items-center gap-2 flex-wrap">
              <p class="font-semibold text-gray-900">{{ p.name }}</p>
              <span v-if="p.managed_by" class="badge badge-blue text-xs">🏢 Managed by {{ p.managed_by.name }}</span>
              <span v-else class="badge badge-gray text-xs">Self-managed</span>
            </div>
            <p class="text-xs text-gray-500 mt-0.5">{{ p.town }}, {{ p.county }} · {{ p.occupied_units }} of {{ p.total_units }} units occupied</p>
          </div>
          <div class="grid grid-cols-3 gap-5 text-right">
            <div><p class="text-[11px] text-gray-400">Collected</p><p class="text-sm font-bold">{{ formatKES(p.revenue_collected) }}</p></div>
            <div><p class="text-[11px] text-gray-400">{{ p.managed_by ? 'Net to you' : 'Arrears' }}</p><p class="text-sm font-bold" :class="p.managed_by ? 'text-emerald-600' : 'text-red-500'">{{ formatKES(p.managed_by ? p.net_to_owner : p.arrears) }}</p></div>
            <div><p class="text-[11px] text-gray-400">Arrears</p><p class="text-sm font-bold text-red-500">{{ formatKES(p.arrears) }}</p></div>
          </div>
        </div>

        <div v-if="p.managed_by" class="mt-3 flex items-center justify-between flex-wrap gap-2 text-xs text-gray-500 bg-blue-50/60 rounded-xl px-3 py-2">
          <span>{{ p.managed_by.management_fee_percent }}% fee · {{ p.managed_by.payout_rule === 'agency_collects' ? 'Agency collects, remits to you' : 'You receive rent directly' }} · since {{ formatDate(p.managed_by.managed_since) }}</span>
          <span class="flex items-center gap-3">
            <a v-if="p.managed_by.phone_number" :href="`tel:${p.managed_by.phone_number}`" class="hover:text-blue-700">📞 {{ p.managed_by.phone_number }}</a>
            <a v-if="p.managed_by.email" :href="`mailto:${p.managed_by.email}`" class="hover:text-blue-700">✉️ {{ p.managed_by.email }}</a>
          </span>
        </div>

        <div class="mt-3 flex items-center gap-3">
          <button class="text-xs font-semibold" :class="accentText" @click="toggle(p.id)">
            {{ open.has(p.id) ? '▲ Hide' : '▼ Who lives here' }} ({{ p.tenants.length }})
          </button>
          <RouterLink :to="`${statementsPath}?property=${p.id}`" class="text-xs text-gray-500 underline">Statements &amp; payouts</RouterLink>
        </div>

        <div v-if="open.has(p.id)" class="mt-3 overflow-x-auto">
          <table v-if="p.tenants.length" class="w-full text-sm">
            <thead><tr class="text-left text-[11px] uppercase tracking-wide text-gray-400">
              <th class="py-1.5 pr-4">Tenant</th><th class="pr-4">Unit</th><th class="pr-4">Rent</th><th class="pr-4">Phone</th><th>Lease ends</th>
            </tr></thead>
            <tbody>
              <tr v-for="t in p.tenants" :key="t.unit + t.name" class="border-t border-gray-100">
                <td class="py-2 pr-4 font-medium text-gray-900">{{ t.name }}</td>
                <td class="pr-4">{{ t.unit }}</td>
                <td class="pr-4">{{ formatKES(t.rent_amount) }}</td>
                <td class="pr-4 text-gray-500">{{ t.phone_number }}</td>
                <td class="text-gray-500">{{ t.lease_end ? formatDate(t.lease_end) : 'Open-ended' }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else class="text-sm text-gray-400 py-2">No active tenants right now.</p>
        </div>
      </div>

      <!-- Hotels / short-stay -->
      <div v-for="(l, i) in shownListings" :key="l.id" v-reveal="'up'" :style="{ transitionDelay: `${(i % 4) * 60}ms` }" class="card card-body">
        <div class="flex items-start gap-4 flex-wrap">
          <div class="w-11 h-11 rounded-xl bg-gray-100 flex items-center justify-center text-xl flex-shrink-0">🏨</div>
          <div class="flex-1 min-w-[220px]">
            <div class="flex items-center gap-2 flex-wrap">
              <p class="font-semibold text-gray-900">{{ l.name }}</p>
              <span v-if="l.managed_by" class="badge badge-blue text-xs">🏢 Managed by {{ l.managed_by.name }}</span>
              <span v-else class="badge badge-gray text-xs">Self-managed</span>
              <span class="badge badge-gray text-xs capitalize">{{ l.listing_type }}</span>
            </div>
            <p class="text-xs text-gray-500 mt-0.5">{{ l.town }}, {{ l.county }} · {{ l.occupancy_percent }}% occupancy this period</p>
          </div>
          <div class="grid grid-cols-2 gap-5 text-right">
            <div><p class="text-[11px] text-gray-400">Collected</p><p class="text-sm font-bold">{{ formatKES(l.revenue_collected) }}</p></div>
            <div><p class="text-[11px] text-gray-400">Net to you</p><p class="text-sm font-bold text-emerald-600">{{ formatKES(l.net_to_owner) }}</p></div>
          </div>
        </div>

        <div v-if="l.managed_by" class="mt-3 flex items-center justify-between flex-wrap gap-2 text-xs text-gray-500 bg-blue-50/60 rounded-xl px-3 py-2">
          <span>{{ l.managed_by.management_fee_percent }}% fee · {{ l.managed_by.payout_rule === 'agency_collects' ? 'Agency collects, remits to you' : 'You receive revenue directly' }} · since {{ formatDate(l.managed_by.managed_since) }}</span>
          <span class="flex items-center gap-3">
            <a v-if="l.managed_by.phone_number" :href="`tel:${l.managed_by.phone_number}`" class="hover:text-blue-700">📞 {{ l.managed_by.phone_number }}</a>
            <a v-if="l.managed_by.email" :href="`mailto:${l.managed_by.email}`" class="hover:text-blue-700">✉️ {{ l.managed_by.email }}</a>
          </span>
        </div>

        <div class="mt-3 flex items-center gap-3">
          <button class="text-xs font-semibold" :class="accentText" @click="toggle(l.id)">
            {{ open.has(l.id) ? '▲ Hide' : '▼ Guests in house' }} ({{ l.guests_in_house.length }})
          </button>
          <RouterLink :to="`${statementsPath}?listing=${l.id}`" class="text-xs text-gray-500 underline">Statements &amp; payouts</RouterLink>
        </div>

        <div v-if="open.has(l.id)" class="mt-3 overflow-x-auto">
          <table v-if="l.guests_in_house.length" class="w-full text-sm">
            <thead><tr class="text-left text-[11px] uppercase tracking-wide text-gray-400">
              <th class="py-1.5 pr-4">Guest</th><th class="pr-4">Room</th><th class="pr-4">Check-in</th><th>Check-out</th>
            </tr></thead>
            <tbody>
              <tr v-for="g in l.guests_in_house" :key="g.name + g.check_in" class="border-t border-gray-100">
                <td class="py-2 pr-4 font-medium text-gray-900">{{ g.name }}</td>
                <td class="pr-4">{{ g.room_type }}</td>
                <td class="pr-4 text-gray-500">{{ formatDate(g.check_in) }}</td>
                <td class="text-gray-500">{{ formatDate(g.check_out) }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else class="text-sm text-gray-400 py-2">No guests checked in right now.</p>
        </div>
      </div>
    </template>

    <p v-else class="text-sm text-red-500">Couldn't load your portfolio. Please refresh.</p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { agencyApi } from '@/api/services'
import { formatKES, formatDate } from '@/utils/formatters'
import type { OwnerPortfolio } from '@/types'

defineProps<{ statementsPath: string; accentText: string }>()

const data = ref<OwnerPortfolio | null>(null)
const loading = ref(true)
const preset = ref('this_month')
const filter = ref<'all' | 'agency' | 'self'>('all')
const open = ref(new Set<string>())
const filters = [
  { key: 'all', label: 'All' }, { key: 'agency', label: 'Agency-managed' }, { key: 'self', label: 'Self-managed' },
] as const

const iso = (d: Date) => d.toISOString().slice(0, 10)
const now = new Date()
const start = ref(iso(new Date(now.getFullYear(), now.getMonth(), 1)))
const end = ref(iso(now))

function onPreset() {
  const y = now.getFullYear(), m = now.getMonth()
  if (preset.value === 'this_month') { start.value = iso(new Date(y, m, 1)); end.value = iso(now) }
  else if (preset.value === 'last_month') { start.value = iso(new Date(y, m - 1, 1)); end.value = iso(new Date(y, m, 0)) }
  else if (preset.value === 'last_90') { start.value = iso(new Date(now.getTime() - 90 * 86400000)); end.value = iso(now) }
  else if (preset.value === 'this_year') { start.value = iso(new Date(y, 0, 1)); end.value = iso(now) }
  if (preset.value !== 'custom') load()
}

const matches = (selfManaged: boolean) =>
  filter.value === 'all' || (filter.value === 'self' ? selfManaged : !selfManaged)
const shownProperties = computed(() => (data.value?.properties || []).filter((p) => matches(p.self_managed)))
const shownListings = computed(() => (data.value?.listings || []).filter((l) => matches(l.self_managed)))

function toggle(id: string) {
  const next = new Set(open.value)
  next.has(id) ? next.delete(id) : next.add(id)
  open.value = next
}

async function load() {
  loading.value = true
  try {
    const res = await agencyApi.ownerPortfolio({ period_start: start.value, period_end: end.value })
    data.value = (res.data as any).data
  } catch {
    data.value = null
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
