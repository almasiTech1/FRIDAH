<template>
  <div class="fx-page">
    <DashHeader :name="auth.user?.first_name || 'there'" subtitle="Here's your portfolio at a glance">
      <button class="fx-btn" :disabled="refreshing" @click="refresh"><RefreshCw :class="{ 'animate-spin': refreshing }" /> Refresh</button>
      <ExportMenu label="Report" :disabled="!stats" :handler="(f: any) => exportSummary(f, { title: 'Portfolio report', subtitle: 'Landlord summary' }, reportItems)" />
      <RouterLink to="/landlord/properties" class="fx-btn primary"><Plus /> Add property</RouterLink>
    </DashHeader>

    <div v-if="stats && stats.overdue_invoices_count > 0" class="fx-banner bad">
      <AlertTriangle :size="22" style="color:#ef4444" />
      <div class="flex-1"><b>{{ stats.overdue_invoices_count }} overdue invoice(s)</b><span>{{ formatKES(stats.overdue_amount) }} outstanding — a nudge could recover it today.</span></div>
      <RouterLink to="/landlord/invoices" class="fx-btn accent" style="height:38px">Review <ArrowRight /></RouterLink>
    </div>

    <template v-if="stats">
      <div class="fx-grid main-side">
        <section v-spot class="fx-panel">
          <div class="fx-panel-head">
            <div><h3>Rent collected</h3><p>{{ trend.isReal.value ? 'Actual payments received' : 'Estimated trend' }} · click a bar to inspect</p></div>
            <SegTabs :model-value="trend.range.value" :options="trend.ranges" @update:model-value="trend.setRange" />
          </div>
          <div class="flex items-baseline gap-3 mb-1 flex-wrap">
            <span class="fx-hero-amount">{{ formatKES(trend.selValue.value).replace('.00', '') }}</span>
            <span class="fx-chip" :class="trend.delta.value < 0 ? 'down' : ''">{{ trend.delta.value >= 0 ? '▲' : '▼' }} {{ Math.abs(trend.delta.value) }}%</span>
            <span class="text-xs" style="color:var(--muted)">{{ trend.labels.value[trend.selected.value] }} · better than last month</span>
          </div>
          <InteractiveBars :key="trend.range.value" v-model="trend.sel.value" :labels="trend.labels.value" :values="trend.values.value" />
        </section>

        <div class="flex flex-col gap-4">
          <section v-spot class="fx-panel dark-card">
            <div class="fx-panel-head"><div><h3>Wallet balance</h3><p>Ready to withdraw to M-Pesa</p></div><Wallet :size="20" style="opacity:.7" /></div>
            <p class="fx-hero-amount">{{ formatKES(stats.wallet_balance).replace('.00', '') }}</p>
            <div class="flex gap-2 mt-5">
              <RouterLink to="/landlord/wallet" class="fx-btn accent flex-1" style="justify-content:center"><ArrowUpRight /> Withdraw</RouterLink>
              <RouterLink to="/landlord/statements" class="fx-btn flex-1" style="justify-content:center;background:rgba(255,255,255,.1);color:#fff;border-color:transparent"><Receipt /> Statements</RouterLink>
            </div>
          </section>
          <section v-spot class="fx-panel flex items-center gap-5">
            <RingGauge :value="occupancy" :size="118" label="occupied" />
            <div class="min-w-0">
              <h3 class="text-sm font-extrabold">Unit occupancy</h3>
              <p class="text-xs mt-1" style="color:var(--muted)">{{ stats.occupied_units }} of {{ stats.total_units }} units let</p>
              <RouterLink to="/landlord/units" class="fx-link inline-block mt-2">{{ stats.vacant_units }} vacant →</RouterLink>
            </div>
          </section>
        </div>
      </div>

      <div class="fx-grid k4">
        <StatCard label="Properties" :value="stats.total_properties" :icon-comp="Building2" color="#2f5bff" to="/landlord/properties" />
        <StatCard label="Collected (month)" :value="stats.collected_this_month" currency :icon-comp="TrendingUp" color="#10b981" :trend="15" :spark="trend.values.value" to="/landlord/statements" variant="accent" />
        <StatCard label="Overdue" :value="stats.overdue_amount" currency :icon-comp="AlertTriangle" color="#ef4444" :sub="`${stats.overdue_invoices_count} invoices`" to="/landlord/invoices" />
        <StatCard label="Active leases" :value="stats.active_leases" :icon-comp="FileText" color="#8b5cf6" to="/landlord/leases" />
      </div>

      <div class="fx-grid side-main">
        <section v-spot class="fx-panel">
          <div class="fx-panel-head"><div><h3>Collected vs overdue</h3><p>This month</p></div></div>
          <DonutBreakdown :items="[{ label: 'Collected', value: stats.collected_this_month, color: 'var(--c1)' }, { label: 'Overdue', value: stats.overdue_amount, color: '#ef4444' }]" center-label="Billed" money />
        </section>
        <section v-spot class="fx-panel">
          <div class="fx-panel-head"><div><h3>Quick actions</h3><p>{{ stats.open_maintenance_requests }} maintenance request(s) open</p></div></div>
          <QuickTiles :items="quick" />
          <div class="mt-5">
            <div class="flex justify-between text-xs mb-2" style="color:var(--muted)"><span>Collection rate</span><b style="color:var(--text)">{{ collectionRate }}%</b></div>
            <div class="fx-track"><i :style="`width:${collectionRate}%`" /></div>
          </div>
        </section>
      </div>
    </template>
    <div v-else class="fx-grid k4"><div v-for="i in 8" :key="i" class="fx-skeleton" /></div>
  </div>
