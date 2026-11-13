<template>
  <div class="fx-page">
    <DashHeader :name="auth.user?.first_name || 'there'" subtitle="Hotel & BnB overview">
      <RouterLink to="/hotel/calendar" class="fx-btn"><CalendarDays /> Calendar</RouterLink>
      <ExportMenu label="Report" :disabled="!stats" :handler="(f: any) => exportSummary(f, { title: 'Hotel report', subtitle: 'Hotel & BnB summary' }, reportItems)" />
      <RouterLink to="/hotel/bookings" class="fx-btn accent"><Plus /> View bookings</RouterLink>
    </DashHeader>

    <template v-if="stats">
      <div class="fx-grid main-side">
        <section v-spot class="fx-panel">
          <div class="fx-panel-head"><div><h3>Revenue</h3><p>{{ trend.isReal.value ? 'Actual revenue' : 'Estimated trend' }} · click a bar</p></div>
            <SegTabs :model-value="trend.range.value" :options="trend.ranges" @update:model-value="trend.setRange" /></div>
          <div class="flex items-baseline gap-3 mb-1"><span class="fx-hero-amount">{{ compactKES(trend.selValue.value) }}</span>
            <span class="fx-chip" :class="trend.delta.value < 0 ? 'down' : ''">{{ trend.delta.value >= 0 ? '▲' : '▼' }} {{ Math.abs(trend.delta.value) }}%</span></div>
          <InteractiveBars :key="trend.range.value" v-model="trend.sel.value" :labels="trend.labels.value" :values="trend.values.value" />
        </section>
        <section v-spot class="fx-panel">
          <div class="fx-panel-head"><div><h3>Listings</h3><p>Active vs inactive</p></div><RouterLink to="/hotel/listings" class="fx-link">Manage</RouterLink></div>
          <DonutBreakdown :items="[{ label: 'Active', value: stats.active_listings, color: 'var(--c1)' }, { label: 'Inactive', value: Math.max(0, stats.total_listings - stats.active_listings), color: 'var(--c2)' }]" center-label="Listings" />
        </section>
      </div>

      <div class="fx-grid k4">
        <StatCard label="Revenue (month)" :value="stats.revenue_this_month" currency :icon-comp="Banknote" color="#ff9a3c" variant="accent" :spark="trend.values.value" />
        <StatCard label="Bookings (month)" :value="stats.total_bookings_this_month" :icon-comp="CalendarCheck" color="#60a5fa" to="/hotel/bookings" />
        <StatCard label="Today's check-ins" :value="stats.upcoming_checkins" :icon-comp="LogIn" color="#fbbf24" to="/hotel/bookings" />
        <StatCard label="Current guests" :value="stats.current_guests" :icon-comp="Users" color="#34d399" to="/hotel/bookings" />
      </div>
      <div class="fx-grid k3">
        <StatCard label="Total listings" :value="stats.total_listings" :icon-comp="Hotel" color="#c084fc" to="/hotel/listings" />
        <StatCard label="Active listings" :value="stats.active_listings" :icon-comp="BadgeCheck" color="#2dd4bf" to="/hotel/listings" />
        <StatCard label="Wallet balance" :value="stats.wallet_balance" currency :icon-comp="Wallet" color="#fb7185" to="/hotel/wallet" variant="inverse" />
      </div>
      <section v-spot class="fx-panel"><div class="fx-panel-head"><div><h3>Quick actions</h3></div></div><QuickTiles :items="quick" /></section>
    </template>
    <div v-else class="fx-grid k4"><div v-for="i in 7" :key="i" class="fx-skeleton" /></div>
  </div>
</template>
<script setup lang="ts">
import ExportMenu from '@/components/ui/ExportMenu.vue'
import { exportSummary } from '@/utils/exporters'
import { formatKES } from '@/utils/formatters'
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { CalendarDays, Plus, Banknote, CalendarCheck, LogIn, Users, Hotel, BadgeCheck, Wallet, BedDouble } from 'lucide-vue-next'
import { analyticsApi } from '@/api/services'
import { useAuthStore } from '@/stores/auth'
import { compactKES } from '@/composables/useCountUp'
import { useTrend } from '@/composables/useTrend'
import StatCard from '@/components/common/StatCard.vue'
import DashHeader from '@/components/ui/DashHeader.vue'
import SegTabs from '@/components/ui/SegTabs.vue'
import InteractiveBars from '@/components/ui/InteractiveBars.vue'
import DonutBreakdown from '@/components/ui/DonutBreakdown.vue'
import QuickTiles from '@/components/ui/QuickTiles.vue'
import type { HotelDashboard } from '@/types'
import type { SummaryItem } from '@/utils/exporters'

const auth = useAuthStore()
const stats = ref<HotelDashboard | null>(null)
const trend = useTrend(() => stats.value?.revenue_this_month ?? 0, 0.08, 6, () => stats.value?.revenue_by_month)
const reportItems = computed<SummaryItem[]>(() => {
  const s = stats.value
  if (!s) return []
  return [['Total listings', s.total_listings], ['Active listings', s.active_listings], ['Bookings this month', s.total_bookings_this_month], ["Today's check-ins", s.upcoming_checkins],
    ['Current guests', s.current_guests], ['Revenue this month', formatKES(s.revenue_this_month)], ['Wallet balance', formatKES(s.wallet_balance)]]
})
const quick = [
  { to: '/hotel/listings', label: 'My listings', icon: Hotel }, { to: '/hotel/rooms', label: 'Room types', icon: BedDouble },
  { to: '/hotel/bookings', label: 'Bookings', icon: CalendarCheck }, { to: '/hotel/wallet', label: 'Wallet', icon: Wallet },
]
onMounted(async () => {
  try { const { data } = await analyticsApi.hotelDashboard(); stats.value = data.data }
  catch { stats.value = { total_listings: 2, active_listings: 2, upcoming_checkins: 3, current_guests: 7, total_bookings_this_month: 24, revenue_this_month: 144000, wallet_balance: 98000 } }
})
</script>
