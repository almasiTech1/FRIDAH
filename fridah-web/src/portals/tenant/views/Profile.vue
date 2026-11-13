<template>
  <div class="space-y-5 max-w-2xl">
    <h1 class="page-title">Profile & KYC</h1>
    <!-- KYC Status Banner -->
    <div :class="kycBanner.bg" class="rounded-xl p-4 flex items-start gap-3">
      <span class="text-xl">{{ kycBanner.icon }}</span>
      <div>
        <p :class="kycBanner.text" class="font-medium text-sm">{{ kycBanner.title }}</p>
        <p :class="kycBanner.subtext" class="text-xs mt-0.5">{{ kycBanner.sub }}</p>
      </div>
    </div>
    <!-- Profile form -->
    <div class="card card-body space-y-4">
      <h2 class="section-title">Personal Information</h2>
      <div class="grid grid-cols-2 gap-4">
        <div><label class="label">First name</label><input v-model="form.first_name" class="input" /></div>
        <div><label class="label">Last name</label><input v-model="form.last_name" class="input" /></div>
      </div>
      <div><label class="label">Email</label><input :value="auth.user?.email" class="input bg-gray-50" readonly /></div>
      <div><label class="label">Phone</label><input :value="auth.user?.phone_number" class="input bg-gray-50" readonly /></div>
      <div class="grid grid-cols-2 gap-4">
        <div><label class="label">County</label><input v-model="form.county" class="input" placeholder="e.g. Nairobi"/></div>
        <div><label class="label">Town</label><input v-model="form.town" class="input" placeholder="e.g. Westlands"/></div>
      </div>
      <div class="flex gap-3 pt-2">
        <button class="btn-primary bg-tenant-600 hover:bg-tenant-700" :disabled="saving" @click="saveProfile">
          <span v-if="saving" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"/>
          <span v-else>Save changes</span>
        </button>
        <p v-if="saved" class="text-sm text-green-600 self-center">✓ Saved</p>
      </div>
    </div>
    <!-- KYC Upload -->
    <div v-if="auth.user?.kyc_status !== 'verified'" class="card card-body space-y-4">
      <h2 class="section-title">KYC Verification</h2>
      <p class="text-sm text-gray-500">Upload your National ID to unlock full platform access.</p>
      <div><label class="label">National ID Number</label><input v-model="kycForm.national_id" class="input" placeholder="Enter ID number"/></div>
      <div>
        <label class="label">ID Document (front/back, max 5MB)</label>
        <input type="file" accept="image/*,application/pdf" class="input py-2 text-sm" @change="onFile"/>
      </div>
      <button class="btn-primary bg-tenant-600 hover:bg-tenant-700" :disabled="submittingKyc" @click="submitKyc">
        <span v-if="submittingKyc" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"/>
        <span v-else>Submit for Review</span>
      </button>
      <p v-if="kycError" class="text-sm text-red-600">{{ kycError }}</p>
      <p v-if="kycDone" class="text-sm text-green-600">✓ KYC submitted — under review</p>
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
const form = reactive({ first_name: '', last_name: '', county: '', town: '' })
const saving = ref(false); const saved = ref(false)
const kycForm = reactive({ national_id: '' }); let kycFile: File | null = null
const submittingKyc = ref(false); const kycError = ref(''); const kycDone = ref(false)
const kycBanner = computed(() => {
  const s = auth.user?.kyc_status
  if (s === 'verified') return { bg:'bg-green-50', icon:'✅', text:'text-green-800', subtext:'text-green-700', title:'KYC Verified', sub:'Your identity has been verified.' }
  if (s === 'pending')  return { bg:'bg-yellow-50', icon:'🕐', text:'text-yellow-800', subtext:'text-yellow-700', title:'KYC Under Review', sub:'We are reviewing your documents.' }
  if (s === 'rejected') return { bg:'bg-red-50', icon:'❌', text:'text-red-800', subtext:'text-red-700', title:'KYC Rejected', sub:'Please resubmit your documents.' }
  return { bg:'bg-blue-50', icon:'🔒', text:'text-blue-800', subtext:'text-blue-700', title:'Verify Your Identity', sub:'Submit your National ID to unlock all features.' }
})
onMounted(() => { if (auth.user) { form.first_name = auth.user.first_name; form.last_name = auth.user.last_name; form.county = auth.user.county || ''; form.town = auth.user.town || '' } })
async function saveProfile() { saving.value = true; saved.value = false; try { await authApi.updateProfile(form); await auth.fetchMe(); saved.value = true; setTimeout(() => saved.value = false, 2000) } finally { saving.value = false } }
function onFile(e: Event) { kycFile = (e.target as HTMLInputElement).files?.[0] || null }
async function submitKyc() {
  if (!kycForm.national_id || !kycFile) { kycError.value = 'Please fill in ID number and upload document.'; return }
  submittingKyc.value = true; kycError.value = ''
  try { const fd = new FormData(); fd.append('national_id', kycForm.national_id); fd.append('kyc_document', kycFile); await authApi.submitKyc(fd); kycDone.value = true; await auth.fetchMe() }
  catch (e: any) { kycError.value = e?.response?.data?.error?.message || 'Submission failed.' }
  finally { submittingKyc.value = false }
}
</script>
