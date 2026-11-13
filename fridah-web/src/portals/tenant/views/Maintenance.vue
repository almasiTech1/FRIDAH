<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="page-title">Maintenance Requests</h1>
      <button class="btn-primary bg-tenant-600 hover:bg-tenant-700" @click="showForm = true">+ New Request</button>
    </div>

    <!-- New request form -->
    <div v-if="showForm" class="card card-body space-y-4">
      <h2 class="section-title">Submit a Request</h2>

      <div class="p-4 rounded-xl bg-brand-50 dark:bg-brand-950 border border-brand-100 dark:border-brand-900 space-y-3">
        <p class="text-sm font-semibold text-brand-700 dark:text-brand-400">✨ Snap a photo for instant AI triage (optional)</p>
        <input type="file" accept="image/*" class="input text-xs" @change="onTriagePhotoSelected" />
        <button class="btn-outline text-xs" :disabled="!triagePhoto || triaging" @click="runTriage">
          <span v-if="triaging" class="animate-spin w-3.5 h-3.5 border-2 border-brand-600 border-t-transparent rounded-full" />
          <span v-else>Analyze photo</span>
        </button>
        <div v-if="triageResult" class="p-3 rounded-lg bg-white dark:bg-gray-900 space-y-1">
          <p class="text-xs font-semibold" :class="triageResult.safety_concern ? 'text-red-600' : 'text-gray-700 dark:text-gray-300'">
            {{ triageResult.safety_concern ? '⚠️ Possible safety concern' : 'AI assessment' }}
          </p>
          <p class="text-xs text-gray-600 dark:text-gray-400">{{ triageResult.description }}</p>
          <p class="text-xs text-gray-400">Suggested: {{ triageResult.category }} · {{ triageResult.priority }} priority ({{ triageResult.confidence }} confidence)</p>
          <button class="text-xs font-semibold text-brand-600 dark:text-brand-400 hover:underline" @click="applyTriage">Use this suggestion</button>
        </div>
        <p v-if="triageError" class="text-xs text-red-600">{{ triageError }}</p>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="label">Category</label>
          <select v-model="form.category" class="input">
            <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>
        <div>
          <label class="label">Priority</label>
          <select v-model="form.priority" class="input">
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
        </div>
      </div>
      <div>
        <label class="label">Title</label>
        <input v-model="form.title" class="input" placeholder="Brief description of the issue" />
      </div>
      <div>
        <label class="label">Details</label>
        <textarea v-model="form.description" class="input resize-none" rows="3" placeholder="Describe the problem in detail..." />
      </div>
      <div class="flex gap-3">
        <button class="btn-outline border-gray-200" @click="showForm = false">Cancel</button>
        <button class="btn-primary bg-tenant-600 hover:bg-tenant-700" :disabled="submitting" @click="submit">
          <span v-if="submitting" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
          <span v-else>Submit Request</span>
        </button>
      </div>
      <p v-if="submitError" class="text-sm text-red-600">{{ submitError }}</p>
    </div>

    <!-- Requests list -->
    <div class="space-y-3">
      <div v-if="loading" class="text-center py-10 text-gray-400">Loading…</div>
      <div v-else-if="!requests.length" class="card card-body text-center text-gray-400 py-10">No maintenance requests yet.</div>
      <div v-else v-for="req in requests" :key="req.id" class="card card-body flex items-start gap-4">
        <div :class="`w-2 h-2 rounded-full mt-2 flex-shrink-0 ${priorityDot(req.priority)}`" />
        <div class="flex-1">
          <div class="flex items-start justify-between gap-2">
            <div>
              <p class="font-medium text-gray-900 text-sm">{{ req.title }}</p>
              <p class="text-xs text-gray-500 mt-0.5">{{ req.category }} · {{ formatDate(req.created_at) }}</p>
            </div>
            <span :class="statusColor(req.status)" class="badge flex-shrink-0">{{ req.status.replace('_', ' ') }}</span>
          </div>
          <p class="text-sm text-gray-600 mt-2">{{ req.description }}</p>
          <p v-if="req.provider_name" class="text-xs text-gray-400 mt-1">Assigned to: {{ req.provider_name }}</p>
          <p v-if="req.resolution_notes" class="text-xs text-gray-500 mt-1 italic">Resolution: {{ req.resolution_notes }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { rentalsApi, aiApi } from '@/api/services'
import { formatDate, statusColor } from '@/utils/formatters'
import type { MaintenanceRequest } from '@/types'

const requests = ref<MaintenanceRequest[]>([])
const loading = ref(true)
const showForm = ref(false)
const submitting = ref(false)
const submitError = ref('')
const categories = ['Plumbing', 'Electrical', 'Carpentry', 'Painting', 'Pest Control', 'Cleaning', 'Security', 'Other']
const form = ref({ category: 'Plumbing', priority: 'medium', title: '', description: '', unit: '' })

const triagePhoto = ref<File | null>(null)
const triaging = ref(false)
const triageError = ref('')
interface TriageResult {
  category: string; priority: string; description: string; confidence: string; safety_concern: boolean
  suggested_service_category?: { id: string; name: string } | null
}
const triageResult = ref<TriageResult | null>(null)

function onTriagePhotoSelected(e: Event) {
  const files = (e.target as HTMLInputElement).files
  triagePhoto.value = files?.[0] || null
  triageResult.value = null
  triageError.value = ''
}

async function runTriage() {
  if (!triagePhoto.value) return
  triaging.value = true
  triageError.value = ''
  try {
    const { data } = await aiApi.maintenanceTriage(triagePhoto.value, form.value.description)
    triageResult.value = (data as any).data
  } catch (e: any) {
    triageError.value = e?.response?.status === 503
      ? 'AI triage is not available right now — please categorize manually below.'
      : e?.response?.data?.error?.message || 'Triage failed. Please try again.'
  } finally {
    triaging.value = false
  }
}

// Maps the AI's category vocabulary (plumbing/electrical/etc) onto this form's dropdown labels.
const CATEGORY_LABELS: Record<string, string> = {
  plumbing: 'Plumbing', electrical: 'Electrical', structural: 'Carpentry', appliance: 'Other',
  pest_control: 'Pest Control', locks_security: 'Security', hvac: 'Other', other: 'Other',
}

function applyTriage() {
  if (!triageResult.value) return
  form.value.category = CATEGORY_LABELS[triageResult.value.category] || 'Other'
  form.value.priority = triageResult.value.priority
  if (!form.value.description) form.value.description = triageResult.value.description
}

const priorityDot = (p: string) => ({ low: 'bg-gray-400', medium: 'bg-blue-500', high: 'bg-yellow-500', urgent: 'bg-red-500' }[p] || 'bg-gray-400')

async function load() {
  try {
    const { data } = await rentalsApi.maintenanceList()
    requests.value = data.data?.results || data.data || []
  } catch {
    requests.value = []
  } finally { loading.value = false }
}

async function submit() {
  if (!form.value.title || !form.value.description) { submitError.value = 'Fill in all fields.'; return }
  submitting.value = true; submitError.value = ''
  try {
    await rentalsApi.createMaintenance(form.value as any)
    showForm.value = false
    form.value = { category: 'Plumbing', priority: 'medium', title: '', description: '', unit: '' }
    triagePhoto.value = null
    triageResult.value = null
    await load()
  } catch (e: any) {
    submitError.value = e?.response?.data?.error?.message || 'Failed to submit.'
  } finally { submitting.value = false }
}

onMounted(load)
</script>
