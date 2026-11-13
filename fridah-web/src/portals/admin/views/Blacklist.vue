<template>
  <div class="space-y-5">
    <div class="page-header">
      <h1 class="page-title">{{ $t('nav.blacklist') }}</h1>
      <select v-model="statusFilter" class="input w-48" @change="load">
        <option value="">All</option>
        <option value="active">{{ $t('blacklist.active') }}</option>
        <option value="disputed">{{ $t('blacklist.disputed') }}</option>
        <option value="removed">{{ $t('blacklist.removed') }}</option>
      </select>
    </div>

    <div class="space-y-3">
      <div v-if="loading" class="card card-body animate-pulse h-24" />
      <div v-for="f in entries" :key="f.id" class="card card-body">
        <div class="flex items-center justify-between mb-2">
          <div>
            <p class="font-semibold">{{ f.tenant_name }} <span class="text-gray-400 dark:text-gray-500 font-normal text-sm">({{ f.tenant_phone }})</span></p>
            <p class="text-xs text-gray-400 dark:text-gray-500">Flagged by {{ f.flagged_by_name }} on {{ formatDate(f.created_at) }}</p>
          </div>
          <span :class="statusColor(f.status)" class="badge">{{ f.status }}</span>
        </div>
        <p class="badge-red badge mb-2 inline-block">{{ f.reason.replace('_', ' ') }}</p>
        <p class="text-sm text-gray-700 dark:text-gray-300">{{ f.details }}</p>
        <p v-if="f.amount_owed" class="text-sm font-medium mt-1">Amount owed: {{ formatKES(f.amount_owed) }}</p>

        <div v-if="f.tenant_response" class="mt-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
          <p class="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">Tenant's response:</p>
          <p class="text-sm">{{ f.tenant_response }}</p>
        </div>

        <div v-if="f.status === 'disputed'" class="flex gap-2 mt-4">
          <button class="btn-primary bg-emerald-600 hover:bg-emerald-700 text-xs py-1.5 px-3" @click="review(f.id, 'active')">Keep flag active</button>
          <button class="btn-outline text-xs py-1.5 px-3" @click="review(f.id, 'removed')">Remove flag</button>
        </div>
      </div>
      <div v-if="!loading && !entries.length" class="card card-body text-center py-10 text-gray-400 dark:text-gray-500">No blacklist entries found.</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { blacklistApi } from '@/api/services'
import { formatKES, formatDate, statusColor } from '@/utils/formatters'

const entries = ref<any[]>([])
const loading = ref(true)
const statusFilter = ref('')

async function load() {
  loading.value = true
  try {
    const { data } = await blacklistApi.list(statusFilter.value ? { status: statusFilter.value } : {})
    entries.value = data.data?.results || data.data || []
  } catch { entries.value = [] } finally { loading.value = false }
}

async function review(id: string, status: 'active' | 'removed') {
  await blacklistApi.review(id, status)
  await load()
}

onMounted(load)
</script>
