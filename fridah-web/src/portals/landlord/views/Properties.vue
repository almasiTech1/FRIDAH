<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="page-title">My Properties</h1>
      <button class="btn-primary bg-landlord-600 hover:bg-landlord-700" @click="showForm = !showForm">+ Add Property</button>
    </div>

    <!-- Add form -->
    <div v-if="showForm" class="card card-body space-y-4">
      <h2 class="section-title">New Property</h2>
      <div class="grid grid-cols-2 gap-4">
        <div><label class="label">Name</label><input v-model="form.name" class="input" placeholder="Sunset Apartments"/></div>
        <div><label class="label">Type</label>
          <select v-model="form.property_type" class="input">
            <option v-for="t in types" :key="t.value" :value="t.value">{{ t.label }}</option>
          </select>
        </div>
      </div>
      <AddressAutocomplete
        v-model="addressQuery"
        label="Address"
        placeholder="Start typing… e.g. Lavington, Nairobi"
        @place-selected="onPlaceSelected"
        @cleared="onAddressCleared"
      />
      <LocationPicker :lat="form.latitude" :lng="form.longitude" @update="onPinMoved" />
      <div class="grid grid-cols-2 gap-4">
        <div><label class="label">County</label><input v-model="form.county" class="input" placeholder="Nairobi"/></div>
        <div><label class="label">Town</label><input v-model="form.town" class="input" placeholder="Westlands"/></div>
        <div><label class="label">Estate</label><input v-model="form.estate" class="input" placeholder="Lavington"/></div>
        <div><label class="label">Total Units</label><input v-model.number="form.total_units" class="input" type="number" min="1"/></div>
      </div>
      <div><label class="label">Description</label><textarea v-model="form.description" class="input resize-none" rows="2"/></div>
      <div><label class="label">Amenities (comma-separated)</label><input v-model="amenitiesInput" class="input" placeholder="parking, borehole water, gym"/></div>

      <div class="p-4 rounded-xl bg-brand-50 dark:bg-brand-950 border border-brand-100 dark:border-brand-900 space-y-3">
        <p class="text-sm font-semibold text-brand-700 dark:text-brand-400">✨ Generate listing copy with AI</p>
        <input type="file" accept="image/*" multiple class="input text-xs" @change="onPhotosSelected" />
        <button class="btn-outline text-xs" :disabled="!aiPhotos.length || aiGenerating" @click="generateWithAi">
          <span v-if="aiGenerating" class="animate-spin w-3.5 h-3.5 border-2 border-brand-600 border-t-transparent rounded-full" />
          <span v-else>Generate from {{ aiPhotos.length || 0 }} photo{{ aiPhotos.length === 1 ? '' : 's' }}</span>
        </button>
        <p v-if="aiGenError" class="text-xs text-red-600">{{ aiGenError }}</p>
      </div>

      <div class="flex gap-3">
        <button class="btn-outline border-gray-200" @click="showForm = false">Cancel</button>
        <button class="btn-primary bg-landlord-600 hover:bg-landlord-700" :disabled="saving" @click="save">
          <span v-if="saving" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"/>
          <span v-else>Submit for Approval</span>
        </button>
      </div>
      <p v-if="saveError" class="text-sm text-red-600">{{ saveError }}</p>
    </div>

    <!-- List -->
    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="card animate-pulse h-20 bg-gray-100 rounded-xl"/>
    </div>
    <div v-else-if="properties.length" class="space-y-3">
      <div v-for="p in properties" :key="p.id" class="card card-body">
        <div class="flex items-center gap-4">
          <div class="flex-1">
            <div class="flex items-center gap-3 flex-wrap">
              <p class="font-semibold text-gray-900">{{ p.name }}</p>
              <span :class="statusColor(p.status)" class="badge">{{ p.status.replace('_',' ') }}</span>
              <span v-if="p.status !== 'active' && p.review_state" :class="statusColor(p.review_state)" class="badge">{{ reviewStateLabel(p.review_state) }}</span>
            </div>
            <p class="text-xs text-gray-500 mt-0.5">{{ p.estate ? p.estate + ', ' : '' }}{{ p.town }}, {{ p.county }} · {{ p.property_type }}</p>
          </div>
          <div class="text-right flex-shrink-0">
            <p class="text-sm font-medium">{{ p.total_units }} units</p>
            <p class="text-xs text-green-600">{{ p.vacant_units_count }} vacant</p>
          </div>
          <div class="flex-shrink-0 text-right">
            <button v-if="managementFor(p.id)?.managing_agency" class="badge badge-blue text-xs block mb-1"
              @click="expandedId = expandedId === p.id ? null : p.id">
              🏢 {{ managementFor(p.id)?.managing_agency?.name }}
              <span class="ml-0.5">{{ expandedId === p.id ? '▲' : '▼' }}</span>
            </button>
            <span v-else class="badge badge-gray text-xs block mb-1">Self-managed</span>
            <button v-if="!managementFor(p.id)?.managing_agency" class="text-xs text-brand-600 underline" @click="openAssign(p)">Assign to agency</button>
          </div>
          <RouterLink :to="`/landlord/units?property=${p.id}`" class="btn-outline border-gray-200 text-xs">Units</RouterLink>
        </div>

        <!-- Management terms detail panel (agency-managed properties only) -->
        <div v-if="expandedId === p.id && managementFor(p.id)?.managing_agency" class="mt-4 pt-4 border-t border-gray-100 grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p class="text-xs text-gray-400">Management Fee</p>
            <p class="text-sm font-semibold">{{ managementFor(p.id)?.managing_agency?.management_fee_percent }}%</p>
          </div>
          <div>
            <p class="text-xs text-gray-400">Payout Rule</p>
            <p class="text-sm font-semibold">{{ managementFor(p.id)?.managing_agency?.payout_rule === 'agency_collects' ? 'Agency collects, remits to me' : 'I receive rent directly' }}</p>
          </div>
          <div>
            <p class="text-xs text-gray-400">Managed Since</p>
            <p class="text-sm font-semibold">{{ formatDate(managementFor(p.id)?.managing_agency?.managed_since || '') }}</p>
          </div>
          <div>
            <p class="text-xs text-gray-400">Agreement Status</p>
            <p class="text-sm font-semibold capitalize">{{ managementFor(p.id)?.managing_agency?.agreement_status?.replace('_',' ') || 'No formal agreement on file' }}</p>
          </div>
          <div class="col-span-2 md:col-span-4 flex items-center justify-between flex-wrap gap-2 pt-1">
            <p class="text-xs text-gray-500">
              {{ managementFor(p.id)?.managing_agency?.name }}
              <span v-if="managementFor(p.id)?.managing_agency?.email"> · {{ managementFor(p.id)?.managing_agency?.email }}</span>
              <span v-if="managementFor(p.id)?.managing_agency?.phone_number"> · {{ managementFor(p.id)?.managing_agency?.phone_number }}</span>
            </p>
            <span class="flex items-center gap-2">
              <RouterLink to="/landlord/managed" class="btn-outline border-gray-200 text-xs">Tenants &amp; Revenue</RouterLink>
              <RouterLink :to="`/landlord/statements?property=${p.id}`" class="btn-outline border-gray-200 text-xs">Statements &amp; Payouts</RouterLink>
            </span>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="card card-body text-center py-12 text-gray-400">No properties yet. Add your first one above.</div>

    <!-- Assign to agency modal -->
    <div v-if="assignTarget" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" @click.self="assignTarget = null">
      <div class="card card-body w-full max-w-md space-y-4">
        <h2 class="section-title">Assign "{{ assignTarget.name }}" to an Agency</h2>

        <div class="relative">
          <label class="label">Search Agencies</label>
          <input v-model="agencySearchQuery" class="input" placeholder="Search by name, town, or county…" @input="onAgencySearch"/>
          <div v-if="agencySearchResults.length" class="absolute z-10 mt-1 w-full bg-white border border-gray-100 rounded-xl shadow-lg max-h-48 overflow-y-auto">
            <button v-for="a in agencySearchResults" :key="a.id" class="w-full text-left px-3 py-2 hover:bg-gray-50 flex items-center gap-2 text-sm"
              @click="pickAgency(a)">
              <span class="w-7 h-7 rounded-full bg-landlord-100 text-landlord-700 flex items-center justify-center text-xs font-bold flex-shrink-0">{{ a.name[0]?.toUpperCase() }}</span>
              <span class="flex-1">
                <span class="block font-medium text-gray-800">{{ a.name }}</span>
                <span class="block text-xs text-gray-400">{{ a.town }}, {{ a.county }} · {{ a.managed_properties_count }} properties managed</span>
              </span>
            </button>
          </div>
          <p v-else-if="agencySearchQuery && searchedAgencies" class="text-xs text-gray-400 mt-1">No active agencies found.</p>
        </div>

        <div v-if="selectedAgency" class="flex items-center gap-2 bg-landlord-50 rounded-xl px-3 py-2">
          <span class="w-8 h-8 rounded-full bg-landlord-100 text-landlord-700 flex items-center justify-center text-xs font-bold flex-shrink-0">{{ selectedAgency.name[0]?.toUpperCase() }}</span>
          <span class="flex-1 text-sm font-medium text-gray-800">{{ selectedAgency.name }}</span>
          <button class="text-xs text-gray-400 underline" @click="selectedAgency = null; assignForm.agency_id = ''">Change</button>
        </div>

        <div><label class="label">Management Fee %</label><input v-model.number="assignForm.management_fee_percent" type="number" step="0.1" class="input"/></div>
        <div><label class="label">Payout Rule</label>
          <select v-model="assignForm.payout_rule" class="input">
            <option value="owner_direct">I receive rent directly</option>
            <option value="agency_collects">Agency collects, then remits to me</option>
          </select>
        </div>
        <div class="flex gap-3">
          <button class="btn-outline border-gray-200 flex-1" @click="assignTarget = null">Cancel</button>
          <button class="btn-primary bg-landlord-600 hover:bg-landlord-700 flex-1" :disabled="assigning || !assignForm.agency_id" @click="confirmAssign">
            <span v-if="assigning" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"/>
            <span v-else>Assign</span>
          </button>
        </div>
        <p v-if="assignError" class="text-sm text-red-600">{{ assignError }}</p>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { propertiesApi, aiApi, agencyApi } from '@/api/services'
