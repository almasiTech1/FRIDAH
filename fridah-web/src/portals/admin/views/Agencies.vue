<template>
  <div class="space-y-5">
    <div class="flex items-start justify-between flex-wrap gap-3">
      <div>
        <h1 class="page-title">Agencies</h1>
        <p class="text-sm text-gray-500 mt-0.5">
          Only administrators can register an agency company. Tenants, landlords, service providers and hotel owners cannot create one.
        </p>
      </div>
      <button class="btn bg-gray-900 text-white" @click="showForm = !showForm">{{ showForm ? 'Close' : '+ Register agency' }}</button>
    </div>

    <form v-if="showForm" class="card card-body space-y-4" @submit.prevent="register">
      <h2 class="font-semibold text-gray-900">Register an agency company</h2>

      <fieldset class="rounded-lg bg-blue-50 border border-blue-100 p-3 space-y-3">
        <legend class="text-sm font-medium text-blue-900 px-1">Agency admin - you create their login</legend>
        <p class="text-xs text-blue-800">
          This person becomes the agency's first Agency Admin and invites their own team. Nobody registers an agency
          themselves: FRIDAH creates the account here with a temporary password that you hand over and that they must
          change at first login.
        </p>
        <div class="grid md:grid-cols-2 gap-3">
          <div><label class="text-xs font-medium text-blue-900" for="ag-fn">First name <span class="text-red-600">*</span></label>
            <input id="ag-fn" v-model="form.admin_first_name" class="input" required autocomplete="off" />
            <p v-if="fieldErrors.admin_first_name" class="text-xs text-red-600" role="alert">{{ fieldErrors.admin_first_name }}</p></div>
          <div><label class="text-xs font-medium text-blue-900" for="ag-ln">Last name <span class="text-red-600">*</span></label>
            <input id="ag-ln" v-model="form.admin_last_name" class="input" required autocomplete="off" />
            <p v-if="fieldErrors.admin_last_name" class="text-xs text-red-600" role="alert">{{ fieldErrors.admin_last_name }}</p></div>
          <div><label class="text-xs font-medium text-blue-900" for="ag-admin">Login email <span class="text-red-600">*</span></label>
            <input id="ag-admin" v-model="form.admin_email" type="email" class="input" required autocomplete="off" placeholder="person@agency.co.ke" />
            <p v-if="fieldErrors.admin_email" class="text-xs text-red-600" role="alert">{{ fieldErrors.admin_email }}</p></div>
          <div><label class="text-xs font-medium text-blue-900" for="ag-aphone">Phone <span class="text-red-600">*</span></label>
            <input id="ag-aphone" v-model="form.admin_phone_number" class="input" required autocomplete="off" placeholder="+2547XXXXXXXX" />
            <p v-if="fieldErrors.admin_phone_number" class="text-xs text-red-600" role="alert">{{ fieldErrors.admin_phone_number }}</p></div>
        </div>
      </fieldset>

      <div class="grid md:grid-cols-3 gap-3">
        <div class="md:col-span-2"><label class="text-xs font-medium text-gray-600" for="ag-name">Agency name <span class="text-red-600">*</span></label>
          <input id="ag-name" v-model="form.name" class="input" required maxlength="200" placeholder="Prime Property Managers" />
          <p v-if="fieldErrors.name" class="text-xs text-red-600" role="alert">{{ fieldErrors.name }}</p></div>
        <div><label class="text-xs font-medium text-gray-600" for="ag-fee">Default management fee (%)</label>
          <input id="ag-fee" v-model.number="form.default_fee_percent" type="number" min="0" max="100" step="0.1" class="input" /></div>
        <div><label class="text-xs font-medium text-gray-600" for="ag-email">Agency email</label>
          <input id="ag-email" v-model="form.email" type="email" class="input" placeholder="ops@agency.co.ke" /></div>
        <div><label class="text-xs font-medium text-gray-600" for="ag-phone">Phone</label>
          <input id="ag-phone" v-model="form.phone_number" class="input" placeholder="+2547XXXXXXXX" />
          <p v-if="fieldErrors.phone_number" class="text-xs text-red-600" role="alert">{{ fieldErrors.phone_number }}</p></div>
        <div><label class="text-xs font-medium text-gray-600" for="ag-reg">Registration number</label>
          <input id="ag-reg" v-model="form.registration_number" class="input" /></div>
        <div><label class="text-xs font-medium text-gray-600" for="ag-kra">KRA PIN</label>
          <input id="ag-kra" v-model="form.kra_pin" class="input" /></div>
        <div><label class="text-xs font-medium text-gray-600" for="ag-county">County</label>
          <input id="ag-county" v-model="form.county" class="input" placeholder="Nairobi" /></div>
        <div><label class="text-xs font-medium text-gray-600" for="ag-town">Town</label>
          <input id="ag-town" v-model="form.town" class="input" placeholder="Westlands" /></div>
      </div>

      <p v-if="formError" class="text-sm text-red-600" role="alert">{{ formError }}</p>
      <div class="flex gap-2">
        <button class="btn bg-gray-900 text-white" :disabled="saving">{{ saving ? 'Registering…' : 'Register agency' }}</button>
        <button type="button" class="btn-outline border-gray-200" @click="showForm = false">Cancel</button>
      </div>
    </form>

    <p v-if="notice" class="text-sm text-emerald-700" role="status">{{ notice }}</p>
    <p v-if="formError && !showForm" class="text-sm text-red-600" role="alert">{{ formError }}</p>

    <!-- One-time credentials: shown once, never retrievable again -->
    <div v-if="credentials" class="rounded-xl border-2 border-amber-300 bg-amber-50 p-4 space-y-2" role="alert">
      <p class="font-semibold text-amber-900">Login for {{ credentials.agency }} - copy it now</p>
      <p class="text-xs text-amber-800">This temporary password is shown only once and cannot be retrieved later. Give it to the agency admin
        securely (not in a group chat). They must change it at first login. If it is lost, use “Reset login”.</p>
      <dl class="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
        <dt class="text-amber-700">Email</dt><dd class="font-mono">{{ credentials.login_email }}</dd>
        <dt class="text-amber-700">Temporary password</dt><dd class="font-mono font-bold select-all">{{ credentials.temporary_password }}</dd>
      </dl>
      <div class="flex gap-2">
        <button class="btn bg-amber-600 text-white" @click="copyCredentials">{{ copied ? 'Copied ✓' : 'Copy details' }}</button>
        <button class="btn-outline border-amber-300" @click="credentials = null">I have saved it - dismiss</button>
      </div>
    </div>

    <div class="card overflow-x-auto">
      <div v-if="loading" class="p-8 text-center text-gray-400" aria-busy="true">Loading…</div>
      <table v-else-if="agencies.length" class="w-full">
        <thead class="bg-gray-50 border-b"><tr>
          <th class="table-th">Agency</th><th class="table-th">Location</th><th class="table-th">Properties</th>
          <th class="table-th">Status</th><th class="table-th">Registered</th><th class="table-th"><span class="sr-only">Actions</span></th>
        </tr></thead>
        <tbody>
          <tr v-for="a in agencies" :key="a.id" class="table-tr">
            <td class="table-td"><p class="font-medium text-gray-900">{{ a.name }}</p><p class="text-xs text-gray-400">{{ a.email }}</p></td>
            <td class="table-td text-sm">{{ [a.town, a.county].filter(Boolean).join(', ') || '—' }}</td>
            <td class="table-td text-sm">{{ a.managed_properties_count ?? 0 }}</td>
            <td class="table-td"><span class="badge" :class="statusColor(a.status)">{{ a.status.replace('_', ' ') }}</span></td>
            <td class="table-td text-xs">{{ formatDate(a.created_at) }}</td>
            <td class="table-td text-right">
              <button class="btn-outline border-gray-200 text-xs mr-1" :disabled="busy === a.id" @click="resetLogin(a)">Reset login</button>
              <button v-if="a.status !== 'active'" class="btn-outline border-emerald-200 text-emerald-700 text-xs" :disabled="busy === a.id" @click="setStatus(a, 'active')">Activate</button>
              <button v-else class="btn-outline border-red-200 text-red-600 text-xs" :disabled="busy === a.id" @click="confirmSuspend(a)">Suspend</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="p-10 text-center text-gray-400">No agencies registered yet.</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { agencyApi } from '@/api/services'
