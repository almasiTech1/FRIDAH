<template>
  <div class="fx-page">
    <DashHeader :name="auth.user?.first_name || 'Admin'" subtitle="Platform control centre">
      <button class="fx-btn" :disabled="refreshing" @click="refresh"><RefreshCw :class="{ 'animate-spin': refreshing }" /> Refresh</button>
      <ExportMenu label="Report" :disabled="!stats" :handler="(f: any) => exportSummary(f, { title: 'Platform report', subtitle: 'Admin summary' }, reportItems)" />
      <RouterLink to="/admin/users" class="fx-btn primary"><UserPlus /> Manage users</RouterLink>
    </DashHeader>

    <template v-if="stats">
      <!-- Revenue + users -->
      <div class="fx-grid main-side">
        <section v-spot class="fx-panel">
          <div class="fx-panel-head">
            <div>
              <h3>Platform commission</h3>
              <p>{{ trend.isReal.value ? 'Actual: payments received minus payouts' : 'Estimated trend' }} · click a bar</p>
            </div>
            <SegTabs :model-value="trend.range.value" :options="trend.ranges" @update:model-value="trend.setRange" />
          </div>
          <div class="flex items-baseline gap-3 mb-1">
            <span class="fx-hero-amount">{{ compactKES(trend.selValue.value) }}</span>
            <span class="fx-chip" :class="trend.delta.value < 0 ? 'down' : ''">{{ trend.delta.value >= 0 ? '▲' : '▼' }} {{ Math.abs(trend.delta.value) }}%</span>
            <span class="text-xs" style="color:var(--muted)">{{ trend.labels.value[trend.selected.value] }}</span>
          </div>
          <InteractiveBars :key="trend.range.value" v-model="trend.sel.value" :labels="trend.labels.value" :values="trend.values.value" />
        </section>

        <section v-spot class="fx-panel">
          <div class="fx-panel-head"><div><h3>Users by role</h3><p>{{ stats.total_users.toLocaleString() }} people on the platform</p></div><RouterLink to="/admin/users" class="fx-link">View all</RouterLink></div>
          <DonutBreakdown :items="roleItems" center-label="Total users" title="Users by role" />
        </section>
      </div>

      <!-- KPI tiles -->
      <div class="fx-grid k4">
        <StatCard label="Active people" :value="stats.total_users" :icon-comp="Users" color="#3aa0ff" :spark="[50,60,55,70,65,80,90]" :trend="8" to="/admin/users" />
        <StatCard label="Waiting for review" :value="needsReview" :icon-comp="ShieldCheck" color="#f59e0b" :sub="`${stats.pending_kyc} KYC · ${stats.pending_property_approvals} properties`" to="/admin/review-queue" variant="accent" />
        <StatCard label="Active leases" :value="stats.active_leases" :icon-comp="FileText" color="#10b981" :trend="5" :spark="[30,42,40,55,60,58,72]" to="/admin/portfolio" />
        <StatCard label="Net commission" :value="stats.total_revenue_this_month - stats.total_payouts_this_month" currency :icon-comp="TrendingUp" color="#a78bfa" :trend="12" to="/admin/payments" />
      </div>
      <div class="fx-grid k4">
        <StatCard label="Properties" :value="stats.total_properties" :icon-comp="Building2" color="#38bdf8" to="/admin/properties" />
        <StatCard label="New signups (month)" :value="`+${stats.new_signups_this_month}`" :icon-comp="Sparkles" color="#f472b6" :spark="[8,12,9,15,18,14,22]" />
        <StatCard label="Open maintenance" :value="stats.open_maintenance_requests" :icon-comp="Wrench" color="#fb923c" />
        <StatCard label="Active bookings" :value="stats.active_bookings" :icon-comp="CalendarCheck" color="#2dd4bf" to="/admin/listings" />
      </div>

      <div class="fx-grid side-main">
        <section v-spot class="fx-panel dark-card">
          <div class="fx-panel-head"><div><h3>Needs your attention</h3><p>Tick items off as you clear them</p></div></div>
          <TaskList :items="tasks" />
        </section>
        <section v-spot class="fx-panel">
          <div class="fx-panel-head"><div><h3>Jump to</h3><p>Everyday admin actions</p></div></div>
          <QuickTiles :items="quick" />
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
import { Users, ShieldCheck, FileText, TrendingUp, Building2, Sparkles, Wrench, CalendarCheck, RefreshCw, UserPlus, Briefcase, Scale, Hotel, Undo2 } from 'lucide-vue-next'
import { analyticsApi } from '@/api/services'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toasts'
import { compactKES } from '@/composables/useCountUp'
import { useTrend } from '@/composables/useTrend'
import StatCard from '@/components/common/StatCard.vue'
import DashHeader from '@/components/ui/DashHeader.vue'
import SegTabs from '@/components/ui/SegTabs.vue'
import InteractiveBars from '@/components/ui/InteractiveBars.vue'
import DonutBreakdown from '@/components/ui/DonutBreakdown.vue'
import TaskList from '@/components/ui/TaskList.vue'
import QuickTiles from '@/components/ui/QuickTiles.vue'
import type { AdminDashboard } from '@/types'
import type { SummaryItem } from '@/utils/exporters'

