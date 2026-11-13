<template>
  <div class="space-y-5">
    <button class="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1" @click="router.back()">&larr; Back</button>

    <div v-if="loading" class="card card-body h-64 animate-pulse bg-gray-100" />

    <template v-else-if="property">
      <div class="card overflow-hidden">
        <div class="h-56 bg-gray-100 relative">
          <img v-if="property.primary_image" :src="property.primary_image" class="w-full h-full object-cover" />
          <div v-else class="w-full h-full flex items-center justify-center text-gray-300 text-5xl">🏠</div>
        </div>
        <div class="p-5">
          <div class="flex items-start justify-between">
            <div>
              <h1 class="text-xl font-bold text-gray-900">{{ property.name }}</h1>
              <p class="text-sm text-gray-500 mt-0.5">{{ property.estate ? property.estate + ', ' : '' }}{{ property.town }}, {{ property.county }}</p>
            </div>
            <span class="badge badge-gray capitalize">{{ property.property_type }}</span>
          </div>
          <p v-if="property.description" class="text-sm text-gray-600 mt-3">{{ property.description }}</p>
          <div v-if="property.amenities?.length" class="flex flex-wrap gap-2 mt-3">
            <span v-for="a in property.amenities" :key="a" class="badge badge-gray text-xs">{{ a }}</span>
          </div>
        </div>
      </div>

      <div class="card card-body">
        <h2 class="section-title">Location</h2>
        <LocationMap :lat="property.latitude" :lng="property.longitude" :title="property.name"
          :address-text="[property.estate, property.town, property.county].filter(Boolean).join(', ')" />
      </div>

      <div class="card card-body">
        <h2 class="section-title">Units</h2>
        <div v-if="!property.units?.length" class="text-sm text-gray-400 py-4 text-center">No units listed yet.</div>
        <div v-else class="space-y-3">
          <div v-for="u in property.units" :key="u.id" class="flex flex-wrap items-start justify-between p-4 rounded-xl border border-gray-100 gap-y-2">
            <div>
              <p class="font-semibold text-gray-900 text-sm">Unit {{ u.unit_number }}</p>
              <p class="text-xs text-gray-500 mt-0.5">{{ u.bedrooms }} bed &middot; {{ u.bathrooms }} bath{{ u.size_sqm ? ` · ${u.size_sqm}m²` : '' }}</p>
              <p class="text-tenant-600 font-semibold text-sm mt-1">{{ formatKES(u.rent_amount) }}/mo</p>
            </div>
            <div class="text-right">
              <span class="badge text-xs mb-2 block" :class="u.status === 'vacant' ? 'badge-green' : 'badge-gray'">{{ u.status }}</span>
              <button
                v-if="u.status === 'vacant'"
                class="btn-primary bg-tenant-600 hover:bg-tenant-700 text-xs"
                @click="openApply(u)"
              >
                {{ myApplicationFor(u.id) ? 'Applied ✓' : 'Apply to Rent' }}
              </button>
            </div>
            <div class="w-full">
              <button class="text-xs text-tenant-600 font-semibold hover:underline" @click="toggleCostOfLiving(u.id)">
                {{ costOfLivingOpen === u.id ? 'Hide cost of living breakdown' : '💰 See total cost of living' }}
              </button>
              <div v-if="costOfLivingOpen === u.id" class="mt-2 p-3 rounded-lg bg-gray-50 space-y-2">
                <div v-if="costOfLivingLoading" class="text-xs text-gray-400">Loading…</div>
                <template v-else-if="costOfLivingData">
                  <div class="flex justify-between text-xs"><span class="text-gray-500">Rent</span><span class="font-medium">{{ formatKES(costOfLivingData.rent) }}</span></div>
                  <div v-for="line in costOfLivingData.utilities" :key="line.utility_type" class="flex justify-between text-xs">
                    <span class="text-gray-500 capitalize">{{ line.utility_type }}</span>
                    <span class="font-medium">{{ line.monthly_estimate ? formatKES(line.monthly_estimate) : 'No data yet' }}</span>
                  </div>
                  <div class="flex justify-between text-xs pt-2 border-t border-gray-200">
                    <span class="text-gray-600 font-semibold">Platform total</span>
                    <span class="font-bold text-tenant-600">{{ formatKES(costOfLivingData.platform_total) }}</span>
                  </div>
                  <p class="text-[10px] text-gray-400 pt-1">{{ costOfLivingData.note }}</p>
                  <div class="pt-2 border-t border-gray-200 space-y-2">
                    <p class="text-[11px] font-semibold text-gray-600">Add your own estimates</p>
                    <div class="flex gap-2">
                      <input v-model.number="personalCosts.transport" type="number" placeholder="Transport" class="input text-xs py-1.5 flex-1" />
                      <input v-model.number="personalCosts.other" type="number" placeholder="Other" class="input text-xs py-1.5 flex-1" />
                    </div>
                    <div class="flex justify-between text-xs pt-1">
                      <span class="text-gray-700 font-bold">Your estimated total</span>
                      <span class="font-bold text-gray-900">{{ formatKES(Number(costOfLivingData.platform_total) + (personalCosts.transport || 0) + (personalCosts.other || 0)) }}</span>
                    </div>
                  </div>
                </template>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <div v-else class="card card-body text-center py-12 text-gray-400">Property not found.</div>

    <!-- Apply modal -->
    <div v-if="applyUnit" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" @click.self="applyUnit = null">
      <div class="card w-full max-w-md p-5 space-y-4">
        <h2 class="section-title">Apply for Unit {{ applyUnit.unit_number }}</h2>
        <p class="text-sm text-gray-500">{{ formatKES(applyUnit.rent_amount) }}/mo &middot; Deposit {{ formatKES(applyUnit.deposit_amount) }}</p>
        <div>
          <label class="label">Preferred move-in date</label>
          <input v-model="applyForm.preferred_move_in_date" type="date" class="input" />
        </div>
        <div>
          <label class="label">Message to landlord (optional)</label>
          <textarea v-model="applyForm.message" class="input resize-none" rows="3" placeholder="Tell the landlord a bit about yourself..." />
        </div>
        <p v-if="applyError" class="text-xs text-red-600">{{ applyError }}</p>
        <div class="flex gap-3">
          <button class="btn-outline border-gray-200 flex-1" @click="applyUnit = null">Cancel</button>
          <button class="btn-primary bg-tenant-600 hover:bg-tenant-700 flex-1" :disabled="applying" @click="submitApplication">
            <span v-if="applying" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
            <span v-else>Submit Application</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { propertiesApi, rentalsApi } from '@/api/services'
