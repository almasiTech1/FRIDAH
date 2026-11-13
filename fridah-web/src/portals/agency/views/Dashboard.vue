<template>
  <div class="fx-page">
    <DashHeader :name="auth.user?.first_name || 'there'" :subtitle="currentAgency?.name || 'Your agency'">
      <RouterLink to="/agency/staff" class="fx-btn"><UserPlus /> Invite staff</RouterLink>
      <RouterLink to="/agency/statements" class="fx-btn accent"><Receipt /> Generate statement</RouterLink>
    </DashHeader>

    <div v-if="!loading && !currentAgency" class="fx-panel text-center py-12">
      <p class="font-bold">You're not part of an agency.</p>
      <p class="text-sm mt-1" style="color:var(--muted)">Agencies are registered by a FRIDAH administrator. Contact support if your company should have one.</p>
    </div>

    <template v-if="currentAgency">
      <div class="fx-grid k4">
        <StatCard label="Managed properties" :value="currentAgency.managed_properties_count" :icon-comp="Building2" color="#0e0e0e" to="/agency/properties" variant="accent" />
        <StatCard label="Property owners" :value="currentAgency.owners_count" :icon-comp="Users" color="#6366f1" />
        <StatCard label="Draft statements" :value="draftStatementsCount" :icon-comp="Receipt" color="#f59e0b" to="/agency/statements" />
        <StatCard label="Pending payouts" :value="pendingPayoutsCount" :icon-comp="Wallet" color="#10b981" to="/agency/payouts" variant="inverse" />
      </div>

      <section v-if="rollup?.collected_by_month?.length" v-spot class="fx-panel">
        <div class="fx-panel-head">
          <div><h3>Rent collected, month by month</h3><p>Actual completed rent payments across your properties · click a bar</p></div>
          <SegTabs :model-value="trend.range.value" :options="trend.ranges" @update:model-value="trend.setRange" />
        </div>
        <div class="flex items-baseline gap-3 mb-1"><span class="fx-hero-amount">{{ compactKES(trend.selValue.value) }}</span>
          <span class="fx-chip" :class="trend.delta.value < 0 ? 'down' : ''">{{ trend.delta.value >= 0 ? '▲' : '▼' }} {{ Math.abs(trend.delta.value) }}%</span>
          <span class="text-xs" style="color:var(--muted)">{{ trend.labels.value[trend.selected.value] }}</span></div>
        <InteractiveBars :key="trend.range.value" v-model="trend.sel.value" :labels="trend.labels.value" :values="trend.values.value" :height="200" />
      </section>

      <div v-if="rollup" class="fx-grid main-side">
        <section v-spot class="fx-panel">
          <div class="fx-panel-head">
            <div><h3>Collected rent by property</h3><p>This month · hover to compare</p></div>
            <span class="fx-chip neutral">{{ rollup.properties.length }} properties</span>
          </div>
          <InteractiveBars v-if="rollup.properties.length" v-model="selProp" :labels="rollup.properties.map((p: any) => shortName(p.property_name))" :values="rollup.properties.map((p: any) => Number(p.collected_this_month))" />
          <p v-else class="py-12 text-center text-sm" style="color:var(--muted)">No collections yet this month.</p>
        </section>
        <section v-spot class="fx-panel dark-card">
          <div class="fx-panel-head"><div><h3>Top performers</h3><p>Ranked by rent collected</p></div></div>
          <div class="space-y-4">
            <button v-for="(p, i) in ranked" :key="p.property_name" class="w-full text-left group" @click="selProp = rollup.properties.indexOf(p)">
              <div class="flex justify-between text-sm mb-1.5"><span class="font-semibold truncate pr-3"><span class="opacity-50 mr-2">{{ i + 1 }}</span>{{ p.property_name }}</span><b>{{ compactKES(Number(p.collected_this_month)) }}</b></div>
              <div class="h-2 rounded-full overflow-hidden" style="background:rgba(255,255,255,.1)"><div class="h-full rounded-full transition-all duration-700" :style="`width:${(Number(p.collected_this_month) / topValue) * 100}%;background:var(--accent)`" /></div>
            </button>
            <p v-if="!ranked.length" class="text-sm opacity-60 text-center py-6">Nothing to rank yet.</p>
          </div>
        </section>
      </div>

      <div v-if="rollup" class="fx-grid side-main">
        <section v-spot class="fx-panel">
          <div class="fx-panel-head"><div><h3>Portfolio occupancy</h3><p>Across every managed property</p></div></div>
          <DonutBreakdown :items="[{ label: 'Occupied', value: rollup.summary.occupied_units, color: 'var(--c1)' }, { label: 'Vacant', value: rollup.summary.vacant_units, color: 'var(--c3)' }]" center-label="Units" />
        </section>
        <section v-spot class="fx-panel"><div class="fx-panel-head"><div><h3>Quick actions</h3></div></div><QuickTiles :items="quick" /></section>
      </div>
      <QuickTiles v-else :items="quick" />
    </template>
  </div>