import { statusColor, formatDate } from '@/utils/formatters'

const agencies = ref<any[]>([])
const loading = ref(true)
const showForm = ref(false)
const saving = ref(false)
const busy = ref<string | null>(null)
const formError = ref('')
const notice = ref('')
const fieldErrors = ref<Record<string, string>>({})
const blank = () => ({
  admin_first_name: '', admin_last_name: '', admin_email: '', admin_phone_number: '', name: '', default_fee_percent: 5, email: '', phone_number: '',
  registration_number: '', kra_pin: '', county: '', town: '',
})
const credentials = ref<{ agency: string; login_email: string; temporary_password: string } | null>(null)
const copied = ref(false)
const form = ref(blank())

async function load() {
  loading.value = true
  try {
    const { data } = await agencyApi.list()
    agencies.value = (data as any).results || (data as any).data?.results || (data as any).data || []
  } catch { agencies.value = [] } finally { loading.value = false }
}

async function register() {
  saving.value = true; formError.value = ''; fieldErrors.value = {}; notice.value = ''
  try {
    const res: any = await agencyApi.create({ ...form.value })
    const c = res?.data?.data?.credentials
    if (c) credentials.value = { agency: form.value.name, login_email: c.login_email, temporary_password: c.temporary_password }
    notice.value = `${form.value.name} registered.`
    form.value = blank(); showForm.value = false
    await load()
  } catch (e: any) {
    const d = e?.response?.data
    if (d && typeof d === 'object' && !d.error) {
      // DRF field errors: { admin_email: ['…'], name: ['…'] }
      fieldErrors.value = Object.fromEntries(Object.entries(d).map(([k, v]) => [k, Array.isArray(v) ? v.join(' ') : String(v)]))
      formError.value = Object.keys(fieldErrors.value).some((k) => !['admin_email', 'admin_first_name', 'admin_last_name', 'admin_phone_number', 'name', 'phone_number'].includes(k))
        ? Object.values(fieldErrors.value).join(' ') : ''
    } else {
      formError.value = d?.error?.message || d?.detail || 'Could not register the agency.'
    }
  } finally { saving.value = false }
}