import { formatKES } from '@/utils/formatters'
import LocationMap from '@/components/public/LocationMap.vue'
import type { Property, Unit } from '@/types'

const route = useRoute()
const router = useRouter()
const property = ref<Property | null>(null)
const loading = ref(true)
const myApplications = ref<any[]>([])

const applyUnit = ref<Unit | null>(null)
const applyForm = ref({ preferred_move_in_date: '', message: '' })
const applying = ref(false)
const applyError = ref('')

const costOfLivingOpen = ref('')
const costOfLivingLoading = ref(false)
const costOfLivingData = ref<any>(null)
const personalCosts = ref<{ transport: number | null; other: number | null }>({ transport: null, other: null })

async function toggleCostOfLiving(unitId: string) {
  if (costOfLivingOpen.value === unitId) {
    costOfLivingOpen.value = ''
    return
  }
  costOfLivingOpen.value = unitId
  costOfLivingData.value = null
  personalCosts.value = { transport: null, other: null }
  costOfLivingLoading.value = true
  try {
    const { data } = await propertiesApi.costOfLiving(unitId)
    costOfLivingData.value = (data as any).data || data
  } catch {
    costOfLivingData.value = null
  } finally {
    costOfLivingLoading.value = false
  }
}

function myApplicationFor(unitId: string) {
  return myApplications.value.find((a) => a.unit === unitId && a.status === 'pending')
}

function openApply(unit: Unit) {
  if (myApplicationFor(unit.id)) return
  applyUnit.value = unit
  applyForm.value = { preferred_move_in_date: '', message: '' }
  applyError.value = ''
}

async function submitApplication() {
  if (!applyUnit.value) return
  applying.value = true
  applyError.value = ''
  try {
    await rentalsApi.applyToUnit(applyUnit.value.id, {
      message: applyForm.value.message || undefined,
      preferred_move_in_date: applyForm.value.preferred_move_in_date || undefined,
    })
    applyUnit.value = null
    await loadMyApplications()
  } catch (e: any) {
    applyError.value = e?.response?.data?.error?.message || 'Failed to submit application.'
  } finally {
    applying.value = false
  }
}

async function loadMyApplications() {
  try {
    const { data } = await rentalsApi.applications()
    myApplications.value = (data as any).results || (data as any).data || []
  } catch { myApplications.value = [] }
}

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await propertiesApi.get(route.params.id as string)
    property.value = (data as any).data || data
  } catch {
    property.value = null
  } finally {
    loading.value = false
  }
  await loadMyApplications()
})
</script>
