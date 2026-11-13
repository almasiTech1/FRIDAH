<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="page-title">My Listings</h1>
      <button class="btn-primary bg-hotel-600 hover:bg-hotel-700" @click="showForm = !showForm">+ Add Listing</button>
    </div>

    <div v-if="showForm" class="card card-body space-y-4">
      <h2 class="section-title">New Listing</h2>
      <div class="grid grid-cols-2 gap-4">
        <div><label class="label">Name</label><input v-model="form.name" class="input" placeholder="Nairobi Boutique Hotel"/></div>
        <div><label class="label">Type</label>
          <select v-model="form.listing_type" class="input">
            <option value="hotel">Hotel</option><option value="bnb">BnB</option>
            <option value="apartment_stay">Serviced Apartment</option><option value="villa">Villa</option>
          </select>
        </div>
        <div><label class="label">County</label><input v-model="form.county" class="input" placeholder="Nairobi"/></div>
        <div><label class="label">Town</label><input v-model="form.town" class="input" placeholder="Kilimani"/></div>
        <div class="col-span-2">
          <AddressAutocomplete
            v-model="form.address_detail"
            label="Address"
            placeholder="Start typing… e.g. Kilimani, Nairobi"
            @place-selected="onPlaceSelected"
            @cleared="onAddressCleared"
          />
          <div class="mt-3"><LocationPicker :lat="form.latitude" :lng="form.longitude" @update="onPinMoved" /></div>
        </div>
        <div><label class="label">Check-in Time</label><input v-model="form.check_in_time" class="input" type="time"/></div>
        <div><label class="label">Check-out Time</label><input v-model="form.check_out_time" class="input" type="time"/></div>
      </div>
      <div><label class="label">Description</label><textarea v-model="form.description" class="input resize-none" rows="2"/></div>
      <div><label class="label">Cancellation Policy</label><textarea v-model="form.cancellation_policy" class="input resize-none" rows="2" placeholder="Free cancellation up to 24h before check-in…"/></div>
      <div class="flex gap-3">
        <button class="btn-outline border-gray-200" @click="showForm = false">Cancel</button>
        <button class="btn-primary bg-hotel-600 hover:bg-hotel-700" :disabled="saving" @click="addListing">
          <span v-if="saving" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"/>
          <span v-else>Submit for Approval</span>
        </button>
      </div>
      <p v-if="saveError" class="text-sm text-red-600">{{ saveError }}</p>
    </div>

    <div v-if="loading" class="space-y-3"><div v-for="i in 3" :key="i" class="card animate-pulse h-20 bg-gray-100 rounded-xl"/></div>
    <div v-else-if="!listings.length" class="card card-body text-center py-12 text-gray-400">
      <p class="text-3xl mb-3">🏨</p><p>No listings yet. Add your first property above.</p>
    </div>
    <div v-else class="space-y-3">
      <div v-for="l in listings" :key="l.id" class="card card-body">
        <div class="flex items-center gap-4">
          <div class="flex-1">
            <div class="flex items-center gap-2 flex-wrap">
              <p class="font-semibold text-gray-900">{{ l.name }}</p>
              <span :class="statusColor(l.status)" class="badge">{{ l.status.replace('_',' ') }}</span>
              <span class="badge badge-gray capitalize">{{ l.listing_type }}</span>
            </div>
            <p class="text-xs text-gray-500 mt-0.5">{{ l.town }}, {{ l.county }}</p>
          </div>
          <div class="flex-shrink-0 text-right">
            <button v-if="managementFor(l.id)?.managing_agency" class="badge badge-blue text-xs block mb-1"
              @click="expandedId = expandedId === l.id ? null : l.id">
              🏢 {{ managementFor(l.id)?.managing_agency?.name }}
              <span class="ml-0.5">{{ expandedId === l.id ? '▲' : '▼' }}</span>
            </button>
            <span v-else class="badge badge-gray text-xs block mb-1">Self-managed</span>
            <button v-if="!managementFor(l.id)?.managing_agency" class="text-xs text-hotel-600 underline" @click="openAssign(l)">Assign to agency</button>
          </div>
          <RouterLink :to="`/hotel/rooms`" class="btn-outline border-gray-200 text-xs">Rooms</RouterLink>
        </div>

        <!-- Management terms detail panel (agency-managed listings only) -->
        <div v-if="expandedId === l.id && managementFor(l.id)?.managing_agency" class="mt-4 pt-4 border-t border-gray-100 grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p class="text-xs text-gray-400">Management Fee</p>
            <p class="text-sm font-semibold">{{ managementFor(l.id)?.managing_agency?.management_fee_percent }}%</p>
          </div>
          <div>
            <p class="text-xs text-gray-400">Payout Rule</p>
            <p class="text-sm font-semibold">{{ managementFor(l.id)?.managing_agency?.payout_rule === 'agency_collects' ? 'Agency collects, remits to me' : 'I receive revenue directly' }}</p>
          </div>
          <div>
            <p class="text-xs text-gray-400">Managed Since</p>
            <p class="text-sm font-semibold">{{ formatDate(managementFor(l.id)?.managing_agency?.managed_since || '') }}</p>
          </div>
          <div>
            <p class="text-xs text-gray-400">Agreement Status</p>
            <p class="text-sm font-semibold capitalize">{{ managementFor(l.id)?.managing_agency?.agreement_status?.replace('_',' ') || 'No formal agreement on file' }}</p>
          </div>
          <div class="col-span-2 md:col-span-4 flex items-center justify-between flex-wrap gap-2 pt-1">
            <p class="text-xs text-gray-500">
              {{ managementFor(l.id)?.managing_agency?.name }}
              <span v-if="managementFor(l.id)?.managing_agency?.email"> · {{ managementFor(l.id)?.managing_agency?.email }}</span>
              <span v-if="managementFor(l.id)?.managing_agency?.phone_number"> · {{ managementFor(l.id)?.managing_agency?.phone_number }}</span>
            </p>
            <RouterLink :to="`/hotel/statements?listing=${l.id}`" class="btn-outline border-gray-200 text-xs">View Statements &amp; Payouts</RouterLink>
          </div>
        </div>
      </div>
    </div>

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
              <span class="w-7 h-7 rounded-full bg-hotel-100 text-hotel-700 flex items-center justify-center text-xs font-bold flex-shrink-0">{{ a.name[0]?.toUpperCase() }}</span>
              <span class="flex-1">
                <span class="block font-medium text-gray-800">{{ a.name }}</span>
                <span class="block text-xs text-gray-400">{{ a.town }}, {{ a.county }} · {{ a.managed_properties_count }} properties managed</span>
              </span>
            </button>
          </div>
          <p v-else-if="agencySearchQuery && searchedAgencies" class="text-xs text-gray-400 mt-1">No active agencies found.</p>
        </div>

        <div v-if="selectedAgency" class="flex items-center gap-2 bg-hotel-50 rounded-xl px-3 py-2">
          <span class="w-8 h-8 rounded-full bg-hotel-100 text-hotel-700 flex items-center justify-center text-xs font-bold flex-shrink-0">{{ selectedAgency.name[0]?.toUpperCase() }}</span>
          <span class="flex-1 text-sm font-medium text-gray-800">{{ selectedAgency.name }}</span>
          <button class="text-xs text-gray-400 underline" @click="selectedAgency = null; assignForm.agency_id = ''">Change</button>
        </div>

        <div><label class="label">Management Fee %</label><input v-model.number="assignForm.management_fee_percent" type="number" step="0.1" class="input"/></div>
        <div><label class="label">Payout Rule</label>
          <select v-model="assignForm.payout_rule" class="input">
            <option value="owner_direct">I receive revenue directly</option>
            <option value="agency_collects">Agency collects, then remits to me</option>
          </select>
        </div>
        <div class="flex gap-3">
          <button class="btn-outline border-gray-200 flex-1" @click="assignTarget = null">Cancel</button>
          <button class="btn-primary bg-hotel-600 hover:bg-hotel-700 flex-1" :disabled="assigning || !assignForm.agency_id" @click="confirmAssign">
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
import { bookingsApi, agencyApi } from '@/api/services'
import { statusColor, formatDate } from '@/utils/formatters'
import LocationPicker from '@/components/public/LocationPicker.vue'
import AddressAutocomplete, { type PlaceSelection } from '@/components/public/AddressAutocomplete.vue'
import type { Listing, OwnedListing, AgencyDirectoryEntry } from '@/types'
const listings = ref<Listing[]>([])
const ownedListings = ref<OwnedListing[]>([])
const loading = ref(true); const showForm = ref(false); const saving = ref(false); const saveError = ref('')
const expandedId = ref<string | null>(null)
const assignTarget = ref<Listing | null>(null)
const assigning = ref(false)
const assignError = ref('')
const assignForm = ref({ agency_id: '', management_fee_percent: 5, payout_rule: 'owner_direct' as 'owner_direct' | 'agency_collects' })
const agencySearchQuery = ref('')
const agencySearchResults = ref<AgencyDirectoryEntry[]>([])
const selectedAgency = ref<AgencyDirectoryEntry | null>(null)
const searchedAgencies = ref(false)
let agencySearchDebounce: ReturnType<typeof setTimeout> | null = null

