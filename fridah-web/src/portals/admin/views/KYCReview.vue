<template>
  <div class="space-y-5">
    <h1 class="page-title">KYC Review</h1>
    <div v-if="loading" class="text-center py-10 text-gray-400">Loading…</div>
    <div v-else-if="!pending.length" class="card card-body text-center py-12 text-green-700">
      <p class="text-2xl mb-2">✅</p><p class="font-medium">All KYC submissions reviewed!</p>
    </div>
    <div v-else class="space-y-4">
      <p class="text-sm text-gray-500">{{ pending.length }} submission(s) awaiting review</p>
      <div v-for="u in pending" :key="u.id" class="card card-body space-y-3">
        <div class="flex items-start justify-between gap-3 flex-wrap">
          <div>
            <p class="font-semibold text-gray-900">{{ u.first_name }} {{ u.last_name }}</p>
            <p class="text-xs text-gray-500">{{ u.email }} · {{ u.phone_number }}</p>
            <p class="text-xs text-gray-400 mt-0.5">Role: <span class="capitalize">{{ u.role.replace('_',' ') }}</span></p>
          </div>
          <div class="flex gap-2 flex-wrap">
            <button class="btn-primary bg-green-600 hover:bg-green-700 text-sm" @click="review(u.id, 'approve')">✓ Approve</button>
            <button class="btn-primary bg-red-600 hover:bg-red-700 text-sm" @click="openReject(u.id)">✕ Reject</button>
          </div>
        </div>
        <div v-if="rejecting === u.id" class="pt-2 border-t border-gray-50 space-y-2">
          <label class="label">Rejection reason</label>
          <input v-model="rejectReason" class="input" placeholder="e.g. Document unclear or expired"/>
          <div class="flex gap-2">
            <button class="btn-outline border-gray-200 text-sm" @click="rejecting = ''">Cancel</button>
            <button class="btn-primary bg-red-600 hover:bg-red-700 text-sm" @click="review(u.id, 'reject')">Confirm Reject</button>
          </div>
        </div>
      </div>
    </div>
    <p v-if="actionError" class="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg p-3">{{ actionError }}</p>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { analyticsApi } from '@/api/services'
import type { User } from '@/types'
const pending = ref<User[]>([]); const loading = ref(true)
const rejecting = ref(''); const rejectReason = ref('')
const actionError = ref('')
async function load() {
  try { const { data } = await analyticsApi.kycPending(); pending.value = data.data?.results || data.data || [] }
  catch (e: any) { pending.value = []; actionError.value = e?.response?.data?.error?.message || 'Failed to load KYC submissions.' }
  finally { loading.value = false }
}
function openReject(id: string) { rejecting.value = id; rejectReason.value = '' }
async function review(userId: string, action: 'approve' | 'reject') {
  actionError.value = ''
  try { await analyticsApi.reviewKyc(userId, action, action === 'reject' ? rejectReason.value : undefined); rejecting.value = ''; await load() }
  catch (e: any) {
    actionError.value = e?.response?.status === 403
      ? "You don't have admin permission for this action. (Is your account's role actually set to admin?)"
      : e?.response?.data?.error?.message || e?.message || 'Action failed - please try again.'
  }
}
onMounted(load)
</script>