async function resetLogin(a: any) {
  if (!window.confirm(`Issue a new temporary password to the Agency Admin of ${a.name}? Their current password stops working.`)) return
  busy.value = a.id; formError.value = ''
  try {
    const res: any = await agencyApi.resetAdminPassword(a.id)
    const c = res?.data?.data
    credentials.value = { agency: a.name, login_email: c.login_email, temporary_password: c.temporary_password }
  } catch (e: any) { formError.value = e?.response?.data?.error?.message || 'Could not reset the login.' }
  finally { busy.value = null }
}
async function copyCredentials() {
  if (!credentials.value) return
  const text = `FRIDAH agency login\nEmail: ${credentials.value.login_email}\nTemporary password: ${credentials.value.temporary_password}`
  try { await navigator.clipboard.writeText(text); copied.value = true; setTimeout(() => (copied.value = false), 2000) } catch {}
}

async function setStatus(a: any, status: 'active' | 'suspended') {
  busy.value = a.id; notice.value = ''
  try { await agencyApi.setStatus(a.id, status); notice.value = `${a.name} is now ${status}.`; await load() }
  catch { notice.value = '' ; formError.value = 'Could not change the agency status.' }
  finally { busy.value = null }
}
function confirmSuspend(a: any) {
  if (window.confirm(`Suspend ${a.name}? It will disappear from the agency directory.`)) setStatus(a, 'suspended')
}

onMounted(load)
</script>
