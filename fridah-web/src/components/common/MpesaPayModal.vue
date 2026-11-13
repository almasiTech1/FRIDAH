<template>
  <Teleport to="body">
    <div v-if="modelValue" class="fx-modal-overlay" @mousedown.self="$emit('update:modelValue', false)" @keydown.esc="$emit('update:modelValue', false)">
      <div class="fx-modal" role="dialog" aria-modal="true" aria-label="Complete your payment">
        <div class="flex items-start justify-between gap-4 mb-5">
          <div>
            <h2 style="font-size:26px;font-weight:800;letter-spacing:-.02em">Complete your payment</h2>
            <p class="text-sm mt-1" style="color:var(--muted,#6b7280)">Secured by Safaricom M-Pesa · you approve it on your phone</p>
          </div>
          <button class="fx-icon-btn" aria-label="Close" @click="$emit('update:modelValue', false)" style="flex-shrink:0">✕</button>
        </div>

        <div class="grid gap-6 md:grid-cols-[1fr_1fr_.9fr] items-start">
          <!-- Card preview -->
          <div>
            <div class="fx-credit" :class="{ flip: flipped }" @click="flipped = !flipped" title="Click to flip">
              <div class="fx-credit-in">
                <div class="fx-credit-face front" style="background:linear-gradient(135deg,#22c55e,#15803d 60%,#0f5a2c)">
                  <div class="flex justify-between items-start"><span class="fx-chip-card" /><b style="letter-spacing:.14em;font-size:15px">M-PESA</b></div>
                  <div style="font:700 19px ui-monospace,monospace;letter-spacing:.06em">{{ masked }}</div>
                  <div class="flex justify-between items-end text-[11px]"><div><span style="opacity:.7">PAYING</span><br><b style="font-size:14px">{{ formatKES(amount) }}</b></div><div style="text-align:right;opacity:.85">STK PUSH<br>SAFARICOM</div></div>
                </div>
                <div class="fx-credit-face back"><div class="strip" /><div class="sig">{{ state === 'success' ? 'PAID ✓' : state === 'processing' ? 'WAITING FOR PIN…' : 'READY' }}</div>
                  <p class="px-5 text-[11px]" style="opacity:.6">Your M-Pesa PIN is entered on your phone only. FRIDAH never sees it.</p></div>
              </div>
            </div>
            <div class="flex justify-center gap-2 mt-4 flex-wrap">
              <span class="fx-kbd">256-bit encrypted</span><span class="fx-kbd">Daraja API</span>
            </div>
          </div>

          <!-- Details -->
          <div>
            <h3 class="font-extrabold mb-3 text-sm">Payment details</h3>
            <div class="fx-field"><label>Amount (KES)</label><input class="input" :value="formatKES(amount)" readonly /></div>
            <div class="fx-field"><label>M-Pesa phone number</label><input v-model="phone" class="input" type="tel" inputmode="tel" placeholder="+254712345678" :disabled="state === 'processing'" @focus="flipped = false" /></div>

            <div v-if="state === 'processing'" class="fx-stk">
              <div class="fx-pulse-ring"><svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><rect x="7" y="2" width="10" height="20" rx="2.5"/><path d="M11 18h2"/></svg></div>
              <p class="text-sm font-semibold text-center">STK push sent — enter your M-Pesa PIN on your phone…</p>
              <p class="text-xs" style="color:var(--muted,#6b7280)">Checking status automatically</p>
            </div>
            <div v-else-if="state === 'success'" class="fx-stk">
              <div class="fx-pulse-ring" style="animation:none"><svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 13l4 4L19 7"/></svg></div>
              <p class="font-extrabold">Payment successful!</p><p class="text-xs" style="color:var(--muted,#6b7280)">{{ successMessage }}</p>
            </div>
            <div v-else-if="state === 'failed'" class="p-3 rounded-2xl text-sm" style="background:rgba(239,68,68,.12);color:#dc2626">{{ errorMessage }}</div>

            <div class="mt-5">
              <button v-if="state === 'idle' || state === 'failed'" class="fx-pay-btn" :disabled="!phone || phone.length < 10 || loading" @click="initiate">
                <span>{{ loading ? 'Sending request…' : state === 'failed' ? 'Try again' : `Pay ${formatKES(amount)}` }}</span><span class="go"><span v-if="loading" class="animate-spin w-4 h-4 border-2 border-current border-t-transparent rounded-full" /><span v-else>→</span></span>
              </button>
              <button v-else-if="state === 'success'" class="fx-pay-btn" @click="done"><span>Done</span><span class="go">✓</span></button>
            </div>
          </div>

          <!-- Summary -->
          <aside class="fx-panel" style="padding:18px;box-shadow:none">
            <h3 class="font-extrabold mb-3 text-sm">Order summary</h3>
            <div class="flex justify-between text-sm py-2"><span style="color:var(--muted,#6b7280)">{{ description || 'FRIDAH payment' }}</span><b>{{ formatKES(amount) }}</b></div>
            <div class="flex justify-between text-sm py-2"><span style="color:var(--muted,#6b7280)">Processing fee</span><b style="color:#16a34a">Free</b></div>
            <div style="border-top:1px dashed var(--border-strong,#e5e7eb)" class="mt-2 pt-3 flex justify-between"><span class="font-semibold">Total</span><b class="text-lg">{{ formatKES(amount) }}</b></div>
            <p class="text-[11px] mt-4" style="color:var(--muted,#6b7280)">A receipt is sent by SMS and appears in your payment history.</p>
          </aside>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, onBeforeUnmount } from 'vue'
