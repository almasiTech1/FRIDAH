<template>
  <div class="space-y-5 max-w-2xl">
    <div class="page-header"><h1 class="page-title">✨ AI Rent Estimator</h1></div>
    <p class="text-sm text-gray-500 dark:text-gray-400 -mt-3">
      Get a recommended rent based on real comparable units already listed on FRIDAH in your area — not a generic guess.
    </p>

    <div class="card card-body space-y-4">
      <div class="grid grid-cols-2 gap-4">
        <div><label class="label">County</label><input v-model="form.county" class="input" placeholder="Nairobi" /></div>
        <div><label class="label">Town</label><input v-model="form.town" class="input" placeholder="Westlands" /></div>
        <div><label class="label">Bedrooms</label>
          <select v-model.number="form.bedrooms" class="input">
            <option v-for="n in [0,1,2,3,4,5]" :key="n" :value="n">{{ n === 0 ? 'Bedsitter/Studio' : `${n} bedroom${n > 1 ? 's' : ''}` }}</option>
          </select>
        </div>
        <div><label class="label">Size (sqm, optional)</label><input v-model.number="form.size_sqm" type="number" class="input" /></div>
      </div>
      <div>
        <label class="label">Amenities (comma-separated)</label>
        <input v-model="amenitiesInput" class="input" placeholder="parking, borehole water, gym, backup generator" />
      </div>
      <button class="btn-primary bg-landlord-600 hover:bg-landlord-700" :disabled="loading || !form.county" @click="runEstimate">
        <span v-if="loading" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
        <span v-else>Get Estimate</span>
      </button>
      <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
    </div>

    <div v-if="result" class="card card-body space-y-5">
      <div v-if="result.recommended_rent" class="text-center py-4">
        <p class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide font-semibold">Recommended Rent</p>
        <p class="text-4xl font-black text-landlord-600 dark:text-landlord-400 mt-1">{{ formatKES(result.recommended_rent) }}</p>
        <p class="text-sm text-gray-400 mt-1">Range: {{ formatKES(result.rent_range_low ?? 0) }} – {{ formatKES(result.rent_range_high ?? 0) }}</p>
      </div>
      <div v-else class="text-center py-6 text-gray-400">
        Not enough comparable data yet to ground a confident estimate.
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div class="p-4 rounded-xl bg-gray-50 dark:bg-gray-800/50">
          <p class="text-xs text-gray-500 dark:text-gray-400">Occupancy likelihood</p>
          <p class="font-bold capitalize" :class="occupancyColor">{{ result.occupancy_likelihood }}</p>
        </div>
        <div class="p-4 rounded-xl bg-gray-50 dark:bg-gray-800/50">
          <p class="text-xs text-gray-500 dark:text-gray-400">Confidence</p>
          <p class="font-bold capitalize">{{ result.confidence }} <span class="text-xs font-normal text-gray-400">({{ result.comparable_stats?.comparable_count || 0 }} comparables)</span></p>
        </div>
      </div>

      <div class="p-4 rounded-xl bg-brand-50 dark:bg-brand-950">
        <p class="text-xs font-semibold text-brand-700 dark:text-brand-400 mb-1">✨ AI reasoning</p>
        <p class="text-sm text-gray-700 dark:text-gray-300">{{ result.demand_notes }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { aiApi } from '@/api/services'
import { formatKES } from '@/utils/formatters'

interface EstimateResult {
  recommended_rent: number | null
  rent_range_low: number | null
  rent_range_high: number | null
  occupancy_likelihood: string
  demand_notes: string
  confidence: string
  comparable_stats?: { comparable_count: number; median_rent: number | null; min_rent: number | null; max_rent: number | null }
}

const form = ref({ county: '', town: '', bedrooms: 2, size_sqm: undefined as number | undefined })
const amenitiesInput = ref('')
const loading = ref(false)
const error = ref('')
const result = ref<EstimateResult | null>(null)

const occupancyColor = computed(() => {
  const map: Record<string, string> = { high: 'text-emerald-600 dark:text-emerald-400', moderate: 'text-amber-600 dark:text-amber-400', low: 'text-red-600 dark:text-red-400' }
  return map[result.value?.occupancy_likelihood || ''] || 'text-gray-600'
})

async function runEstimate() {
  loading.value = true
  error.value = ''
  result.value = null
  try {
    const amenities = amenitiesInput.value.split(',').map((a) => a.trim()).filter(Boolean)
    const { data } = await aiApi.rentEstimate({ ...form.value, amenities })
    result.value = (data as any).data
  } catch (e: any) {
    error.value = e?.response?.status === 503
      ? 'AI rent estimation is not available right now.'
      : e?.response?.data?.error?.message || 'Estimation failed. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>
