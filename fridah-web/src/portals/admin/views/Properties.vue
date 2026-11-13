<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between flex-wrap gap-3">
      <h1 class="page-title">Property Management</h1>
      <div class="flex items-center gap-2">
        <select v-model="statusFilter" class="input w-auto text-sm">
          <option value="">All</option><option value="pending_approval">Pending</option><option value="active">Active</option><option value="suspended">Suspended</option>
        </select>
        <button class="btn-primary bg-gray-900 hover:bg-gray-700 text-sm" @click="showForm = !showForm">
          {{ showForm ? 'Cancel' : '+ Add Property' }}
        </button>
      </div>
    </div>

    <div v-if="showForm" class="card card-body space-y-4">
      <h2 class="section-title">New Property</h2>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="label">Landlord</label>
          <select v-model="form.landlord" class="input" required>
            <option value="" disabled>Select the landlord this property belongs to…</option>
            <option v-for="l in landlords" :key="l.id" :value="l.id">{{ l.first_name }} {{ l.last_name }} ({{ l.email }})</option>
          </select>
          <p v-if="landlordsLoading" class="text-xs text-gray-400 mt-1">Loading landlords…</p>
          <p v-else-if="!landlords.length" class="text-xs text-amber-600 mt-1">No landlord accounts exist yet — create one first, or this property has nowhere to attach.</p>
        </div>
        <div><label class="label">Name</label><input v-model="form.name" class="input" placeholder="Sunset Apartments"/></div>
        <div><label class="label">Type</label>
          <select v-model="form.property_type" class="input">
            <option v-for="t in types" :key="t.value" :value="t.value">{{ t.label }}</option>
          </select>
        </div>
        <div><label class="label">Total Units</label><input v-model.number="form.total_units" class="input" type="number" min="1"/></div>
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
        <div><label class="label">Amenities (comma-separated)</label><input v-model="amenitiesInput" class="input" placeholder="parking, borehole water"/></div>
      </div>
      <div><label class="label">Description</label><textarea v-model="form.description" class="input resize-none" rows="2"/></div>
      <p class="text-xs text-gray-400">Properties added here go live immediately (no separate approval step, since an admin is creating it directly).</p>
      <div class="flex gap-3">
        <button class="btn-outline border-gray-200" @click="showForm = false">Cancel</button>
        <button class="btn-primary bg-gray-900 hover:bg-gray-700" :disabled="saving || !form.landlord" @click="save">
          <span v-if="saving" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"/>
          <span v-else>Create Property</span>
        </button>
      </div>
      <p v-if="saveError" class="text-sm text-red-600">{{ saveError }}</p>
    </div>

    <div class="card overflow-x-auto">
      <div v-if="loading" class="p-8 text-center text-gray-400">Loading…</div>
      <table v-else-if="filtered.length" class="w-full">
        <thead class="bg-gray-50 border-b"><tr>
          <th class="table-th">Property</th><th class="table-th">Landlord</th><th class="table-th">Location</th>
          <th class="table-th">Units</th><th class="table-th">Status</th><th class="table-th">Actions</th>
        </tr></thead>
        <tbody>
          <tr v-for="p in filtered" :key="p.id" class="table-tr">
            <td class="table-td font-medium">{{ p.name }}</td>
            <td class="table-td text-xs">{{ p.landlord_name }}</td>
            <td class="table-td text-xs">{{ p.town }}, {{ p.county }}</td>
            <td class="table-td">{{ p.total_units }}</td>
            <td class="table-td">
              <span :class="statusColor(p.status)" class="badge">{{ p.status.replace('_',' ') }}</span>
              <span v-if="p.status !== 'active' && p.review_state" :class="statusColor(p.review_state)" class="badge ml-1">{{ reviewStateLabel(p.review_state) }}</span>
            </td>
            <td class="table-td flex gap-1 flex-wrap">
              <button v-if="p.status === 'pending_approval'" class="btn-primary bg-green-600 hover:bg-green-700 text-xs py-1 px-2" @click="approve(p.id,'approve')">Approve</button>
              <button v-if="p.status === 'active'" class="btn-primary bg-yellow-600 hover:bg-yellow-700 text-xs py-1 px-2" @click="approve(p.id,'suspend')">Suspend</button>
              <button v-if="p.status === 'suspended'" class="btn-primary bg-green-600 hover:bg-green-700 text-xs py-1 px-2" @click="approve(p.id,'reinstate')">Reactivate</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="p-10 text-center text-gray-400">No properties found.</div>
    </div>
    <p v-if="actionError" class="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg p-3">{{ actionError }}</p>
  </div>
