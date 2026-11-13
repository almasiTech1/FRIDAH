<template>
  <div class="space-y-5">
    <h1 class="page-title">Agency Audit Log</h1>
    <p class="text-xs text-gray-400 -mt-3">Every staffing, assignment, statement, and payout action taken in this agency, for accountability.</p>

    <div v-if="loading" class="space-y-2">
      <div v-for="i in 6" :key="i" class="card animate-pulse h-12 bg-gray-100 rounded-xl"/>
    </div>
    <div v-else-if="logs.length" class="card divide-y divide-gray-100">
      <div v-for="l in logs" :key="l.id" class="px-4 py-3 flex items-center gap-3 text-sm">
        <span class="w-2 h-2 rounded-full bg-agency-400 flex-shrink-0"/>
        <span class="font-semibold text-gray-700">{{ l.action.replace(/\./g, ' → ') }}</span>
        <span class="text-gray-400">by {{ l.actor_name || 'System' }}</span>
        <span class="ml-auto text-xs text-gray-400">{{ formatDateTime(l.created_at) }}</span>
      </div>
    </div>
    <div v-else class="card card-body text-center py-12 text-gray-400">No audit entries yet.</div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { agencyApi } from '@/api/services'
import { formatDateTime } from '@/utils/formatters'
import { useAuthStore } from '@/stores/auth'
import type { AgencyAuditLog } from '@/types'

const auth = useAuthStore()
const logs = ref<AgencyAuditLog[]>([])
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    if (!auth.agencies.length) await auth.fetchAgencies()
    const id = auth.agencies[0]?.id
    if (!id) { logs.value = []; return }
    const { data } = await agencyApi.auditLogs(id)
    logs.value = (data as any).data?.results || (data as any).data || []
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>