import { statusColor, formatDate, reviewStateLabel } from '@/utils/formatters'
import LocationPicker from '@/components/public/LocationPicker.vue'
import AddressAutocomplete, { type PlaceSelection } from '@/components/public/AddressAutocomplete.vue'
import type { Property, OwnedProperty, AgencyDirectoryEntry } from '@/types'
const properties = ref<Property[]>([])
const ownedProperties = ref<OwnedProperty[]>([])
const loading = ref(true); const showForm = ref(false); const saving = ref(false); const saveError = ref('')
const addressQuery = ref('')
const amenitiesInput = ref('')
const aiPhotos = ref<File[]>([])
const aiGenerating = ref(false)
const aiGenError = ref('')
const assignTarget = ref<Property | null>(null)
const expandedId = ref<string | null>(null)
const assigning = ref(false)
const assignError = ref('')
const assignForm = ref({ agency_id: '', management_fee_percent: 5, payout_rule: 'owner_direct' as 'owner_direct' | 'agency_collects' })
const agencySearchQuery = ref('')
const agencySearchResults = ref<AgencyDirectoryEntry[]>([])
const selectedAgency = ref<AgencyDirectoryEntry | null>(null)
const searchedAgencies = ref(false)
let agencySearchDebounce: ReturnType<typeof setTimeout> | null = null

