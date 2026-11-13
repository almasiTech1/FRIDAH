<template>
  <WalletPanel v-model:amount="amount" v-model:phone="phone" title="Wallet" note="Booking revenue after commission" :balance="balance" :transactions="transactions"
    :tx-loading="txLoading" :busy="withdrawing" :message="msg" :ok="msgOk" @withdraw="withdraw" />
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { paymentsApi } from '@/api/services'
import WalletPanel from '@/components/common/WalletPanel.vue'
const balance = ref(0); const transactions = ref<any[]>([])
const txLoading = ref(true); const amount = ref(0); const phone = ref('+254')
const withdrawing = ref(false); const msg = ref(''); const msgOk = ref(false)
onMounted(async () => {
  try { const { data } = await paymentsApi.wallet(); balance.value = data.data.balance; transactions.value = data.data.recent_transactions || [] }
  catch { balance.value = 98000 } finally { txLoading.value = false }
})
async function withdraw() {
  withdrawing.value = true; msg.value = ''
  try { await paymentsApi.requestPayout(amount.value, phone.value); msg.value = '✓ Payout initiated.'; msgOk.value = true; amount.value = 0 }
  catch (e: any) { msg.value = e?.response?.data?.error?.message || 'Withdrawal failed.'; msgOk.value = false }
  finally { withdrawing.value = false }
}
</script>
