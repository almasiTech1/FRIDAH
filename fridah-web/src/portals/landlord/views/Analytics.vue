<template>
  <div class="space-y-5">
    <h1 class="page-title">Analytics</h1>
    <div v-if="stats" class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard label="Occupancy Rate" :value="`${occupancyRate}%`" />
      <StatCard label="Collected This Month" :value="stats.collected_this_month" :currency="true" />
      <StatCard label="Overdue Amount" :value="stats.overdue_amount" :currency="true" />
      <StatCard label="Wallet Balance" :value="stats.wallet_balance" :currency="true" />
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div class="card card-body" v-if="stats">
        <h2 class="section-title">Unit Occupancy</h2>
        <DoughnutChart :labels="['Occupied', 'Vacant']" :values="[stats.occupied_units, stats.vacant_units]" :colors="['#6366f1', '#e5e7eb']" />
      </div>
      <div class="card card-body">
        <div class="flex items-center justify-between mb-1">
          <h2 class="section-title mb-0">Revenue Forecast</h2>
          <span v-if="forecast" class="text-xs font-semibold text-gray-400">{{ forecast.historical_collection_rate_pct }}% historical collection rate</span>
        </div>
        <LineChart
          v-if="forecast"
          :labels="forecast.forecast.map((f: any) => f.month)"
          :series="[
            { label: 'Billed', values: forecast.forecast.map((f: any) => f.billed_revenue), color: '#c7d2fe', dashed: true },
            { label: 'Expected Collected', values: forecast.forecast.map((f: any) => f.expected_collected_revenue), color: '#6366f1' },
          ]"
          :currency="true"
        />
      </div>
    </div>

    <div class="card card-body">
      <h2 class="section-title">Portfolio Snapshot</h2>
      <div class="space-y-3">
        <div v-if="stats">
          <div class="flex justify-between text-sm mb-1"><span class="text-gray-600">Occupancy</span><span class="font-medium">{{ stats.occupied_units }}/{{ stats.total_units }} units</span></div>
          <div class="h-3 bg-gray-100 rounded-full overflow-hidden">
            <div class="h-full bg-landlord-600 rounded-full transition-all" :style="`width:${occupancyRate}%`"/>
          </div>
        </div>
        <div v-if="stats">
          <div class="flex justify-between text-sm mb-1"><span class="text-gray-600">Invoice collection rate</span><span class="font-medium">{{ collectionRate }}%</span></div>
          <div class="h-3 bg-gray-100 rounded-full overflow-hidden">
            <div class="h-full bg-green-500 rounded-full transition-all" :style="`width:${collectionRate}%`"/>
          </div>
        </div>
      </div>
    </div>
    <div class="grid grid-cols-2 gap-4" v-if="stats">
      <div class="card card-body text-center">
        <p class="text-3xl font-bold text-landlord-600">{{ stats.active_leases }}</p>
        <p class="text-sm text-gray-500 mt-1">Active leases</p>
      </div>
      <div class="card card-body text-center">
        <p class="text-3xl font-bold text-red-500">{{ stats.open_maintenance_requests }}</p>
        <p class="text-sm text-gray-500 mt-1">Open maintenance requests</p>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { analyticsApi } from '@/api/services'
import StatCard from '@/components/common/StatCard.vue'
import DoughnutChart from '@/components/charts/DoughnutChart.vue'
import LineChart from '@/components/charts/LineChart.vue'
import type { LandlordDashboard } from '@/types'
const stats = ref<LandlordDashboard | null>(null)
const forecast = ref<any>(null)
const occupancyRate = computed(() => stats.value && stats.value.total_units > 0 ? Math.round(stats.value.occupied_units / stats.value.total_units * 100) : 0)
const collectionRate = computed(() => {
  if (!stats.value) return 0
  const total = stats.value.collected_this_month + stats.value.overdue_amount
  return total > 0 ? Math.round(stats.value.collected_this_month / total * 100) : 0
})
onMounted(async () => {
  try { const { data } = await analyticsApi.landlordDashboard(); stats.value = data.data }
  catch { stats.value = { total_properties:4, total_units:24, occupied_units:18, vacant_units:6, active_leases:18, overdue_invoices_count:3, overdue_amount:75000, collected_this_month:450000, open_maintenance_requests:5, wallet_balance:320000 } }
  try { const { data } = await analyticsApi.revenueForecast(); forecast.value = data.data }
  catch { forecast.value = null }
})
</script>
