<template>
  <div class="space-y-5">
    <h1 class="page-title">Platform Analytics</h1>
    <div v-if="stats" class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard label="Total Users" :value="stats.total_users" />
      <StatCard label="Revenue (Month)" :value="stats.total_revenue_this_month" :currency="true" />
      <StatCard label="Payouts (Month)" :value="stats.total_payouts_this_month" :currency="true" />
      <StatCard label="Net Commission" :value="stats.total_revenue_this_month - stats.total_payouts_this_month" :currency="true" />
    </div>
    <div v-if="stats" class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="card card-body">
        <h2 class="section-title">Users by Role</h2>
        <DoughnutChart :labels="Object.keys(stats.users_by_role).map(r => r.replace('_',' '))" :values="Object.values(stats.users_by_role)" />
      </div>
      <div class="card card-body">
        <h2 class="section-title">Revenue vs Payouts</h2>
        <BarChart
          :labels="['This Month']"
          :series="[
            { label: 'Revenue', values: [stats.total_revenue_this_month], color: '#10b981' },
            { label: 'Payouts', values: [stats.total_payouts_this_month], color: '#f59e0b' },
          ]"
          :currency="true"
        />
      </div>
    </div>
    <div v-if="stats" class="card card-body">
      <h2 class="section-title">Platform Health</h2>
      <div class="space-y-3 text-sm">
        <div class="flex justify-between py-2 border-b border-gray-50"><span class="text-gray-500">Active leases</span><span class="font-medium">{{ stats.active_leases }}</span></div>
        <div class="flex justify-between py-2 border-b border-gray-50"><span class="text-gray-500">Active bookings</span><span class="font-medium">{{ stats.active_bookings }}</span></div>
        <div class="flex justify-between py-2 border-b border-gray-50"><span class="text-gray-500">Open maintenance</span><span class="font-medium text-yellow-600">{{ stats.open_maintenance_requests }}</span></div>
        <div class="flex justify-between py-2"><span class="text-gray-500">New signups (month)</span><span class="font-medium text-green-600">+{{ stats.new_signups_this_month }}</span></div>
      </div>
    </div>

    <div v-if="aiUsage" class="card card-body">
      <div class="flex items-center justify-between mb-1">
        <h2 class="section-title mb-0">AI Feature Usage (30 days)</h2>
        <span class="text-xs font-semibold text-gray-400">{{ aiUsage.summary.success_rate }}% success rate</span>
      </div>
      <BarChart
        :labels="aiUsage.by_feature.map((f: any) => f.feature.replace('_',' '))"
        :series="[{ label: 'Calls', values: aiUsage.by_feature.map((f: any) => f.calls), color: '#8b5cf6' }]"
        :horizontal="true"
      />
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { analyticsApi } from '@/api/services'
import StatCard from '@/components/common/StatCard.vue'
import DoughnutChart from '@/components/charts/DoughnutChart.vue'
import BarChart from '@/components/charts/BarChart.vue'
import type { AdminDashboard } from '@/types'
const stats = ref<AdminDashboard | null>(null)
const aiUsage = ref<any>(null)
onMounted(async () => {
  try { const { data } = await analyticsApi.adminDashboard(); stats.value = data.data }
  catch { stats.value = null }
  try { const { data } = await analyticsApi.aiUsageDashboard(); aiUsage.value = data.data }
  catch { aiUsage.value = null }
})
</script>
