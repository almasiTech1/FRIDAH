<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="page-title">Agency Staff</h1>
      <button class="btn-primary bg-agency-600 hover:bg-agency-700" @click="showInvite = !showInvite">+ Add Staff</button>
    </div>

    <div v-if="showInvite" class="card card-body space-y-4">
      <h2 class="section-title">Add a Staff Member</h2>
      <p class="text-xs text-gray-400">
        Nobody registers themselves. Enter their details and FRIDAH creates their login with a temporary password
        that you hand over and they must change at first login. If the email already has a FRIDAH account, they are
        invited instead.
      </p>
      <div class="grid grid-cols-2 gap-4">
        <div><label class="label" for="st-fn">First name</label><input id="st-fn" v-model="inviteForm.first_name" class="input"/></div>
        <div><label class="label" for="st-ln">Last name</label><input id="st-ln" v-model="inviteForm.last_name" class="input"/></div>
        <div><label class="label" for="st-email">Email</label><input id="st-email" v-model="inviteForm.email" type="email" class="input" placeholder="staff@example.com"/></div>
        <div><label class="label" for="st-phone">Phone</label><input id="st-phone" v-model="inviteForm.phone_number" class="input" placeholder="+2547XXXXXXXX"/></div>
        <div><label class="label">Role</label>
          <select v-model="inviteForm.role_id" class="input">
            <option value="" disabled>Select a role</option>
            <option v-for="r in roles" :key="r.id" :value="r.id">{{ r.name }}</option>
          </select>
        </div>
      </div>
      <div class="flex gap-3">
        <button class="btn-outline border-gray-200" @click="showInvite = false">Cancel</button>
        <button class="btn-primary bg-agency-600 hover:bg-agency-700" :disabled="inviting" @click="invite">
          <span v-if="inviting" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"/>
          <span v-else>Add staff member</span>
        </button>
      </div>
      <p v-if="inviteError" class="text-sm text-red-600">{{ inviteError }}</p>
    </div>

    <div v-if="credentials" class="rounded-xl border-2 border-amber-300 bg-amber-50 p-4 space-y-2" role="alert">
      <p class="font-semibold text-amber-900">Login for {{ credentials.name }} - copy it now</p>
      <p class="text-xs text-amber-800">Shown only once and cannot be retrieved later. Give it to them securely; they must change it at first
        login. If it is lost, use “Reset login” on their row.</p>
      <dl class="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
        <dt class="text-amber-700">Email</dt><dd class="font-mono">{{ credentials.login_email }}</dd>
        <dt class="text-amber-700">Temporary password</dt><dd class="font-mono font-bold select-all">{{ credentials.temporary_password }}</dd>
      </dl>
      <button class="btn-outline border-amber-300" @click="credentials = null">I have saved it - dismiss</button>
    </div>

    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="card animate-pulse h-16 bg-gray-100 rounded-xl"/>
    </div>
    <div v-else-if="members.length" class="space-y-3">
      <div v-for="m in members" :key="m.id" class="card card-body flex items-center gap-4">
        <div class="w-10 h-10 rounded-xl bg-agency-100 flex items-center justify-center text-agency-700 font-bold flex-shrink-0">
          {{ (m.user_name || m.user_email)[0]?.toUpperCase() }}
        </div>
        <div class="flex-1">
          <div class="flex items-center gap-3 flex-wrap">
            <p class="font-semibold text-gray-900">{{ m.user_name || m.user_email }}</p>
            <span :class="statusColor(m.status)" class="badge">{{ m.status }}</span>
          </div>
          <p class="text-xs text-gray-500 mt-0.5">{{ m.role_name }} · {{ m.user_email }}</p>
        </div>
        <button v-if="m.status === 'active' && m.role_name !== 'Agency Admin'" class="btn-outline border-gray-200 text-xs" @click="resetLogin(m)">Reset login</button>
        <button v-if="m.status === 'active'" class="btn-outline border-orange-200 text-orange-600 text-xs" @click="suspend(m.id)">Suspend</button>
        <button v-if="m.status !== 'removed'" class="btn-outline border-red-200 text-red-600 text-xs" @click="remove(m.id)">Remove</button>
      </div>
    </div>
    <div v-else class="card card-body text-center py-12 text-gray-400">No staff members yet.</div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { agencyApi } from '@/api/services'
import { statusColor } from '@/utils/formatters'
import { useAuthStore } from '@/stores/auth'
import type { AgencyMembership, AgencyRole } from '@/types'

const auth = useAuthStore()
const members = ref<AgencyMembership[]>([])
const roles = ref<AgencyRole[]>([])
const loading = ref(true)
const showInvite = ref(false)
const inviting = ref(false)
const inviteError = ref('')
const blankForm = () => ({ email: '', role_id: '', first_name: '', last_name: '', phone_number: '' })
const inviteForm = ref(blankForm())
const credentials = ref<{ name: string; login_email: string; temporary_password: string } | null>(null)

function agencyId() { return auth.agencies[0]?.id }

async function load() {
  loading.value = true
  try {
    if (!auth.agencies.length) await auth.fetchAgencies()
    const id = agencyId()
    if (!id) { members.value = []; roles.value = []; return }
    const [mRes, rRes] = await Promise.all([agencyApi.members(id), agencyApi.roles(id)])
    members.value = (mRes.data as any).data?.results || (mRes.data as any).data || []
    roles.value = (rRes.data as any).data?.results || (rRes.data as any).data || []
  } finally {
    loading.value = false
  }
}

async function invite() {
  inviting.value = true; inviteError.value = ''
  try {
    const id = agencyId()
    if (!id) throw new Error('No agency')
    const f = inviteForm.value
    const res: any = await agencyApi.inviteMember(id, f.email, f.role_id, {
      first_name: f.first_name, last_name: f.last_name, phone_number: f.phone_number,
    })
    const c = res?.data?.data?.credentials
    if (c) credentials.value = { name: `${f.first_name} ${f.last_name}`.trim(), login_email: c.login_email, temporary_password: c.temporary_password }
    showInvite.value = false
    inviteForm.value = blankForm()
    await load()
  } catch (e: any) {
    const d = e?.response?.data
    const fields = d && typeof d === 'object' && !d.error ? Object.values(d).flat().join(' ') : ''
    inviteError.value = d?.error?.message || fields || 'Failed to add the staff member.'
  } finally {
    inviting.value = false
  }
}

async function resetLogin(m: any) {
  if (!confirm(`Issue a new temporary password to ${m.user_name || m.user_email}? Their current password stops working.`)) return
  try {
    const res: any = await agencyApi.resetStaffPassword(m.id)
    const c = res?.data?.data
    credentials.value = { name: m.user_name || m.user_email, login_email: c.login_email, temporary_password: c.temporary_password }
  } catch (e: any) { inviteError.value = e?.response?.data?.error?.message || 'Could not reset the login.' }
}

async function suspend(id: string) {
  await agencyApi.suspendMember(id)
  await load()
}
async function remove(id: string) {
  if (!confirm('Remove this staff member from the agency?')) return
  await agencyApi.removeMember(id)
  await load()
}

onMounted(load)
</script>