</template>
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { propertiesApi, analyticsApi } from '@/api/services'
import { statusColor, reviewStateLabel } from '@/utils/formatters'
import LocationPicker from '@/components/public/LocationPicker.vue'
import AddressAutocomplete, { type PlaceSelection } from '@/components/public/AddressAutocomplete.vue'
import type { Property, User } from '@/types'

const properties = ref<Property[]>([]); const loading = ref(true); const statusFilter = ref('')
const actionError = ref('')
const filtered = computed(() => statusFilter.value ? properties.value.filter(p => p.status === statusFilter.value) : properties.value)

const showForm = ref(false); const saving = ref(false); const saveError = ref('')
const addressQuery = ref('')
const amenitiesInput = ref('')
const landlords = ref<User[]>([])
const landlordsLoading = ref(true)
const types = [{ value:'apartment',label:'Apartment'},{ value:'bungalow',label:'Bungalow'},{ value:'maisonette',label:'Maisonette'},{ value:'townhouse',label:'Townhouse'},{ value:'commercial',label:'Commercial'},{ value:'hostel',label:'Hostel'},{ value:'bedsitter',label:'Bedsitter'},{ value:'single_room',label:'Single Room'}]
const form = ref<{ landlord: string; name: string; property_type: string; county: string; town: string; estate: string; total_units: number; description: string; latitude?: number; longitude?: number }>({
  landlord: '', name:'', property_type:'apartment', county:'', town:'', estate:'', total_units:1, description:'',
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

async function loadLandlords() {
  landlordsLoading.value = true
  try {
    const { data } = await analyticsApi.users({ role: 'landlord' })
    landlords.value = (data as any).data?.results || (data as any).data || []
  } catch {
    landlords.value = []
  } finally {
    landlordsLoading.value = false
  }
}

async function load() {
  try { const { data } = await propertiesApi.list(); properties.value = data.data?.results || data.data || [] }
  catch (e: any) { properties.value = []; actionError.value = e?.response?.data?.error?.message || 'Failed to load properties.' }
  finally { loading.value = false }
}

async function save() {
  saving.value = true; saveError.value = ''
  try {
    const amenities = amenitiesInput.value.split(',').map((a) => a.trim()).filter(Boolean)
    await propertiesApi.create({ ...form.value, amenities } as any)
    showForm.value = false
    form.value = { landlord: '', name:'', property_type:'apartment', county:'', town:'', estate:'', total_units:1, description:'' }
    addressQuery.value = ''
    amenitiesInput.value = ''
    await load()
  } catch (e: any) {
    saveError.value = e?.response?.data?.error?.message
      || e?.response?.data?.error?.landlord?.[0]
      || 'Failed to create property.'
  } finally {
    saving.value = false
  }
}

async function approve(id: string, action: string) {
  actionError.value = ''
  try {
    const res: any = await propertiesApi.approve(id, action)
    // An admin approval alone does not publish a property that also needs the landlord's approval.
    const missing: string[] = res?.data?.data?.missing_approvals || []
    if (action === 'approve' && missing.length) actionError.value = `Your approval is recorded. Still waiting on: ${missing.join(', ')}.`
    await load()
  }
  catch (e: any) {
    actionError.value = e?.response?.status === 403
      ? "You don't have admin permission for this action. (Is your account's role actually set to admin?)"
      : e?.response?.data?.error?.message || e?.message || 'Action failed - please try again.'
  }
}
onMounted(() => { load(); loadLandlords() })
</script>