function onAgencySearch() {
  selectedAgency.value = null
  assignForm.value.agency_id = ''
  if (agencySearchDebounce) clearTimeout(agencySearchDebounce)
  if (!agencySearchQuery.value.trim()) { agencySearchResults.value = []; searchedAgencies.value = false; return }
  agencySearchDebounce = setTimeout(async () => {
    searchedAgencies.value = false
    try {
      const { data } = await agencyApi.searchDirectory(agencySearchQuery.value.trim())
      agencySearchResults.value = (data as any).data || []
    } catch {
      agencySearchResults.value = []
    } finally {
      searchedAgencies.value = true
    }
  }, 300)
}

function pickAgency(a: AgencyDirectoryEntry) {
  selectedAgency.value = a
  assignForm.value.agency_id = a.id
  agencySearchResults.value = []
  agencySearchQuery.value = ''
}
const form = ref<{ name: string; property_type: string; county: string; town: string; estate: string; total_units: number; description: string; latitude?: number; longitude?: number }>({
  name:'', property_type:'apartment', county:'', town:'', estate:'', total_units:1, description:'',
})
const types = [{ value:'apartment',label:'Apartment'},{ value:'bungalow',label:'Bungalow'},{ value:'maisonette',label:'Maisonette'},{ value:'townhouse',label:'Townhouse'},{ value:'commercial',label:'Commercial'},{ value:'hostel',label:'Hostel'},{ value:'bedsitter',label:'Bedsitter'},{ value:'single_room',label:'Single Room'}]

