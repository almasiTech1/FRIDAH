<template>
  <form class="mt-3 p-4 rounded-lg bg-gray-50 border border-gray-200 space-y-3" aria-label="Request a refund" @submit.prevent="submit">
    <p class="text-sm font-medium text-gray-800">
      Request a refund for {{ payment.reference }}
      <span class="text-gray-500 font-normal">(up to {{ formatKES(remaining) }} can still be refunded)</span>
    </p>
    <div class="grid md:grid-cols-4 gap-3">
      <div>
        <label class="text-xs font-medium text-gray-600" :for="`rf-amt-${payment.id}`">Amount (KES)</label>
        <input :id="`rf-amt-${payment.id}`" v-model="amount" type="number" min="1" step="0.01" :max="remaining" class="input" required />
      </div>
      <div v-if="canReverse">
        <label class="text-xs font-medium text-gray-600" :for="`rf-kind-${payment.id}`">Type</label>
        <select :id="`rf-kind-${payment.id}`" v-model="kind" class="input" @change="onKind">
          <option value="refund">Refund</option>
          <option value="reversal">Reversal (full, mistaken/duplicate)</option>
        </select>
      </div>
      <div :class="canReverse ? 'md:col-span-2' : 'md:col-span-3'">
        <label class="text-xs font-medium text-gray-600" :for="`rf-why-${payment.id}`">Reason</label>
        <input :id="`rf-why-${payment.id}`" v-model="reason" class="input" required placeholder="Why should this be refunded?" />
      </div>
    </div>
    <p class="text-xs text-gray-500">
      Refunds over {{ formatKES(limit) }} and all reversals need an administrator. You cannot approve your own request.
    </p>
    <p v-if="error" class="text-sm text-red-600" role="alert">{{ error }}</p>
    <div class="flex gap-2">
      <button class="btn bg-gray-900 text-white" :disabled="saving || !amount || !reason.trim()">{{ saving ? 'Sending…' : 'Submit request' }}</button>
      <button type="button" class="btn-outline border-gray-200" @click="$emit('cancel')">Cancel</button>
    </div>
  </form>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { refundApi } from '@/api/services'
import { formatKES } from '@/utils/formatters'

const props = withDefaults(defineProps<{
  payment: { id: string; reference: string; amount: string | number; refunded_amount?: string | number }
  canReverse?: boolean
  adminAbove?: number
}>(), { canReverse: false, adminAbove: 5000 })
const emit = defineEmits<{ (e: 'done'): void; (e: 'cancel'): void }>()

const limit = ref(props.adminAbove)
onMounted(async () => {
  try { const res: any = await refundApi.policy(); const v = res?.data?.data?.admin_approval_above; if (v !== undefined) limit.value = Number(v) } catch { /* keep the default */ }
})
const remaining = computed(() => Number(props.payment.amount) - Number(props.payment.refunded_amount || 0))
const amount = ref<string>('')
const reason = ref('')
const kind = ref<'refund' | 'reversal'>('refund')
const saving = ref(false)
const error = ref('')

function onKind() { if (kind.value === 'reversal') amount.value = String(remaining.value) }

async function submit() {
  error.value = ''; saving.value = true
  try {
    await refundApi.request(props.payment.id, { amount: amount.value, reason: reason.value.trim(), kind: kind.value })
    emit('done')
  } catch (e: any) {
    error.value = e?.response?.data?.error?.message || e?.response?.data?.detail || 'Could not submit the request.'
  } finally { saving.value = false }
}
</script>
