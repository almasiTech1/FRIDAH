<template>
  <div class="fx-page">
    <header class="fx-head"><div><h2>{{ title }}</h2><p>Your balance, payouts and history in one place</p></div></header>

    <div class="fx-grid main-side">
      <section v-spot class="fx-panel">
        <div class="fx-panel-head"><div><h3>Total balance</h3><p>{{ note }}</p></div>
          <button class="fx-icon-btn" :aria-label="hidden ? 'Show balance' : 'Hide balance'" @click="hidden = !hidden"><component :is="hidden ? EyeOff : Eye" /></button></div>
        <p class="fx-hero-amount">{{ hidden ? 'KES ••••••' : formatKES(shown).replace('.00', '') }}</p>
        <div class="grid sm:grid-cols-2 gap-5 mt-6 items-center">
          <div class="fx-credit" :class="{ flip }" @click="flip = !flip" title="Click to flip">
            <div class="fx-credit-in">
              <div class="fx-credit-face front"><div class="flex justify-between"><span class="fx-chip-card" /><b style="letter-spacing:.14em">FRIDAH</b></div>
                <div style="font:700 17px ui-monospace,monospace;letter-spacing:.08em">•••• •••• •••• {{ last4 }}</div>
                <div class="flex justify-between text-[11px]"><span>{{ holder }}</span><span>WALLET</span></div></div>
              <div class="fx-credit-face back"><div class="strip" /><div class="sig">{{ hidden ? '••••' : formatKES(shown).replace('.00', '') }}</div></div>
            </div>
          </div>
          <div class="space-y-2">
            <p class="text-xs font-bold uppercase tracking-wider" style="color:var(--muted)">Quick withdraw</p>
            <div class="fx-seg w-full" style="display:flex">
              <button v-for="p in [25, 50, 75, 100]" :key="p" class="flex-1" :class="{ on: pct === p }" @click="setPct(p)">{{ p === 100 ? 'Max' : p + '%' }}</button>
            </div>
            <p class="text-[11px]" style="color:var(--muted)">Pick a share of your balance to fill the amount.</p>
          </div>
        </div>
      </section>

      <section v-spot class="fx-panel">
        <div class="fx-panel-head"><div><h3>Withdraw to M-Pesa</h3><p>Minimum KES 100</p></div></div>
        <div class="fx-field"><label>Amount (KES)</label><input :value="amount || ''" class="input" type="number" :max="balance" min="100" placeholder="0" @input="$emit('update:amount', Number(($event.target as HTMLInputElement).value)); pct = 0" /></div>
        <div class="fx-field"><label>M-Pesa number</label><input :value="phone" class="input" placeholder="+254712345678" @input="$emit('update:phone', ($event.target as HTMLInputElement).value)" /></div>
        <button class="fx-pay-btn" :disabled="busy || amount < 100 || amount > balance" @click="$emit('withdraw')">
          <span>{{ busy ? 'Sending…' : amount > 0 ? `Withdraw ${formatKES(amount).replace('.00', '')}` : 'Withdraw' }}</span>
          <span class="go"><span v-if="busy" class="animate-spin w-4 h-4 border-2 border-current border-t-transparent rounded-full" /><span v-else>→</span></span>
        </button>
        <p v-if="amount > balance" class="text-xs mt-3" style="color:#dc2626">That's more than your available balance.</p>
        <p v-if="message" class="text-sm mt-3 font-semibold" :style="`color:${ok ? '#16a34a' : '#dc2626'}`" role="status">{{ message }}</p>
      </section>
    </div>

    <section class="fx-panel" style="padding:0">
      <div class="fx-panel-head" style="padding:20px 22px 0;margin:0"><div><h3>Transaction history</h3></div><span class="fx-live">Live</span></div>
      <p v-if="txLoading" class="p-8 text-center text-sm" style="color:var(--muted)">Loading…</p>
      <p v-else-if="!transactions.length" class="p-10 text-center text-sm" style="color:var(--muted)">No transactions yet.</p>
      <div v-else class="p-3 fx-feed">
        <div v-for="tx in transactions" :key="tx.id" class="fx-feed-item">
          <span class="fx-avatar" style="width:36px;height:36px;border-radius:12px" :style="tx.entry_type === 'credit' ? '' : 'background:rgba(239,68,68,.18);color:#ef4444'">{{ tx.entry_type === 'credit' ? '+' : '−' }}</span>
          <span class="min-w-0"><b class="block truncate">{{ tx.description }}</b><small>{{ formatDate(tx.created_at) }} · Bal {{ formatKES(tx.balance_after) }}</small></span>
          <span class="amt" :class="tx.entry_type === 'credit' ? 'pos' : 'neg'">{{ tx.entry_type === 'credit' ? '+' : '−' }}{{ formatKES(tx.amount) }}</span>
        </div>
      </div>
    </section>
  </div>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { Eye, EyeOff } from 'lucide-vue-next'
import { formatKES, formatDate } from '@/utils/formatters'
import { useCountUp } from '@/composables/useCountUp'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{ title: string; balance: number; note?: string; transactions: any[]; txLoading?: boolean; amount: number; phone: string; busy?: boolean; message?: string; ok?: boolean }>()
const emit = defineEmits<{ 'update:amount': [n: number]; 'update:phone': [s: string]; withdraw: [] }>()
const auth = useAuthStore()
const hidden = ref(false); const flip = ref(false); const pct = ref(0)
const shown = useCountUp(() => props.balance)
const holder = computed(() => `${auth.user?.first_name || ''} ${auth.user?.last_name || ''}`.trim().toUpperCase() || 'FRIDAH USER')
const last4 = computed(() => String(auth.user?.id || '0000').replace(/\D/g, '').padEnd(4, '0').slice(-4))
function setPct(p: number) { pct.value = p; emit('update:amount', Math.floor((props.balance * p) / 100)) }
</script>
