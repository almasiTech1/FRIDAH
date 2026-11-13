<template>
  <div class="fx-page">
    <DashHeader :name="auth.user?.first_name || 'there'" subtitle="Your rental overview">
      <RouterLink to="/tenant/maintenance" class="fx-btn"><Wrench /> Report issue</RouterLink>
      <button class="fx-btn accent" :disabled="!nextInvoice" @click="nextInvoice && payNow(nextInvoice)"><CreditCard /> {{ nextInvoice ? 'Pay rent now' : 'All paid up' }}</button>
    </DashHeader>

    <div v-if="!auth.isKycVerified" class="fx-banner warn">
      <Lock :size="22" style="color:#d97706" />
      <div class="flex-1"><b>Complete your KYC verification</b><span>Upload your National ID to unlock every feature.</span></div>
      <RouterLink to="/tenant/profile" class="fx-btn primary" style="height:38px">Verify now <ArrowRight /></RouterLink>
    </div>

    <template v-if="stats">
      <div class="fx-grid main-side">
        <section v-spot class="fx-panel">
          <div class="fx-panel-head"><div><h3>Your invoices</h3><p>Click a bar to see the amount</p></div>
            <SegTabs v-model="invFilter" :options="[{ label: 'All', value: 'all' }, { label: 'Unpaid', value: 'unpaid' }, { label: 'Paid', value: 'paid' }]" /></div>
          <div v-if="barInvoices.length">
            <div class="flex items-baseline gap-3 mb-1"><span class="fx-hero-amount">{{ formatKES(barInvoices[selBar]?.amount || 0).replace('.00', '') }}</span>
              <span v-if="barInvoices[selBar]" class="badge" :class="statusColor(barInvoices[selBar].status)">{{ barInvoices[selBar].status }}</span></div>
            <InteractiveBars :key="invFilter" v-model="selBar" :labels="barInvoices.map(i => formatDate(i.period_start).replace(/ \d{4}$/, ''))" :values="barInvoices.map(i => Number(i.amount))" :height="200" />
          </div>
          <p v-else class="py-14 text-center text-sm" style="color:var(--muted)">No invoices to show yet.</p>
        </section>

        <section v-spot class="fx-panel dark-card">
          <div class="fx-panel-head"><div><h3>To do</h3><p>Stay on top of your tenancy</p></div></div>
          <TaskList :items="tasks" />
        </section>
      </div>

      <div class="fx-grid k4">
        <StatCard label="Pending balance" :value="stats.pending_balance" currency :icon-comp="Wallet" color="#ef4444" :trend="-2" to="/tenant/invoices" variant="accent" />
        <StatCard label="Unpaid invoices" :value="stats.pending_invoices_count" :icon-comp="Receipt" color="#f97316" to="/tenant/invoices" />
        <StatCard label="Open maintenance" :value="stats.open_maintenance_requests" :icon-comp="Wrench" color="#8b5cf6" to="/tenant/maintenance" />
        <StatCard label="Paid this year" :value="stats.total_paid_this_year" currency :icon-comp="CheckCircle2" color="#10b981" :trend="12" :spark="[20,28,26,34,38,36,48]" variant="inverse" />
      </div>

      <section v-if="lease" v-spot class="fx-panel fade-in">
        <div class="fx-panel-head">
          <div class="flex items-center gap-3"><span class="fx-ico" style="width:44px;height:44px"><Home /></span>
            <div><h3 class="text-base">{{ lease.property_name }}</h3><p>Unit {{ lease.unit_number }}</p></div></div>
          <span class="badge badge-green">{{ lease.status }}</span>
        </div>
        <div class="fx-grid k4">
          <div v-for="f in leaseFields" :key="f.label"><p class="text-[11px] font-bold uppercase tracking-wider" style="color:var(--muted)">{{ f.label }}</p><p class="font-extrabold mt-1">{{ f.value }}</p></div>
        </div>
      </section>

      <section class="fx-panel" style="padding:0">
        <div class="fx-panel-head" style="padding:20px 22px 0;margin:0"><div><h3>Recent invoices</h3></div><RouterLink to="/tenant/invoices" class="fx-link">View all →</RouterLink></div>
        <div v-if="invoices.length" class="overflow-x-auto mt-2">
          <table class="w-full">
            <thead><tr><th class="table-th">Invoice</th><th class="table-th">Period</th><th class="table-th">Amount</th><th class="table-th">Status</th><th class="table-th">Action</th></tr></thead>
            <tbody>
              <tr v-for="inv in invoices" :key="inv.id" class="table-tr">
                <td class="table-td font-mono text-xs">{{ inv.invoice_number }}</td>
                <td class="table-td">{{ formatDate(inv.period_start) }}</td>
                <td class="table-td font-bold" style="color:var(--text)">{{ formatKES(inv.amount) }}</td>
                <td class="table-td"><span :class="statusColor(inv.status)" class="badge"><span class="w-1.5 h-1.5 rounded-full bg-current opacity-60" />{{ inv.status }}</span></td>
                <td class="table-td"><button v-if="inv.status !== 'paid'" class="fx-btn accent" style="height:32px;padding:0 14px;font-size:12px" @click="payNow(inv)">Pay</button><span v-else class="text-xs" style="color:var(--muted)">—</span></td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else class="py-12 text-center" style="color:var(--muted)">No invoices yet</p>
      </section>

      <QuickTiles :items="quick" />
    </template>
    <div v-else class="fx-grid k4"><div v-for="i in 4" :key="i" class="fx-skeleton" /></div>

    <MpesaPayModal v-model="showPay" :amount="selectedInvoice?.balance || 0" :invoice-id="selectedInvoice?.id" accent-bg="bg-tenant-600 hover:bg-tenant-700" @paid="loadData" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { Wrench, CreditCard, Lock, ArrowRight, Wallet, Receipt, CheckCircle2, Home, Building2 } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { analyticsApi, rentalsApi } from '@/api/services'
