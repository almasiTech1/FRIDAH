<template>
  <div class="space-y-5">
    <h1 class="page-title">My Quotes</h1>
    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="card animate-pulse h-20 bg-gray-100 rounded-xl"/>
    </div>
    <div v-else-if="!quotes.length" class="card card-body text-center py-12 text-gray-400">
      <p class="text-3xl mb-3">📝</p><p>No quotes submitted yet. Browse open jobs to get started.</p>
    </div>
    <div v-else class="space-y-3">
      <div v-for="q in quotes" :key="q.id" class="card card-body">
        <div class="flex items-start justify-between gap-3 flex-wrap">
          <div>
            <p class="font-semibold text-gray-900 text-sm">Quote for Job</p>
            <p class="text-xs text-gray-500 mt-0.5">Submitted {{ formatDate(q.created_at) }}</p>
          </div>
          <span :class="quoteBadge(q.status)" class="badge">{{ q.status }}</span>
        </div>
        <div class="grid grid-cols-2 gap-3 mt-3 text-sm">
          <div><p class="text-gray-500 text-xs">Your Price</p><p class="font-semibold text-provider-600">{{ formatKES(q.amount) }}</p></div>
          <div><p class="text-gray-500 text-xs">Est. Days</p><p class="font-medium">{{ q.estimated_days }} day(s)</p></div>
        </div>
        <p v-if="q.message" class="text-sm text-gray-600 mt-2 italic">"{{ q.message }}"</p>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { servicesApi } from '@/api/services'
import { formatKES, formatDate } from '@/utils/formatters'
import type { Quote } from '@/types'
const quotes = ref<Quote[]>([])
const loading = ref(true)
const quoteBadge = (s: string) => ({ pending:'badge-yellow', accepted:'badge-green', rejected:'badge-red', withdrawn:'badge-gray' }[s] || 'badge-gray')
onMounted(async () => {
  try {
    const { data } = await servicesApi.jobs()
    const allJobs = data.data?.results || data.data || []
    quotes.value = allJobs.flatMap((j: any) => j.quotes || [])
  } catch { quotes.value = [] } finally { loading.value = false }
})
</script>
