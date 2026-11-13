<template>
  <div class="space-y-5">
    <h1 class="page-title">My Lease</h1>

    <div v-if="renewal && renewal.status === 'pending'" class="card card-body border-2 border-tenant-200 dark:border-tenant-800 bg-tenant-50 dark:bg-tenant-950/30">
      <h2 class="section-title flex items-center gap-2">
        {{ $t('renewal.title') }}
        <span class="badge-yellow badge text-xs">{{ $t('renewal.pending') }}</span>
      </h2>
      <div class="grid grid-cols-2 gap-4 text-sm mb-4">
        <div><p class="text-gray-500 dark:text-gray-400">{{ $t('renewal.proposedRent') }}</p><p class="font-semibold text-lg">{{ formatKES(renewal.proposed_rent_amount) }}</p></div>
        <div><p class="text-gray-500 dark:text-gray-400">{{ $t('renewal.proposedTerm') }}</p><p class="font-medium">{{ formatDate(renewal.proposed_start_date) }} - {{ formatDate(renewal.proposed_end_date) }}</p></div>
      </div>
      <div v-if="showDeclineForm" class="mb-4">
        <label class="label">Reason (optional)</label>
        <textarea v-model="declineReason" class="input" rows="2" placeholder="Let your landlord know why…"/>
      </div>
      <div class="flex gap-3">
        <button v-if="!showDeclineForm" class="btn-primary bg-tenant-600 hover:bg-tenant-700" :disabled="responding" @click="respond(true)">
          {{ $t('renewal.accept') }}
        </button>
        <button v-if="!showDeclineForm" class="btn-outline" @click="showDeclineForm = true">{{ $t('renewal.decline') }}</button>
        <template v-else>
          <button class="btn-danger" :disabled="responding" @click="respond(false)">Confirm decline</button>
          <button class="btn-outline" @click="showDeclineForm = false">{{ $t('common.cancel') }}</button>
        </template>
      </div>
    </div>
    <div v-else-if="renewal && renewal.status !== 'pending'" class="card card-body text-sm text-gray-500 dark:text-gray-400">
      {{ $t('renewal.title') }}: <span class="font-medium">{{ $t(`renewal.${renewal.status}`) || renewal.status }}</span>
    </div>

    <div v-if="loading" class="card card-body animate-pulse h-40" />
    <div v-else-if="lease" class="space-y-4">
      <div class="card card-body">
        <div class="flex items-center justify-between mb-4">
          <h2 class="section-title mb-0">{{ lease.property_name }} — Unit {{ lease.unit_number }}</h2>
          <span :class="statusColor(lease.status)" class="badge">{{ lease.status }}</span>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div><p class="text-gray-500 dark:text-gray-400">Landlord</p><p class="font-medium">{{ lease.landlord }}</p></div>
          <div><p class="text-gray-500 dark:text-gray-400">Start date</p><p class="font-medium">{{ formatDate(lease.start_date) }}</p></div>
          <div><p class="text-gray-500 dark:text-gray-400">End date</p><p class="font-medium">{{ lease.end_date ? formatDate(lease.end_date) : 'Ongoing' }}</p></div>
          <div><p class="text-gray-500 dark:text-gray-400">Rent due</p><p class="font-medium">Day {{ lease.rent_due_day }} each month</p></div>
          <div><p class="text-gray-500 dark:text-gray-400">Monthly rent</p><p class="font-medium text-lg">{{ formatKES(lease.rent_amount) }}</p></div>
          <div><p class="text-gray-500 dark:text-gray-400">Deposit</p><p class="font-medium">{{ formatKES(lease.deposit_amount) }}</p></div>
          <div><p class="text-gray-500 dark:text-gray-400">Deposit paid</p><p :class="lease.deposit_paid ? 'text-green-600' : 'text-red-600'" class="font-medium">{{ lease.deposit_paid ? 'Yes' : 'No' }}</p></div>
        </div>
      </div>
    </div>
    <div v-else class="card card-body text-center py-12 text-gray-400 dark:text-gray-500">
      <p>No active lease found.</p>
      <RouterLink to="/tenant/properties" class="mt-3 btn-primary bg-tenant-600 hover:bg-tenant-700 inline-flex">Browse Properties</RouterLink>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { rentalsApi, renewalsApi } from '@/api/services'
import { formatKES, formatDate, statusColor } from '@/utils/formatters'
import type { Lease } from '@/types'

interface Renewal { id: string; status: string; proposed_rent_amount: number; proposed_start_date: string; proposed_end_date: string }

const lease = ref<Lease | null>(null)
const renewal = ref<Renewal | null>(null)
const loading = ref(true)
const responding = ref(false)
const showDeclineForm = ref(false)
const declineReason = ref('')

async function respond(accept: boolean) {
  if (!renewal.value) return
  responding.value = true
  try {
    await renewalsApi.respond(renewal.value.id, accept, declineReason.value)
    const { data } = await renewalsApi.get(renewal.value.id)
    renewal.value = data.data
    if (accept) {
      const { data: leaseData } = await rentalsApi.leases({ status: 'active' })
      lease.value = (leaseData.data?.results || leaseData.data || [])[0] || lease.value
    }
  } finally {
    responding.value = false
    showDeclineForm.value = false
  }
}

onMounted(async () => {
  try {
    const { data } = await rentalsApi.leases({ status: 'active' })
    const items = data.data?.results || data.data || []
    lease.value = items[0] || null

    const { data: renewalData } = await renewalsApi.list()
    const renewals = renewalData.data?.results || renewalData.data || []
    renewal.value = renewals[0] || null
  } catch (e) { console.error('Failed to load lease/renewal data:', e) } finally { loading.value = false }
})
</script>
