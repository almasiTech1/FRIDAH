<template>
  <div class="space-y-5">
    <h1 class="page-title">Owner Payouts</h1>

    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="card animate-pulse h-16 bg-gray-100 rounded-xl"/>
    </div>
    <div v-else-if="payouts.length" class="space-y-3">
      <div v-for="p in payouts" :key="p.id" class="card card-body flex items-center gap-4">
        <div class="w-10 h-10 rounded-xl bg-emerald-100 flex items-center justify-center text-lg flex-shrink-0">💸</div>
        <div class="flex-1">
          <div class="flex items-center gap-3 flex-wrap">
            <p class="font-semibold text-gray-900">{{ formatKES(p.amount) }}</p>
            <span :class="statusColor(p.status)" class="badge">{{ p.status }}</span>
          </div>
          <p class="text-xs text-gray-500 mt-0.5">Ref: {{ p.reference }} · {{ formatDateTime(p.created_at) }}</p>
        </div>
      </div>
    </div>
    <div v-else class="card card-body text-center py-12 text-gray-400">No payouts yet.</div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { agencyApi } from '@/api/services'
import { statusColor, formatKES, formatDateTime } from '@/utils/formatters'
import type { OwnerPayout } from '@/types'

const payouts = ref<OwnerPayout[]>([])
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    const { data } = await agencyApi.payouts()
    payouts.value = (data as any).data?.results || (data as any).data || []
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>