import { paymentsApi } from '@/api/services'
import { formatKES } from '@/utils/formatters'

const props = withDefaults(defineProps<{
  modelValue: boolean
  amount: number
  invoiceId?: string
  bookingId?: string
  description?: string
  accentBg?: string
}>(), { accentBg: 'bg-green-600 hover:bg-green-700' })

const emit = defineEmits<{ 'update:modelValue': [v: boolean]; 'paid': [] }>()

const phone = ref('+254')
const flipped = ref(false)
const masked = computed(() => {
  const d = phone.value.replace(/[^\d+]/g, '')
  const pad = (d + '••••••••••••').slice(0, 13)
  return pad.replace(/(.{4})(.{3})(.{3})(.*)/, '$1 $2 $3 $4').trim()
})
const state = ref<'idle' | 'processing' | 'success' | 'failed'>('idle')
const loading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
let pollTimer: ReturnType<typeof setInterval> | null = null
let paymentId = ''

async function initiate() {
  loading.value = true
  state.value = 'idle'
  try {
    const { data } = await paymentsApi.stkPush({
      phone_number: phone.value,
      amount: props.amount,
      invoice_id: props.invoiceId,
      booking_id: props.bookingId,
      description: props.description || 'FRIDAH Payment',
    })
    paymentId = data.data.payment.id
    state.value = 'processing'
    startPolling()
  } catch (err: any) {
    errorMessage.value = err?.response?.data?.error?.message || 'Could not initiate payment. Please try again.'
    state.value = 'failed'
  } finally {
    loading.value = false
  }
}

function startPolling() {
  let attempts = 0
  pollTimer = setInterval(async () => {
    attempts++
    if (attempts > 12) { clearPolling(); state.value = 'failed'; errorMessage.value = 'Payment timed out.'; return }
    try {
      const { data } = await paymentsApi.stkStatus(paymentId)
      const s = data.data.status
      if (s === 'completed') {
        clearPolling(); state.value = 'success'
        successMessage.value = `KES ${props.amount.toLocaleString()} paid successfully.`
      } else if (s === 'failed' || s === 'cancelled') {
        clearPolling(); state.value = 'failed'
        errorMessage.value = data.data.failure_reason || 'Payment failed or was cancelled.'
      }
    } catch {}
  }, 5000)
}

function clearPolling() { if (pollTimer) { clearInterval(pollTimer); pollTimer = null } }

function done() { emit('paid'); emit('update:modelValue', false); state.value = 'idle'; flipped.value = false }
onBeforeUnmount(clearPolling)
</script>