</template>
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { Building2, Users, Receipt, Wallet, UserPlus } from 'lucide-vue-next'
import { agencyApi } from '@/api/services'
import { useAuthStore } from '@/stores/auth'
import { compactKES } from '@/composables/useCountUp'
import StatCard from '@/components/common/StatCard.vue'
import DashHeader from '@/components/ui/DashHeader.vue'
import InteractiveBars from '@/components/ui/InteractiveBars.vue'
import SegTabs from '@/components/ui/SegTabs.vue'
import { useTrend } from '@/composables/useTrend'
import DonutBreakdown from '@/components/ui/DonutBreakdown.vue'
import QuickTiles from '@/components/ui/QuickTiles.vue'
import type { Agency, OwnerStatement, OwnerPayout } from '@/types'

const auth = useAuthStore()
const loading = ref(true)
const statements = ref<OwnerStatement[]>([])
const payouts = ref<OwnerPayout[]>([])
const rollup = ref<any>(null)
const selProp = ref(0)
const trend = useTrend(() => Number(rollup.value?.summary?.gross_rent_collected_this_month ?? 0), 0.05, 6, () => rollup.value?.collected_by_month)

const currentAgency = computed<Agency | null>(() => auth.agencies[0] || null)
const draftStatementsCount = computed(() => statements.value.filter((s) => s.status === 'draft').length)
const pendingPayoutsCount = computed(() => payouts.value.filter((p) => p.status === 'pending' || p.status === 'processing').length)
const ranked = computed<any[]>(() => (rollup.value?.properties || []).slice().sort((a: any, b: any) => Number(b.collected_this_month) - Number(a.collected_this_month)).slice(0, 5))
const topValue = computed(() => Math.max(1, ...ranked.value.map((p: any) => Number(p.collected_this_month))))
const shortName = (n: string) => (n.length > 10 ? `${n.slice(0, 9)}…` : n)
const quick = [
  { to: '/agency/properties', label: 'Manage properties', icon: Building2 }, { to: '/agency/staff', label: 'Invite staff', icon: UserPlus },
  { to: '/agency/statements', label: 'Generate statement', icon: Receipt }, { to: '/agency/payouts', label: 'Owner payouts', icon: Wallet },
]

async function load() {
  loading.value = true
  try {
    if (!auth.agencies.length) await auth.fetchAgencies()
    if (currentAgency.value) {
      const [stRes, poRes] = await Promise.all([agencyApi.statements(), agencyApi.payouts()])
      statements.value = (stRes.data as any).data?.results || (stRes.data as any).data || []
      payouts.value = (poRes.data as any).data?.results || (poRes.data as any).data || []
      try { const { data } = await agencyApi.dashboard(currentAgency.value.id); rollup.value = (data as any).data }
      catch { rollup.value = null }
    }
  } finally { loading.value = false }
}
onMounted(load)
</script>
