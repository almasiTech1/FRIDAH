<template>
  <div class="space-y-4">
    <div class="flex gap-2 flex-wrap" role="group" aria-label="Filter by status">
      <button v-for="f in filters" :key="f.value" class="btn-outline text-xs" :class="status === f.value ? 'border-gray-900 font-semibold' : 'border-gray-200'"
              @click="status = f.value; load()">{{ f.label }}</button>
    </div>

    <div v-if="loading" class="space-y-3" aria-busy="true"><div v-for="i in 2" :key="i" class="card animate-pulse h-24 bg-gray-100 rounded-xl" /></div>
    <div v-else-if="error" class="card card-body text-center text-red-600" role="alert">{{ error }}</div>
    <div v-else-if="!items.length" class="card card-body text-center py-12 text-gray-400">No refund requests.</div>

    <div v-else class="space-y-3 stagger">
      <div v-for="r in items" :key="r.id" class="card card-body">
        <div class="flex items-start justify-between flex-wrap gap-3">
          <div>
            <div class="flex items-center gap-2 flex-wrap">
              <p class="font-semibold text-gray-900">{{ formatKES(r.amount) }} · {{ r.kind === 'reversal' ? 'Reversal' : 'Refund' }}</p>
              <span class="badge" :class="statusColor(r.status)">{{ refundStatusLabel(r.status) }}</span>
              <span v-if="r.status === 'requested' && r.approval_level === 'admin'" class="badge badge-gray">Admin approval needed</span>
            </div>
            <p class="text-xs text-gray-500 mt-0.5">
              Payment <span class="font-mono">{{ r.payment_reference }}</span> ({{ formatKES(r.payment_amount) }})
              · requested by {{ r.requested_by_name || '—' }} · {{ formatDate(r.created_at) }}
            </p>
            <p class="text-sm text-gray-700 mt-1">“{{ r.reason }}”</p>
            <p v-if="r.decision_comment" class="text-xs text-gray-500 mt-1">{{ r.decided_by_name }}: {{ r.decision_comment }}</p>
            <p v-if="r.payout_reference" class="text-xs text-emerald-700 mt-1">Paid out · ref {{ r.payout_reference }}</p>
          </div>

          <div class="flex gap-2 flex-wrap items-center">
            <template v-if="r.can_decide">
              <button class="btn bg-emerald-600 text-white" :disabled="busy === r.id" @click="approve(r)">Approve</button>
              <button class="btn-outline border-red-200 text-red-600" :disabled="busy === r.id" @click="startReject(r.id)">Reject</button>
            </template>
            <button v-if="r.status === 'requested' && mine(r)" class="btn-outline border-gray-200" :disabled="busy === r.id" @click="cancel(r)">Cancel</button>
            <button v-if="role === 'admin' && r.status === 'approved' && r.auto_payout_available && r.payout_status !== 'processing'"
                    class="btn bg-emerald-600 text-white" :disabled="busy === r.id" @click="sendMpesa(r)">Send via M-Pesa</button>
            <span v-if="r.payout_status === 'processing'" class="badge badge-yellow">M-Pesa payout processing…</span>
            <button v-if="role === 'admin' && r.status === 'approved'" class="btn-outline border-emerald-200 text-emerald-700" @click="startPay(r.id)">Record payout manually</button>
          </div>
        </div>

        <label v-if="negativeOffer === r.id" class="mt-3 flex items-start gap-2 text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg p-3">
          <input v-model="allowNegative" type="checkbox" class="mt-1" />
          <span>The recipient has already withdrawn this money. Approve anyway and let their wallet go negative (recovered from future earnings)?
            <button type="button" class="underline ml-1" @click="approve(r, true)">Approve with negative balance</button></span>
        </label>

        <form v-if="rejecting === r.id" class="mt-3 flex gap-2" @submit.prevent="reject(r)">
          <label class="sr-only" :for="`rj-${r.id}`">Reason</label>
          <input :id="`rj-${r.id}`" v-model="text" class="input flex-1" required placeholder="Reason for rejecting (required)" />
          <button class="btn bg-gray-900 text-white" :disabled="!text.trim()">Send</button>
          <button type="button" class="btn-outline border-gray-200" @click="rejecting = null">Cancel</button>
        </form>
        <form v-if="paying === r.id" class="mt-3 flex gap-2" @submit.prevent="markPaid(r)">
          <label class="sr-only" :for="`pr-${r.id}`">M-Pesa reference</label>
          <input :id="`pr-${r.id}`" v-model="text" class="input flex-1" required minlength="6" placeholder="M-Pesa reference of the payout to the customer" />
          <button class="btn bg-gray-900 text-white" :disabled="text.trim().length < 6">Save</button>
          <button type="button" class="btn-outline border-gray-200" @click="paying = null">Cancel</button>
        </form>
        <p v-if="actionError[r.id]" class="text-sm text-red-600 mt-2" role="alert">{{ actionError[r.id] }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { refundApi } from '@/api/services'
import { useAuthStore } from '@/stores/auth'
import { statusColor, formatKES, formatDate, refundStatusLabel } from '@/utils/formatters'

const props = defineProps<{ role: 'admin' | 'landlord' | 'tenant' }>()
const auth = useAuthStore()

const filters = [
  { value: '', label: 'All' }, { value: 'requested', label: 'Awaiting approval' },
  { value: 'approved', label: 'Payout pending' }, { value: 'paid_out', label: 'Paid out' },
]
const status = ref('')
const items = ref<any[]>([])
const loading = ref(true)
const error = ref('')
const busy = ref<string | null>(null)
const rejecting = ref<string | null>(null)
const paying = ref<string | null>(null)
const negativeOffer = ref<string | null>(null)
const allowNegative = ref(false)
const text = ref('')
const actionError = ref<Record<string, string>>({})

const mine = (r: any) => r.requested_by === auth.user?.id

async function load() {
  loading.value = true; error.value = ''
  try {
    const res: any = await refundApi.list(status.value ? { status: status.value } : {})
    items.value = res.data?.data?.results || res.data?.results || []
  } catch { error.value = 'Could not load refund requests.' } finally { loading.value = false }
}

async function run(r: any, fn: () => Promise<any>) {
  busy.value = r.id; actionError.value = { ...actionError.value, [r.id]: '' }
  try { await fn(); rejecting.value = null; paying.value = null; negativeOffer.value = null; await load() }
  catch (e: any) {
    const msg = e?.response?.data?.error?.message || e?.response?.data?.detail || 'That action failed.'
    actionError.value = { ...actionError.value, [r.id]: msg }
    // Offer the admin override only for the "already withdrawn" case.
    if (props.role === 'admin' && /already withdrawn/i.test(msg)) negativeOffer.value = r.id
  } finally { busy.value = null }
}

const sendMpesa = (r: any) => run(r, () => refundApi.payOut(r.id))
const approve = (r: any, negative = false) => run(r, () => refundApi.approve(r.id, '', negative))
const reject = (r: any) => run(r, () => refundApi.reject(r.id, text.value.trim()))
const cancel = (r: any) => run(r, () => refundApi.cancel(r.id))
const markPaid = (r: any) => run(r, () => refundApi.markPaid(r.id, text.value.trim()))
const startReject = (id: string) => { rejecting.value = id; paying.value = null; text.value = '' }
const startPay = (id: string) => { paying.value = id; rejecting.value = null; text.value = '' }

onMounted(load)
</script>