import StatCard from '@/components/common/StatCard.vue'
import MpesaPayModal from '@/components/common/MpesaPayModal.vue'
import DashHeader from '@/components/ui/DashHeader.vue'
import SegTabs from '@/components/ui/SegTabs.vue'
import InteractiveBars from '@/components/ui/InteractiveBars.vue'
import TaskList from '@/components/ui/TaskList.vue'
import QuickTiles from '@/components/ui/QuickTiles.vue'
import { formatKES, formatDate, statusColor } from '@/utils/formatters'
import type { TenantDashboard, Lease, Invoice } from '@/types'

const auth = useAuthStore()
const stats = ref<TenantDashboard | null>(null)
const lease = ref<Lease | null>(null)
const invoices = ref<Invoice[]>([])
const showPay = ref(false)
const selectedInvoice = ref<Invoice | null>(null)
const invFilter = ref<'all' | 'unpaid' | 'paid'>('all')
const selBar = ref(0)

const barInvoices = computed(() => {
  const list = invoices.value.filter((i) => invFilter.value === 'all' || (invFilter.value === 'paid' ? i.status === 'paid' : i.status !== 'paid')).slice().reverse()
  return list
})
const nextInvoice = computed(() => invoices.value.find((i) => i.status !== 'paid') || null)
const tasks = computed(() => [
  ...(nextInvoice.value ? [{ id: 'pay', title: `Pay invoice ${nextInvoice.value.invoice_number}`, meta: `${formatKES(nextInvoice.value.balance ?? nextInvoice.value.amount)} · due ${formatDate(nextInvoice.value.period_start)}`, to: '/tenant/invoices' }] : []),
  ...(!auth.isKycVerified ? [{ id: 'kyc', title: 'Upload your National ID', meta: 'KYC verification', to: '/tenant/profile' }] : []),
  ...((stats.value?.open_maintenance_requests || 0) > 0 ? [{ id: 'maint', title: `Follow up ${stats.value!.open_maintenance_requests} maintenance request(s)`, meta: 'Open requests', to: '/tenant/maintenance' }] : []),
  { id: 'lease', title: 'Check your lease details', meta: 'Term, rent and due day', to: '/tenant/lease' },
])
const leaseFields = computed(() => lease.value ? [
  { label: 'Property', value: lease.value.property_name }, { label: 'Unit', value: lease.value.unit_number },
  { label: 'Rent', value: formatKES(lease.value.rent_amount) }, { label: 'Due day', value: `Day ${lease.value.rent_due_day}` },
] : [])
const quick = [
  { to: '/tenant/invoices', label: 'Pay rent', icon: Receipt }, { to: '/tenant/maintenance', label: 'Maintenance', icon: Wrench },
  { to: '/tenant/properties', label: 'Browse homes', icon: Building2 }, { to: '/tenant/payments', label: 'Payment history', icon: CreditCard },
]

function payNow(inv: Invoice) { selectedInvoice.value = inv; showPay.value = true }

async function loadData() {
  try {
    const [dashRes, leaseRes, invRes] = await Promise.all([analyticsApi.tenantDashboard(), rentalsApi.leases({ status: 'active' }), rentalsApi.invoices()])
    stats.value = dashRes.data.data
    lease.value = (leaseRes.data.data?.results || [])[0] || null
    invoices.value = (invRes.data.data?.results || []).slice(0, 6)
  } catch {
    stats.value = { active_lease_id: undefined, rent_amount: 25000, pending_invoices_count: 2, pending_balance: 50000, open_maintenance_requests: 1, total_paid_this_year: 150000 }
  }
  selBar.value = Math.max(0, barInvoices.value.length - 1)
}
onMounted(loadData)
</script>
