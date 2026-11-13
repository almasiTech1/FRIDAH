<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between flex-wrap gap-3">
      <h1 class="page-title">Available Jobs</h1>
      <div class="flex gap-2">
        <select v-model="categoryFilter" class="input w-auto text-sm">
          <option value="">All categories</option>
          <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
      </div>
    </div>
    <div v-if="loading" class="space-y-3">
      <div v-for="i in 4" :key="i" class="card animate-pulse h-28 bg-gray-100 rounded-xl"/>
    </div>
    <div v-else-if="!jobs.length" class="card card-body text-center py-12 text-gray-400">
      <p class="text-3xl mb-3">🔍</p><p>No open jobs right now. Check back soon.</p>
    </div>
    <div v-else class="space-y-3">
      <div v-for="job in jobs" :key="job.id" class="card card-body hover:shadow-md transition-shadow">
        <div class="flex items-start justify-between gap-3">
          <div class="flex-1">
            <div class="flex items-center gap-2 flex-wrap">
              <p class="font-semibold text-gray-900">{{ job.title }}</p>
              <span class="badge badge-blue text-xs">{{ job.category_name }}</span>
            </div>
            <p class="text-xs text-gray-500 mt-1">📍 {{ job.town }}, {{ job.county }}</p>
            <p class="text-sm text-gray-600 mt-2">{{ job.description }}</p>
            <div class="flex items-center gap-4 mt-2 text-xs text-gray-400">
              <span>Posted by {{ job.posted_by_name }}</span>
              <span>{{ formatDate(job.created_at) }}</span>
              <span v-if="job.budget_estimate" class="text-provider-600 font-medium">Budget: {{ formatKES(job.budget_estimate) }}</span>
            </div>
          </div>
          <div class="flex-shrink-0">
            <button
              class="btn-primary bg-provider-600 hover:bg-provider-700 text-sm"
              @click="openQuote(job)"
            >Submit Quote</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Quote modal -->
    <Teleport to="body">
      <div v-if="quoteJob" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" @click.self="quoteJob = null">
        <div class="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
          <h2 class="text-lg font-semibold mb-1">Submit Quote</h2>
          <p class="text-sm text-gray-500 mb-5">{{ quoteJob.title }}</p>
          <div class="space-y-4">
            <div>
              <label class="label">Your Price (KES)</label>
              <input v-model.number="quoteForm.amount" class="input" type="number" min="1"/>
            </div>
            <div>
              <label class="label">Estimated Days</label>
              <input v-model.number="quoteForm.estimated_days" class="input" type="number" min="1"/>
            </div>
            <div>
              <label class="label">Message to Client</label>
              <textarea v-model="quoteForm.message" class="input resize-none" rows="3" placeholder="Introduce yourself, your experience…"/>
            </div>
          </div>
          <p v-if="quoteError" class="text-sm text-red-600 mt-3">{{ quoteError }}</p>
          <div class="flex gap-3 mt-5">
            <button class="btn-outline flex-1 border-gray-200" @click="quoteJob = null">Cancel</button>
            <button class="btn-primary flex-1 bg-provider-600 hover:bg-provider-700" :disabled="submitting" @click="submitQuote">
              <span v-if="submitting" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"/>
              <span v-else>Submit Quote</span>
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { servicesApi } from '@/api/services'
import { formatKES, formatDate } from '@/utils/formatters'
import type { ServiceJob } from '@/types'
const jobs = ref<ServiceJob[]>([])
const categories = ref<any[]>([])
const loading = ref(true)
const categoryFilter = ref('')
const quoteJob = ref<ServiceJob | null>(null)
const quoteForm = ref({ amount: 0, estimated_days: 1, message: '' })
const submitting = ref(false)
const quoteError = ref('')

function openQuote(job: ServiceJob) { quoteJob.value = job; quoteForm.value = { amount: job.budget_estimate || 0, estimated_days: 1, message: '' }; quoteError.value = '' }

async function load() {
  loading.value = true
  try {
    const [jobsRes, catsRes] = await Promise.all([
      servicesApi.jobs({ status: 'open', category: categoryFilter.value || undefined }),
      servicesApi.categories()
    ])
    jobs.value = jobsRes.data.data?.results || jobsRes.data.data || []
    categories.value = catsRes.data.data?.results || catsRes.data.data || []
  } catch {
    jobs.value = []
  } finally { loading.value = false }
}

async function submitQuote() {
  if (!quoteJob.value || !quoteForm.value.amount) { quoteError.value = 'Enter a price.'; return }
  submitting.value = true; quoteError.value = ''
  try {
    await servicesApi.submitQuote({ job: quoteJob.value.id, ...quoteForm.value })
    quoteJob.value = null
    await load()
  } catch (e: any) {
    quoteError.value = e?.response?.data?.error?.message || 'Failed to submit quote.'
  } finally { submitting.value = false }
}
onMounted(load)
</script>