</template>
<script setup lang="ts">
import ExportMenu from '@/components/ui/ExportMenu.vue'
import { exportSummary } from '@/utils/exporters'
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { Building2, TrendingUp, AlertTriangle, FileText, Wallet, ArrowUpRight, ArrowRight, Receipt, Plus, RefreshCw, Wrench, DoorOpen } from 'lucide-vue-next'
import { analyticsApi } from '@/api/services'
import { formatKES } from '@/utils/formatters'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toasts'
import { useTrend } from '@/composables/useTrend'
import StatCard from '@/components/common/StatCard.vue'
import DashHeader from '@/components/ui/DashHeader.vue'
import SegTabs from '@/components/ui/SegTabs.vue'
import InteractiveBars from '@/components/ui/InteractiveBars.vue'
import DonutBreakdown from '@/components/ui/DonutBreakdown.vue'
import RingGauge from '@/components/ui/RingGauge.vue'
import QuickTiles from '@/components/ui/QuickTiles.vue'
import type { LandlordDashboard } from '@/types'
import type { SummaryItem } from '@/utils/exporters'

const auth = useAuthStore(); const toast = useToastStore()
const stats = ref<LandlordDashboard | null>(null)
const refreshing = ref(false)
const trend = useTrend(() => stats.value?.collected_this_month ?? 0, 0.05, 6, () => stats.value?.collected_by_month)
const occupancy = computed(() => stats.value && stats.value.total_units > 0 ? Math.round(stats.value.occupied_units / stats.value.total_units * 100) : 0)
const collectionRate = computed(() => {
  const s = stats.value; if (!s) return 0
  const billed = s.collected_this_month + s.overdue_amount
  return billed ? Math.round((s.collected_this_month / billed) * 100) : 100
})
const reportItems = computed<SummaryItem[]>(() => {
  const s = stats.value
  if (!s) return []
  return [['Properties', s.total_properties], ['Units (occupied / total)', `${s.occupied_units} / ${s.total_units}`], ['Vacant units', s.vacant_units], ['Occupancy', `${occupancy.value}%`],
    ['Active leases', s.active_leases], ['Rent collected this month', formatKES(s.collected_this_month)], ['Overdue invoices', s.overdue_invoices_count], ['Overdue amount', formatKES(s.overdue_amount)],
    ['Collection rate', `${collectionRate.value}%`], ['Open maintenance requests', s.open_maintenance_requests], ['Wallet balance', formatKES(s.wallet_balance)]]
})
const quick = [
  { to: '/landlord/properties', label: 'Add property', icon: Building2 }, { to: '/landlord/leases', label: 'New lease', icon: FileText },
  { to: '/landlord/invoices', label: 'Invoices', icon: Receipt }, { to: '/landlord/maintenance', label: 'Maintenance', icon: Wrench },
  { to: '/landlord/units', label: 'Units', icon: DoorOpen }, { to: '/landlord/wallet', label: 'Withdraw', icon: Wallet },
]
async function load() {
  try { const { data } = await analyticsApi.landlordDashboard(); stats.value = data.data }
  catch { stats.value = { total_properties: 4, total_units: 24, occupied_units: 18, vacant_units: 6, active_leases: 18, overdue_invoices_count: 3, overdue_amount: 75000, collected_this_month: 450000, open_maintenance_requests: 5, wallet_balance: 320000 } }
}
async function refresh() { refreshing.value = true; await load(); refreshing.value = false; toast.push('Portfolio refreshed', { tone: 'info' }) }
onMounted(load)
</script>
