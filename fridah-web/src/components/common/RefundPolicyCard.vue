<template>
  <section class="card card-body space-y-3" aria-labelledby="rp-title">
    <div>
      <h2 id="rp-title" class="font-semibold text-gray-900">Refund policy</h2>
      <p class="text-xs text-gray-500">
        Set with finance. Up to the limit a refund can be approved by the payment's recipient or an administrator; above it, and for every reversal,
        only an administrator. Every change is recorded in the audit log.
      </p>
    </div>
    <p v-if="loadError" class="text-sm text-red-600" role="alert">{{ loadError }}</p>
    <form v-else-if="policy" class="grid md:grid-cols-4 gap-3 items-end" @submit.prevent="save">
      <div>
        <label class="text-xs font-medium text-gray-600" for="rp-limit">Admin approval needed above (KES)</label>
        <input id="rp-limit" v-model="limit" type="number" min="0" max="1000000" step="1" class="input" required />
      </div>
      <div>
        <label class="text-xs font-medium text-gray-600" for="rp-days">Refund window (days)</label>
        <input id="rp-days" v-model="days" type="number" min="1" max="730" step="1" class="input" required />
      </div>
      <div class="md:col-span-2 flex items-center gap-3">
        <button class="btn bg-gray-900 text-white" :disabled="saving">{{ saving ? 'Saving…' : 'Save policy' }}</button>
        <span v-if="saved" class="text-sm text-emerald-700" role="status">Saved</span>
      </div>
      <p class="md:col-span-4 text-xs text-gray-500">
        Fixed by configuration (not editable here):
        approving your own request is <strong>{{ policy.self_approval_allowed ? 'allowed' : 'not allowed' }}</strong>;
        automatic M-Pesa payouts are <strong>{{ policy.auto_payout_enabled ? 'on' : 'off' }}</strong>.
      </p>
      <p v-if="error" class="md:col-span-4 text-sm text-red-600" role="alert">{{ error }}</p>
    </form>
  </section>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { refundApi } from '@/api/services'

const policy = ref<any | null>(null)
const limit = ref<string | number>('')
const days = ref<string | number>('')
const loadError = ref(''); const error = ref('')
const saving = ref(false); const saved = ref(false)

function apply(p: any) { policy.value = p; limit.value = Number(p.admin_approval_above); days.value = p.window_days }

onMounted(async () => {
  try { apply(((await refundApi.policy()).data as any).data) } catch { loadError.value = 'Could not load the refund policy.' }
})

async function save() {
  saving.value = true; error.value = ''; saved.value = false
  try {
    apply(((await refundApi.updatePolicy(limit.value, days.value)).data as any).data)
    saved.value = true; setTimeout(() => (saved.value = false), 2500)
  } catch (e: any) { error.value = e?.response?.data?.error?.message || 'Could not save the policy.' }
  finally { saving.value = false }
}
</script>
