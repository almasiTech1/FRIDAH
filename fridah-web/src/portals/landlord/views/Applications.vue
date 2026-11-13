<template>
  <div class="space-y-5">
    <h1 class="page-title">Rental Applications</h1>

    <div class="flex gap-2">
      <button
        v-for="s in statusFilters" :key="s.value"
        class="px-3 py-1.5 rounded-full text-xs font-semibold transition-colors"
        :class="filter === s.value ? 'bg-landlord-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
        @click="filter = s.value"
      >{{ s.label }}</button>
    </div>

    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="card h-20 animate-pulse bg-gray-100" />
    </div>
    <div v-else-if="!filtered.length" class="card card-body text-center py-12 text-gray-400">No applications here.</div>
    <div v-else class="space-y-3">
      <div v-for="a in filtered" :key="a.id" class="card card-body">
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="font-semibold text-gray-900 text-sm">{{ a.tenant_name }}</p>
            <p class="text-xs text-gray-500 mt-0.5">{{ a.property_name }} &middot; Unit {{ a.unit_number }} &middot; {{ formatKES(a.rent_amount) }}/mo</p>
            <p v-if="a.preferred_move_in_date" class="text-xs text-gray-500 mt-0.5">Preferred move-in: {{ formatDate(a.preferred_move_in_date) }}</p>
            <p v-if="a.message" class="text-xs text-gray-600 mt-2 italic">"{{ a.message }}"</p>
          </div>
          <span class="badge text-xs shrink-0" :class="statusBadge(a.status)">{{ a.status }}</span>
        </div>

        <div v-if="a.status === 'pending'" class="mt-4 pt-4 border-t border-gray-50">
          <div v-if="reviewing === a.id" class="space-y-3">
            <div class="grid grid-cols-3 gap-3">
              <div><label class="label">Rent (KES)</label><input v-model.number="approveForm.rent_amount" type="number" class="input" /></div>
              <div><label class="label">Deposit (KES)</label><input v-model.number="approveForm.deposit_amount" type="number" class="input" /></div>
              <div><label class="label">Start Date</label><input v-model="approveForm.start_date" type="date" class="input" /></div>
            </div>
            <div class="flex gap-3">
              <button class="btn-outline border-gray-200" @click="reviewing = ''">Cancel</button>
              <button class="btn-primary bg-green-600 hover:bg-green-700" :disabled="submitting" @click="approve(a)">
                <span v-if="submitting" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
                <span v-else>Confirm Approval</span>
              </button>
            </div>
          </div>
          <div v-else class="flex gap-3">
            <button class="btn-outline border-gray-200 text-red-600" @click="reject(a)">Reject</button>
            <button class="btn-primary bg-landlord-600 hover:bg-landlord-700" @click="startReview(a)">Approve & Create Lease</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { rentalsApi } from '@/api/services'
import { formatKES, formatDate } from '@/utils/formatters'

const applications = ref<any[]>([])
const loading = ref(true)
const filter = ref('pending')
const reviewing = ref('')
const submitting = ref(false)
const approveForm = ref({ rent_amount: 0, deposit_amount: 0, start_date: '' })

const statusFilters = [
  { value: 'pending', label: 'Pending' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
  { value: '', label: 'All' },
]

const filtered = computed(() => filter.value ? applications.value.filter((a) => a.status === filter.value) : applications.value)

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

function startReview(a: any) {
  reviewing.value = a.id
  approveForm.value = {
    rent_amount: a.rent_amount, deposit_amount: a.rent_amount,
    start_date: new Date().toISOString().slice(0, 10),
  }
}

async function approve(a: any) {
  submitting.value = true
  try {
    await rentalsApi.approveApplication(a.id, approveForm.value)
    reviewing.value = ''
    await load()
  } finally { submitting.value = false }
}

async function reject(a: any) {
  const reason = window.prompt('Reason for rejecting this application (optional):') || ''
  await rentalsApi.rejectApplication(a.id, reason)
  await load()
}

onMounted(load)
</script>
