<template>
  <div class="space-y-5">
    <div>
      <h1 class="page-title">Amenity Charges</h1>
      <p class="text-sm text-gray-500 mt-0.5">
        Charge tenants for shared services - security, water, garbage, parking, gym. Each charge becomes an itemised
        invoice that tenants pay through M-Pesa like rent.
      </p>
    </div>

    <form class="card card-body grid md:grid-cols-5 gap-3 items-end" @submit.prevent="create">
      <div class="md:col-span-1">
        <label class="text-xs font-medium text-gray-600" for="am-prop">Property</label>
        <select id="am-prop" v-model="form.property" class="input" required>
          <option value="" disabled>Choose…</option>
          <option v-for="p in properties" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
      </div>
      <div>
        <label class="text-xs font-medium text-gray-600" for="am-name">Name</label>
        <input id="am-name" v-model="form.name" class="input" required maxlength="120" placeholder="e.g. Security" />
      </div>
      <div>
        <label class="text-xs font-medium text-gray-600" for="am-amt">Amount (KES)</label>
        <input id="am-amt" v-model="form.amount" type="number" min="1" step="0.01" class="input" required />
      </div>
      <div>
        <label class="text-xs font-medium text-gray-600" for="am-freq">Billing</label>
        <select id="am-freq" v-model="form.frequency" class="input">
          <option value="monthly">Monthly</option>
          <option value="one_off">One-off</option>
        </select>
      </div>
      <button class="btn bg-gray-900 text-white justify-center" :disabled="saving">{{ saving ? 'Saving…' : 'Add charge' }}</button>
      <p v-if="error" class="md:col-span-5 text-sm text-red-600" role="alert">{{ error }}</p>
    </form>

    <div v-if="loading" class="space-y-3" aria-busy="true">
      <div v-for="i in 2" :key="i" class="card animate-pulse h-20 bg-gray-100 rounded-xl" />
    </div>
    <div v-else-if="!charges.length" class="card card-body text-center py-12 text-gray-400">
      No amenity charges yet. Add your first one above.
    </div>

    <div v-else class="space-y-3 stagger">
      <div v-for="c in charges" :key="c.id" class="card card-body flex items-center justify-between flex-wrap gap-3">
        <div>
          <div class="flex items-center gap-2 flex-wrap">
            <p class="font-semibold text-gray-900">{{ c.name }}</p>
            <span class="badge" :class="c.is_active ? 'badge-green' : 'badge-gray'">{{ c.is_active ? 'Active' : 'Paused' }}</span>
            <span class="badge badge-blue">{{ c.frequency === 'monthly' ? 'Monthly' : 'One-off' }}</span>
          </div>
          <p class="text-xs text-gray-500 mt-0.5">{{ propertyName(c.property) }} · {{ formatKES(c.amount) }}
            · {{ c.applies_to_all_units ? 'All units' : `${c.units.length} selected units` }}</p>
          <p v-if="notice[c.id]" class="text-xs text-emerald-700 mt-1" role="status">{{ notice[c.id] }}</p>
        </div>
        <div class="flex gap-2">
          <button class="btn-outline border-gray-200 text-xs" :disabled="busy === c.id" @click="billNow(c)">Bill now</button>
          <button class="btn-outline border-gray-200 text-xs" :disabled="busy === c.id" @click="toggle(c)">
            {{ c.is_active ? 'Pause' : 'Resume' }}
          </button>
        </div>
      </div>
    </div>

    <p class="text-xs text-gray-400">
      Billing runs automatically each day and never bills the same tenant twice for the same month. To waive an unpaid
      amenity invoice, open it under Invoices and use “Waive” - a reason is always required and recorded.
    </p>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { amenityApi, agencyApi } from '@/api/services'
import { formatKES } from '@/utils/formatters'

const charges = ref<any[]>([])
const properties = ref<any[]>([])
const loading = ref(true)
const saving = ref(false)
const busy = ref<string | null>(null)
const error = ref('')
const notice = ref<Record<string, string>>({})
const form = ref({ property: '', name: '', amount: '', frequency: 'monthly' })

const list = (res: any) => res.data?.data?.results || res.data?.results || res.data?.data || []
const propertyName = (id: string) => properties.value.find((p) => p.id === id)?.name || 'Property'

async function load() {
  loading.value = true
  try { charges.value = list(await amenityApi.list()) } catch { charges.value = [] } finally { loading.value = false }
}

async function create() {
  saving.value = true; error.value = ''
  try {
    await amenityApi.create({ ...form.value, applies_to_all_units: true })
    form.value = { property: form.value.property, name: '', amount: '', frequency: 'monthly' }
    await load()
  } catch (e: any) {
    const d = e?.response?.data
    error.value = d?.error?.message || d?.amount?.[0] || d?.detail || 'Could not add the charge.'
  } finally { saving.value = false }
}

async function toggle(c: any) {
  busy.value = c.id
  try { await amenityApi.update(c.id, { is_active: !c.is_active }); await load() } finally { busy.value = null }
}

async function billNow(c: any) {
  busy.value = c.id
  try {
    const res: any = await amenityApi.billNow(c.id)
    const d = res.data?.data || {}
    notice.value = { ...notice.value, [c.id]: `Billed ${d.created ?? 0} tenant(s); ${d.skipped ?? 0} already billed or exempt.` }
  } catch (e: any) {
    notice.value = { ...notice.value, [c.id]: e?.response?.data?.detail || 'Billing failed.' }
  } finally { busy.value = null }
}

onMounted(async () => {
  try { properties.value = list(await agencyApi.myProperties()) } catch { properties.value = [] }
  await load()
})
</script>