function managementFor(propertyId: string) {
  return ownedProperties.value.find((op) => op.id === propertyId)
}

function openAssign(p: Property) {
  assignTarget.value = p
  assignError.value = ''
  assignForm.value = { agency_id: '', management_fee_percent: 5, payout_rule: 'owner_direct' }
  agencySearchQuery.value = ''
  agencySearchResults.value = []
  selectedAgency.value = null
  searchedAgencies.value = false
}

async function confirmAssign() {
  if (!assignTarget.value) return
  assigning.value = true; assignError.value = ''
  try {
    await agencyApi.assignProperty({
      property_id: assignTarget.value.id,
      agency_id: assignForm.value.agency_id,
      start_date: new Date().toISOString().slice(0, 10),
      management_fee_percent: assignForm.value.management_fee_percent,
      payout_rule: assignForm.value.payout_rule,
    })
    assignTarget.value = null
    await loadOwnedProperties()
  } catch (e: any) {
    assignError.value = e?.response?.data?.error?.message || 'Failed to assign property. Check the Agency ID.'
  } finally {
    assigning.value = false
  }
}

async function loadOwnedProperties() {
  try {
    const { data } = await agencyApi.ownerProperties()
    ownedProperties.value = (data as any).data || []
  } catch { ownedProperties.value = [] }
}

function onPlaceSelected(place: PlaceSelection) {
  form.value.latitude = place.lat
  form.value.longitude = place.lng
  if (place.county) form.value.county = place.county
  if (place.town) form.value.town = place.town
}
function onPinMoved(p: { lat: number; lng: number }) {
  form.value.latitude = p.lat
  form.value.longitude = p.lng
}
function onAddressCleared() {
  form.value.latitude = undefined
  form.value.longitude = undefined
}

function onPhotosSelected(e: Event) {
  const files = (e.target as HTMLInputElement).files
  aiPhotos.value = files ? Array.from(files) : []
}

async function generateWithAi() {
  if (!aiPhotos.value.length) return
  aiGenerating.value = true
  aiGenError.value = ''
  try {
    const facts = {
      property_type: form.value.property_type,
      county: form.value.county,
      town: form.value.town,
      estate: form.value.estate,
      known_amenities: amenitiesInput.value.split(',').map((a) => a.trim()).filter(Boolean),
    }
    const { data } = await aiApi.generateListing(aiPhotos.value, facts)
    const result = (data as any).data
    if (result.title && !form.value.name) form.value.name = result.title
    if (result.description) form.value.description = result.description
    if (result.amenities?.length) amenitiesInput.value = result.amenities.join(', ')
  } catch (e: any) {
    aiGenError.value = e?.response?.status === 503
      ? 'AI listing generation is not available right now.'
      : e?.response?.data?.error?.message || 'Generation failed. Please try again.'
  } finally {
    aiGenerating.value = false
  }
}

async function load() {
  try { const { data } = await propertiesApi.list(); properties.value = data.data?.results || data.data || [] }
  catch { properties.value = [] } finally { loading.value = false }
  await loadOwnedProperties()
}
async function save() {
  saving.value = true; saveError.value = ''
  try {
    const amenities = amenitiesInput.value.split(',').map((a) => a.trim()).filter(Boolean)
    await propertiesApi.create({ ...form.value, amenities } as any)
    showForm.value = false
    form.value = { name:'', property_type:'apartment', county:'', town:'', estate:'', total_units:1, description:'' }
    addressQuery.value = ''
    amenitiesInput.value = ''
    aiPhotos.value = []
    await load()
  }
  catch (e: any) { saveError.value = e?.response?.data?.error?.message || 'Failed to save.' }
  finally { saving.value = false }
}
onMounted(load)
</script>