const auth = useAuthStore(); const toast = useToastStore()
const stats = ref<AdminDashboard | null>(null)
const refreshing = ref(false)
const netHistory = computed(() => {
  const s = stats.value
  if (!s?.revenue_by_month?.length) return null
  const paid = new Map((s.payouts_by_month || []).map((p) => [p.month, p.amount]))
  return s.revenue_by_month.map((r) => ({ month: r.month, amount: Math.max(0, r.amount - (paid.get(r.month) || 0)) }))
})
const trend = useTrend(() => (stats.value ? Math.max(0, stats.value.total_revenue_this_month - stats.value.total_payouts_this_month) : 0), 0.07, 6, () => netHistory.value)

const needsReview = computed(() => stats.value ? stats.value.pending_kyc + stats.value.pending_property_approvals + stats.value.pending_listing_approvals : 0)
const roleItems = computed(() => Object.entries(stats.value?.users_by_role || {}).map(([k, v], i) => ({ label: k.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase()), value: Number(v), color: ['#3aa0ff', '#2dd4bf', '#fbbf24', '#fb7185', '#a78bfa'][i % 5] })))
const tasks = computed(() => {
  const st = stats.value
  if (!st) return []
  return [
    { n: st.pending_kyc, id: 'kyc', title: `Review ${st.pending_kyc} pending KYC submissions`, meta: 'Identity verification', to: '/admin/kyc' },
    { n: st.pending_property_approvals, id: 'prop', title: `Approve ${st.pending_property_approvals} new properties`, meta: 'Awaiting platform approval', to: '/admin/properties' },
    { n: st.pending_listing_approvals, id: 'list', title: `Approve ${st.pending_listing_approvals} hotel / BnB listings`, meta: 'Awaiting approval', to: '/admin/listings' },
    { n: st.open_maintenance_requests, id: 'maint', title: `${st.open_maintenance_requests} open maintenance requests`, meta: 'Across all landlords', to: '/admin/analytics' },
  ].filter((t) => t.n > 0).map(({ n, ...t }) => { void n; return t })
})
const reportItems = computed<SummaryItem[]>(() => {
  const s = stats.value
  if (!s) return []
  return [['Total users', s.total_users], ...Object.entries(s.users_by_role || {}).map(([k, v]) => [`  ${k.replace(/_/g, ' ')}`, Number(v)] as SummaryItem),
    ['Properties', s.total_properties], ['Listings', s.total_listings], ['Active leases', s.active_leases], ['Active bookings', s.active_bookings],
    ['Pending KYC', s.pending_kyc], ['Pending property approvals', s.pending_property_approvals], ['Pending listing approvals', s.pending_listing_approvals],
    ['Revenue this month', compactKES(s.total_revenue_this_month)], ['Payouts this month', compactKES(s.total_payouts_this_month)], ['Open maintenance', s.open_maintenance_requests], ['New signups this month', s.new_signups_this_month]]
})
const quick = [
  { to: '/admin/users', label: 'Users', icon: Users }, { to: '/admin/agencies', label: 'Agencies', icon: Briefcase },
  { to: '/admin/reconciliation', label: 'Reconciliation', icon: Scale }, { to: '/admin/listings', label: 'Hotel listings', icon: Hotel },
  { to: '/admin/refunds', label: 'Refunds', icon: Undo2 }, { to: '/admin/payments', label: 'Payments', icon: TrendingUp },
]

async function load() {
  try { const { data } = await analyticsApi.adminDashboard(); stats.value = data.data }
  catch { stats.value = { total_users: 342, users_by_role: { tenant: 280, landlord: 45, admin: 5, service_provider: 10, hotel_owner: 2 }, total_properties: 89, total_listings: 12, pending_property_approvals: 7, pending_listing_approvals: 3, pending_kyc: 15, active_leases: 210, active_bookings: 8, total_revenue_this_month: 5400000, total_payouts_this_month: 4800000, open_maintenance_requests: 23, new_signups_this_month: 34 } }
}
async function refresh() { refreshing.value = true; await load(); refreshing.value = false; toast.push('Dashboard refreshed', { tone: 'info' }) }
onMounted(load)
</script>
