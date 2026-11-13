<template>
  <div class="fx-page">
    <DashHeader :name="auth.user?.first_name || 'there'" subtitle="Your service provider overview">
      <RouterLink to="/provider/quotes" class="fx-btn"><FileText /> My quotes</RouterLink>
      <RouterLink to="/provider/jobs" class="fx-btn accent"><Search /> Browse jobs</RouterLink>
    </DashHeader>

    <template v-if="stats">
      <div class="fx-grid k3">
        <StatCard label="Active jobs" :value="stats.active_jobs" sub="assigned / in progress" :icon-comp="Hammer" color="#7a67d8" :spark="[2,3,2,4,3,5,stats.active_jobs]" to="/provider/my-jobs" />
        <StatCard label="Completed jobs" :value="stats.completed_jobs" :icon-comp="CheckCircle2" color="#34d399" :trend="9" :spark="[6,8,9,12,13,16,stats.completed_jobs]" />
        <StatCard label="Wallet balance" :value="stats.wallet_balance" currency :icon-comp="Wallet" color="#fb923c" to="/provider/wallet" variant="accent" />
      </div>

      <section v-if="stats.earnings_by_month?.length" v-spot class="fx-panel">
        <div class="fx-panel-head">
          <div><h3>Earnings</h3><p>Actual wallet credits after commission · click a bar</p></div>
          <SegTabs :model-value="trend.range.value" :options="trend.ranges" @update:model-value="trend.setRange" />
        </div>
        <div class="flex items-baseline gap-3 mb-1"><span class="fx-hero-amount">{{ compactKES(trend.selValue.value) }}</span>
          <span class="fx-chip" :class="trend.delta.value < 0 ? 'down' : ''">{{ trend.delta.value >= 0 ? '▲' : '▼' }} {{ Math.abs(trend.delta.value) }}%</span>
          <span class="text-xs" style="color:var(--muted)">{{ trend.labels.value[trend.selected.value] }}</span></div>
        <InteractiveBars :key="trend.range.value" v-model="trend.sel.value" :labels="trend.labels.value" :values="trend.values.value" :height="200" />
      </section>

      <div class="fx-grid side-main">
        <section v-spot class="fx-panel">
          <div class="fx-panel-head"><div><h3>Jobs breakdown</h3><p>Hover a slice to focus it</p></div></div>
          <DonutBreakdown :items="[{ label: 'Active', value: stats.active_jobs, color: 'var(--c1)' }, { label: 'Completed', value: stats.completed_jobs, color: 'var(--c2)' }]" center-label="Jobs" />
        </section>
        <section v-spot class="fx-panel">
          <div class="fx-panel-head"><div><h3>Quote pipeline</h3><p>From first quote to accepted work</p></div><RouterLink to="/provider/quotes" class="fx-link">Open quotes</RouterLink></div>
          <div class="space-y-5">
            <div v-for="row in pipeline" :key="row.label">
              <div class="flex justify-between text-sm mb-2"><span class="font-semibold">{{ row.label }}</span><b>{{ row.value }}</b></div>
              <div class="fx-track"><i :style="`width:${row.pct}%;background:${row.color}`" /></div>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-3 mt-6">
            <RouterLink to="/provider/jobs" class="fx-tile"><span class="fx-ico"><Search /></span>{{ stats.available_open_jobs }} open jobs in your area</RouterLink>
            <RouterLink to="/provider/profile" class="fx-tile"><span class="fx-ico"><UserRound /></span>Polish your profile</RouterLink>
          </div>
        </section>
      </div>
      <QuickTiles :items="quick" />
    </template>
    <div v-else class="fx-grid k3"><div v-for="i in 6" :key="i" class="fx-skeleton" /></div>
  </div>
</template>
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { FileText, Search, Hammer, CheckCircle2, Wallet, UserRound, ClipboardList } from 'lucide-vue-next'
import { analyticsApi } from '@/api/services'
import { useAuthStore } from '@/stores/auth'
import StatCard from '@/components/common/StatCard.vue'
import DashHeader from '@/components/ui/DashHeader.vue'
import DonutBreakdown from '@/components/ui/DonutBreakdown.vue'
import SegTabs from '@/components/ui/SegTabs.vue'
import InteractiveBars from '@/components/ui/InteractiveBars.vue'
import { useTrend } from '@/composables/useTrend'
import { compactKES } from '@/composables/useCountUp'
import QuickTiles from '@/components/ui/QuickTiles.vue'
import type { ServiceProviderDashboard } from '@/types'

const auth = useAuthStore()
const stats = ref<ServiceProviderDashboard | null>(null)
const trend = useTrend(() => 0, 0.06, 6, () => stats.value?.earnings_by_month)
const pipeline = computed(() => {
  const s = stats.value; if (!s) return []
  const max = Math.max(1, s.pending_quotes + s.accepted_quotes, s.available_open_jobs)
  return [
    { label: 'Open jobs available', value: s.available_open_jobs, pct: (s.available_open_jobs / max) * 100, color: 'var(--c5)' },
    { label: 'Pending quotes', value: s.pending_quotes, pct: (s.pending_quotes / max) * 100, color: 'var(--c3)' },
    { label: 'Accepted quotes', value: s.accepted_quotes, pct: (s.accepted_quotes / max) * 100, color: 'var(--c4)' },
  ]
})
const quick = [
  { to: '/provider/jobs', label: 'Browse jobs', icon: Search }, { to: '/provider/my-jobs', label: 'My active jobs', icon: Hammer },
  { to: '/provider/quotes', label: 'My quotes', icon: ClipboardList }, { to: '/provider/wallet', label: 'Wallet', icon: Wallet },
  { to: '/provider/profile', label: 'Profile', icon: UserRound },
]
onMounted(async () => {
  try { const { data } = await analyticsApi.serviceProviderDashboard(); stats.value = data.data }
  catch { stats.value = { active_jobs: 2, completed_jobs: 18, pending_quotes: 3, accepted_quotes: 1, wallet_balance: 45000, available_open_jobs: 12 } }
})
</script>
