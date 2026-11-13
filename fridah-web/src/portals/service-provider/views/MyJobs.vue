<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="page-title">My Jobs</h1>
      <select v-model="statusFilter" class="input w-auto text-sm">
        <option value="">All</option>
        <option value="assigned">Assigned</option>
        <option value="in_progress">In Progress</option>
        <option value="completed">Completed</option>
      </select>
    </div>
    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="card animate-pulse h-24 bg-gray-100 rounded-xl"/>
    </div>
    <div v-else-if="!filtered.length" class="card card-body text-center py-12 text-gray-400">
      <p class="text-3xl mb-3">🔧</p><p>No jobs assigned to you yet.</p>
    </div>
    <div v-else class="space-y-3">
      <div v-for="job in filtered" :key="job.id" class="card card-body">
        <div class="flex items-start justify-between gap-3">
          <div class="flex-1">
            <div class="flex items-center gap-2 flex-wrap mb-1">
              <p class="font-semibold text-gray-900">{{ job.title }}</p>
              <span :class="jobStatusBadge(job.status)" class="badge">{{ job.status.replace('_',' ') }}</span>
            </div>
            <p class="text-xs text-gray-500">📍 {{ job.town }}, {{ job.county }} · {{ job.category_name }}</p>
            <p class="text-sm text-gray-600 mt-2">{{ job.description }}</p>
            <p v-if="job.scheduled_date" class="text-xs text-gray-400 mt-1">Scheduled: {{ formatDate(job.scheduled_date) }}</p>
          </div>
          <div class="flex flex-col gap-2 flex-shrink-0">
            <button
              v-if="job.status === 'assigned'"
              class="btn-primary bg-provider-600 hover:bg-provider-700 text-xs"
              @click="action(job.id, 'start')"
            >Start Job</button>
            <button
              v-if="job.status === 'in_progress'"
              class="btn-primary bg-green-600 hover:bg-green-700 text-xs"
              @click="action(job.id, 'complete')"
            >Mark Complete</button>
          </div>
        </div>
      </div>
    </div>
    <p v-if="actionError" class="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg p-3">{{ actionError }}</p>
  </div>
</template>
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { servicesApi } from '@/api/services'
import { formatDate } from '@/utils/formatters'
import type { ServiceJob } from '@/types'
const jobs = ref<ServiceJob[]>([])
const loading = ref(true)
const statusFilter = ref('')
const actionError = ref('')
const filtered = computed(() => statusFilter.value ? jobs.value.filter(j => j.status === statusFilter.value) : jobs.value)
const jobStatusBadge = (s: string) => ({ assigned:'badge-blue', in_progress:'badge-yellow', completed:'badge-green', cancelled:'badge-red' }[s] || 'badge-gray')
async function load() {
  try {
    const { data } = await servicesApi.jobs({ status: statusFilter.value || undefined })
    jobs.value = (data.data?.results || data.data || []).filter((j: ServiceJob) => j.assigned_provider)
  } catch (e: any) { jobs.value = []; actionError.value = e?.response?.data?.error?.message || 'Failed to load jobs.' }
  finally { loading.value = false }
}
async function action(id: string, type: 'start' | 'complete') {
  actionError.value = ''
  try {
    if (type === 'start') await servicesApi.startJob(id)
    else await servicesApi.completeJob(id)
    await load()
  } catch (e: any) {
    actionError.value = e?.response?.data?.error?.message || `Failed to ${type === 'start' ? 'start' : 'complete'} the job.`
  }
}
onMounted(load)
</script>