function managementFor(listingId: string) {
  return ownedListings.value.find((ol) => ol.id === listingId)
}

function openAssign(l: Listing) {
  assignTarget.value = l
  assignError.value = ''
  assignForm.value = { agency_id: '', management_fee_percent: 5, payout_rule: 'owner_direct' }
  agencySearchQuery.value = ''
  agencySearchResults.value = []
  selectedAgency.value = null
  searchedAgencies.value = false
}

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

async function confirmAssign() {
  if (!assignTarget.value) return
  assigning.value = true; assignError.value = ''
  try {
    await agencyApi.assignListing({
      listing_id: assignTarget.value.id,
      agency_id: assignForm.value.agency_id,
      start_date: new Date().toISOString().slice(0, 10),
      management_fee_percent: assignForm.value.management_fee_percent,
      payout_rule: assignForm.value.payout_rule,
    })
    assignTarget.value = null
    await loadOwnedListings()
  } catch (e: any) {
    assignError.value = e?.response?.data?.error?.message || 'Failed to assign listing.'
  } finally {
    assigning.value = false
  }
}

async function loadOwnedListings() {
  try {
    const { data } = await agencyApi.ownerListings()
    ownedListings.value = (data as any).data || []
  } catch { ownedListings.value = [] }
}

const form = ref<{ name: string; listing_type: string; county: string; town: string; address_detail: string; check_in_time: string; check_out_time: string; description: string; cancellation_policy: string; latitude?: number; longitude?: number }>({
  name:'', listing_type:'hotel', county:'', town:'', address_detail:'', check_in_time:'14:00', check_out_time:'11:00', description:'', cancellation_policy:'',
})

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

async function load() {
  try { const { data } = await bookingsApi.listings(); listings.value = data.data?.results || data.data || [] }
  catch { listings.value = [] } finally { loading.value = false }
  await loadOwnedListings()
}
async function addListing() {
  saving.value = true; saveError.value = ''
  try { await bookingsApi.createListing(form.value as any); showForm.value = false; await load() }
  catch (e: any) { saveError.value = e?.response?.data?.error?.message || 'Failed.' }
  finally { saving.value = false }
}
onMounted(load)
</script>
