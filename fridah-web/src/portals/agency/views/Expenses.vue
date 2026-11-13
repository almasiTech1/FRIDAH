<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="page-title">Property Expenses</h1>
      <button class="btn-primary bg-agency-600 hover:bg-agency-700" @click="showForm = !showForm">+ Record Expense</button>
    </div>

    <div v-if="showForm" class="card card-body space-y-4">
      <h2 class="section-title">New Expense</h2>
      <div class="grid grid-cols-2 gap-4">
        <div><label class="label">Property ID</label><input v-model="form.property" class="input" placeholder="UUID of the property"/></div>
        <div><label class="label">Category</label>
          <select v-model="form.category" class="input">
            <option value="maintenance">Maintenance</option>
            <option value="utilities">Utilities</option>
            <option value="compliance">Compliance / Certification</option>
            <option value="security">Security</option>
            <option value="cleaning">Cleaning</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div><label class="label">Amount (KES)</label><input v-model.number="form.amount" type="number" class="input"/></div>
        <div><label class="label">Date Incurred</label><input v-model="form.incurred_on" type="date" class="input"/></div>
      </div>
      <div><label class="label">Description</label><input v-model="form.description" class="input" placeholder="Plumber callout for unit A2"/></div>
      <label class="flex items-center gap-2 text-sm text-gray-600">
        <input v-model="form.is_deductible_from_owner" type="checkbox" class="rounded"/> Deduct from owner's next statement
      </label>
      <div class="flex gap-3">
        <button class="btn-outline border-gray-200" @click="showForm = false">Cancel</button>
        <button class="btn-primary bg-agency-600 hover:bg-agency-700" :disabled="saving" @click="save">
          <span v-if="saving" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"/>
          <span v-else>Save Expense</span>
        </button>
      </div>
      <p v-if="saveError" class="text-sm text-red-600">{{ saveError }}</p>
    </div>

    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="card animate-pulse h-16 bg-gray-100 rounded-xl"/>
    </div>
    <div v-else-if="expenses.length" class="space-y-3">
      <div v-for="e in expenses" :key="e.id" class="card card-body flex items-center gap-4">
        <div class="flex-1">
          <div class="flex items-center gap-3 flex-wrap">
            <p class="font-semibold text-gray-900">{{ e.description }}</p>
            <span class="badge badge-gray">{{ e.category }}</span>
          </div>
          <p class="text-xs text-gray-500 mt-0.5">{{ e.property_name }} · {{ formatDate(e.incurred_on) }}{{ e.is_deductible_from_owner ? ' · Deductible' : '' }}</p>
        </div>
        <p class="font-bold text-orange-500">{{ formatKES(e.amount) }}</p>
      </div>
    </div>
    <div v-else class="card card-body text-center py-12 text-gray-400">No expenses recorded yet.</div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { agencyApi } from '@/api/services'
import { formatDate, formatKES } from '@/utils/formatters'
import { useAuthStore } from '@/stores/auth'
import type { AgencyExpense } from '@/types'

const auth = useAuthStore()
const expenses = ref<AgencyExpense[]>([])
const loading = ref(true)
const showForm = ref(false)
const saving = ref(false)
const saveError = ref('')
const form = ref({
  property: '', category: 'maintenance', amount: 0,
  incurred_on: new Date().toISOString().slice(0, 10), description: '', is_deductible_from_owner: true,
})

function agencyId() { return auth.agencies[0]?.id }

async function load() {
  loading.value = true
  try {
    if (!auth.agencies.length) await auth.fetchAgencies()
    const id = agencyId()
    if (!id) { expenses.value = []; return }
    const { data } = await agencyApi.expenses(id)
    expenses.value = (data as any).data?.results || (data as any).data || []
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true; saveError.value = ''
  try {
    const id = agencyId()
    if (!id) throw new Error('No agency')
    await agencyApi.createExpense(id, form.value)
    showForm.value = false
    form.value = { property: '', category: 'maintenance', amount: 0, incurred_on: new Date().toISOString().slice(0, 10), description: '', is_deductible_from_owner: true }
    await load()
  } catch (e: any) {
    saveError.value = e?.response?.data?.error?.message || 'Failed to save expense.'
  } finally {
    saving.value = false
  }
}
onMounted(load)
</script>
