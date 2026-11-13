<template>
  <div class="space-y-5 max-w-2xl">
    <h1 class="page-title">Profile</h1>
    <div class="card card-body space-y-4">
      <div class="flex items-center gap-4">
        <div class="w-16 h-16 rounded-full bg-landlord-100 flex items-center justify-center text-landlord-700 text-2xl font-bold">
          {{ initials }}
        </div>
        <div>
          <p class="font-semibold text-gray-900">{{ auth.user?.first_name }} {{ auth.user?.last_name }}</p>
          <p class="text-sm text-gray-500">{{ auth.user?.email }}</p>
          <span :class="auth.isKycVerified ? 'badge-green' : 'badge-yellow'" class="badge mt-1">{{ auth.user?.kyc_status }}</span>
        </div>
      </div>
      <div class="grid grid-cols-2 gap-4 pt-2 border-t border-gray-50">
        <div><label class="label">First name</label><input v-model="form.first_name" class="input"/></div>
        <div><label class="label">Last name</label><input v-model="form.last_name" class="input"/></div>
        <div><label class="label">County</label><input v-model="form.county" class="input"/></div>
        <div><label class="label">Town</label><input v-model="form.town" class="input"/></div>
      </div>
      <button class="btn-primary bg-landlord-600 hover:bg-landlord-700" :disabled="saving" @click="save">
        <span v-if="saving" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"/>
        <span v-else>Save</span>
      </button>
      <p v-if="saved" class="text-sm text-green-600">✓ Saved</p>
    </div>
    <div v-if="!auth.isKycVerified" class="card card-body space-y-4">
      <h2 class="section-title">KYC Verification</h2>
      <div><label class="label">National ID</label><input v-model="kycId" class="input"/></div>
      <div><label class="label">ID Document</label><input type="file" class="input py-2 text-sm" @change="(e) => kycFile = (e.target as HTMLInputElement).files?.[0]"/></div>
      <button class="btn-primary bg-landlord-600 hover:bg-landlord-700" :disabled="kycLoading" @click="submitKyc">Submit KYC</button>
      <p v-if="kycMsg" class="text-sm text-green-600">{{ kycMsg }}</p>
    </div>
    <NotificationPreferences />
  </div>
</template>
<script setup lang="ts">
import NotificationPreferences from '@/components/common/NotificationPreferences.vue'
import { reactive, ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api/services'
const auth = useAuthStore()
const form = reactive({ first_name:'', last_name:'', county:'', town:'' })
const saving = ref(false); const saved = ref(false)
const kycId = ref(''); let kycFile: any = null; const kycLoading = ref(false); const kycMsg = ref('')
const initials = computed(() => ((auth.user?.first_name?.[0] || '') + (auth.user?.last_name?.[0] || '')).toUpperCase() || '?')
onMounted(() => { if (auth.user) { form.first_name = auth.user.first_name; form.last_name = auth.user.last_name; form.county = auth.user.county || ''; form.town = auth.user.town || '' } })
async function save() { saving.value = true; try { await authApi.updateProfile(form); await auth.fetchMe(); saved.value = true; setTimeout(() => saved.value = false, 2000) } finally { saving.value = false } }
async function submitKyc() {
  if (!kycId.value || !kycFile) return
  kycLoading.value = true
  try { const fd = new FormData(); fd.append('national_id', kycId.value); fd.append('kyc_document', kycFile!); await authApi.submitKyc(fd); kycMsg.value = '✓ Submitted for review'; await auth.fetchMe() }
  finally { kycLoading.value = false }
}
</script>
