<template>
  <div class="space-y-5 max-w-2xl">
    <h1 class="page-title">Profile</h1>
    <div class="card card-body space-y-4">
      <div class="flex items-center gap-4">
        <div class="w-16 h-16 rounded-full bg-agency-100 flex items-center justify-center text-agency-700 text-2xl font-bold">
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
      <button class="btn-primary bg-agency-600 hover:bg-agency-700" :disabled="saving" @click="save">
        <span v-if="saving" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"/>
        <span v-else>Save</span>
      </button>
      <p v-if="saved" class="text-sm text-green-600">✓ Saved</p>
    </div>

    <div v-if="auth.agencies.length" class="card card-body space-y-2">
      <h2 class="section-title">Your Agencies</h2>
      <div v-for="a in auth.agencies" :key="a.id" class="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
        <div>
          <p class="font-semibold text-gray-800 text-sm">{{ a.name }}</p>
          <p class="text-xs text-gray-400">{{ a.managed_properties_count }} properties · {{ a.owners_count }} owners</p>
        </div>
        <span :class="a.status === 'active' ? 'badge-green' : 'badge-yellow'" class="badge">{{ a.status }}</span>
      </div>
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
const initials = computed(() => ((auth.user?.first_name?.[0] || '') + (auth.user?.last_name?.[0] || '')).toUpperCase() || '?')
onMounted(() => { if (auth.user) { form.first_name = auth.user.first_name; form.last_name = auth.user.last_name; form.county = auth.user.county || ''; form.town = auth.user.town || '' } })
async function save() { saving.value = true; try { await authApi.updateProfile(form); await auth.fetchMe(); saved.value = true; setTimeout(() => saved.value = false, 2000) } finally { saving.value = false } }
</script>
