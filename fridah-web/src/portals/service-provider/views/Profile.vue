<template>
  <div class="space-y-5 max-w-2xl">
    <h1 class="page-title">Provider Profile</h1>
    <div class="card card-body space-y-4">
      <h2 class="section-title">Account</h2>
      <div class="flex items-center gap-4">
        <div class="w-16 h-16 rounded-full bg-provider-100 flex items-center justify-center text-provider-700 text-2xl font-bold">
          {{ initials }}
        </div>
        <div>
          <p class="font-semibold text-gray-900">{{ auth.user?.first_name }} {{ auth.user?.last_name }}</p>
          <p class="text-sm text-gray-500">{{ auth.user?.email }}</p>
          <span :class="auth.isKycVerified ? 'badge-green' : 'badge-yellow'" class="badge mt-1">{{ auth.user?.kyc_status }}</span>
        </div>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div><label class="label">First name</label><input v-model="form.first_name" class="input"/></div>
        <div><label class="label">Last name</label><input v-model="form.last_name" class="input"/></div>
        <div><label class="label">County</label><input v-model="form.county" class="input" placeholder="Nairobi"/></div>
        <div><label class="label">Town</label><input v-model="form.town" class="input" placeholder="Westlands"/></div>
      </div>
      <button class="btn-primary bg-provider-600 hover:bg-provider-700" :disabled="saving" @click="save">
        <span v-if="saving" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"/>
        <span v-else>Save</span>
      </button>
      <p v-if="saved" class="text-sm text-green-600">✓ Saved</p>
    </div>
    <div class="card card-body space-y-4">
      <h2 class="section-title">Provider Details</h2>
      <div><label class="label">Bio / About</label><textarea v-model="providerForm.bio" class="input resize-none" rows="3" placeholder="Describe your experience and skills…"/></div>
      <div class="grid grid-cols-2 gap-4">
        <div><label class="label">Years Experience</label><input v-model.number="providerForm.years_experience" class="input" type="number" min="0"/></div>
        <div class="flex items-end gap-2 pb-1">
          <label class="flex items-center gap-2 cursor-pointer">
            <input v-model="providerForm.is_available" type="checkbox" class="w-4 h-4 accent-provider-600"/>
            <span class="text-sm font-medium text-gray-700">Available for work</span>
          </label>
        </div>
      </div>
      <button class="btn-primary bg-provider-600 hover:bg-provider-700" :disabled="savingProfile" @click="saveProvider">
        <span v-if="savingProfile" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"/>
        <span v-else>Update Profile</span>
      </button>
      <p v-if="providerSaved" class="text-sm text-green-600">✓ Profile updated</p>
    </div>
    <NotificationPreferences />
  </div>
</template>
<script setup lang="ts">
import NotificationPreferences from '@/components/common/NotificationPreferences.vue'
import { reactive, ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { authApi, servicesApi } from '@/api/services'
const auth = useAuthStore()
const form = reactive({ first_name: '', last_name: '', county: '', town: '' })
const providerForm = reactive({ bio: '', years_experience: 0, is_available: true })
const saving = ref(false); const saved = ref(false)
const savingProfile = ref(false); const providerSaved = ref(false)
const initials = computed(() => ((auth.user?.first_name?.[0] || '') + (auth.user?.last_name?.[0] || '')).toUpperCase() || '?')
onMounted(async () => {
  if (auth.user) { form.first_name = auth.user.first_name; form.last_name = auth.user.last_name; form.county = auth.user.county || ''; form.town = auth.user.town || '' }
  try { const { data } = await servicesApi.providerProfile(); Object.assign(providerForm, { bio: data.data.bio, years_experience: data.data.years_experience, is_available: data.data.is_available }) } catch (e) { console.error('Failed to load provider profile:', e) }
})
async function save() { saving.value = true; try { await authApi.updateProfile(form); await auth.fetchMe(); saved.value = true; setTimeout(() => saved.value = false, 2000) } finally { saving.value = false } }
async function saveProvider() { savingProfile.value = true; try { await servicesApi.updateProviderProfile(providerForm); providerSaved.value = true; setTimeout(() => providerSaved.value = false, 2000) } finally { savingProfile.value = false } }
</script>
