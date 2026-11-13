<template>
  <div class="space-y-5">
    <h1 class="page-title">My Applications</h1>

    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="card h-20 animate-pulse bg-gray-100" />
    </div>
    <div v-else-if="!applications.length" class="card card-body text-center py-12 text-gray-400">
      No applications yet. <router-link to="/tenant/properties" class="text-tenant-600 font-semibold hover:underline">Browse properties</router-link>
    </div>
    <div v-else class="space-y-3">
      <div v-for="a in applications" :key="a.id" class="card card-body flex items-center justify-between gap-4">
        <div>
          <p class="font-semibold text-gray-900 text-sm">{{ a.property_name }} &middot; Unit {{ a.unit_number }}</p>
          <p class="text-xs text-gray-500 mt-0.5">{{ formatKES(a.rent_amount) }}/mo</p>
          <p v-if="a.status === 'rejected' && a.rejection_reason" class="text-xs text-red-500 mt-1">{{ a.rejection_reason }}</p>
          <p class="text-xs text-gray-400 mt-1">Applied {{ formatDate(a.created_at) }}</p>
        </div>
        <div class="text-right shrink-0">
          <span class="badge text-xs block mb-2" :class="statusBadge(a.status)">{{ a.status }}</span>
          <button v-if="a.status === 'pending'" class="btn-outline text-xs border-gray-200" :disabled="withdrawing === a.id" @click="withdraw(a.id)">
            Withdraw
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { rentalsApi } from '@/api/services'
import { formatKES, formatDate } from '@/utils/formatters'

const applications = ref<any[]>([])
const loading = ref(true)
const withdrawing = ref('')

function statusBadge(status: string) {
  return { pending: 'badge-yellow', approved: 'badge-green', rejected: 'badge-red', withdrawn: 'badge-gray' }[status] || 'badge-gray'
}

async function load() {
  loading.value = true
  try {
    const { data } = await rentalsApi.applications()
    applications.value = (data as any).results || (data as any).data || []
  } catch { applications.value = [] } finally { loading.value = false }
}

async function withdraw(id: string) {
  withdrawing.value = id
  try { await rentalsApi.withdrawApplication(id); await load() }
  finally { withdrawing.value = '' }
}

onMounted(load)
</script>
