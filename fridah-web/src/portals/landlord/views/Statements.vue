<template>
  <div class="space-y-5">
    <div>
      <h1 class="page-title">Statements &amp; Payouts</h1>
      <p class="text-sm text-gray-500 mt-0.5">Income, fees and net payouts reported by agencies managing your properties.</p>
    </div>

    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="card animate-pulse h-24 bg-gray-100 rounded-xl"/>
    </div>

    <div v-else-if="!statements.length" class="card card-body text-center py-12 text-gray-400">
      No statements yet. Once an agency managing one of your properties issues a statement, it will show up here.
    </div>

    <div v-else class="space-y-3">
      <div v-for="s in statements" :key="s.id" class="card card-body">
        <div class="flex items-center justify-between flex-wrap gap-2">
          <div>
            <div class="flex items-center gap-3 flex-wrap">
              <p class="font-semibold text-gray-900">{{ s.property_name }}</p>
              <span :class="statusColor(s.status)" class="badge">{{ s.status }}</span>
            </div>
            <p class="text-xs text-gray-500 mt-0.5">{{ formatDate(s.period_start) }} – {{ formatDate(s.period_end) }} · Managed by {{ s.agency_name || 'Fridah' }}</p>
          </div>
          <div class="flex items-center gap-3">
            <span v-if="payoutFor(s.id)" :class="statusColor(payoutFor(s.id)!.status)" class="badge text-xs">
              Payout: {{ payoutFor(s.id)!.status }}
            </span>
            <a v-if="s.pdf_statement" :href="s.pdf_statement" target="_blank" rel="noopener" class="btn-outline border-gray-200 text-xs">Download PDF</a>
          </div>
        </div>
        <div class="grid grid-cols-3 md:grid-cols-6 gap-3 mt-4 text-center">
          <div><p class="text-xs text-gray-400">Gross</p><p class="text-sm font-bold">{{ formatKES(s.gross_rent_collected) }}</p></div>
          <div><p class="text-xs text-gray-400">Vacancy</p><p class="text-sm font-bold text-orange-500">{{ formatKES(s.vacancy_loss) }}</p></div>
          <div><p class="text-xs text-gray-400">Arrears</p><p class="text-sm font-bold text-red-500">{{ formatKES(s.arrears) }}</p></div>
          <div><p class="text-xs text-gray-400">Agency Fee</p><p class="text-sm font-bold text-landlord-600">{{ formatKES(s.agency_commission) }}</p></div>
          <div><p class="text-xs text-gray-400">Expenses</p><p class="text-sm font-bold text-orange-500">{{ formatKES(s.approved_expenses) }}</p></div>
          <div><p class="text-xs text-gray-400">Net Payable</p><p class="text-base font-black text-emerald-600">{{ formatKES(s.net_payable) }}</p></div>
        </div>
        <div v-if="payoutFor(s.id)" class="mt-3 pt-3 border-t border-gray-100 text-xs text-gray-500 flex items-center gap-3 flex-wrap">
          <span>Ref: {{ payoutFor(s.id)!.reference || '—' }}</span>
          <span v-if="payoutFor(s.id)!.completed_at">Paid {{ formatDate(payoutFor(s.id)!.completed_at!) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { agencyApi } from '@/api/services'
import { statusColor, formatDate, formatKES } from '@/utils/formatters'
import type { OwnerStatement, OwnerPayout } from '@/types'

const route = useRoute()
const statements = ref<OwnerStatement[]>([])
const payouts = ref<OwnerPayout[]>([])
const loading = ref(true)

function payoutFor(statementId: string): OwnerPayout | undefined {
  return payouts.value.find((p) => p.statement === statementId)
}

async function load() {
  loading.value = true
  try {
    const params: Record<string, unknown> = {}
    if (route.query.property) params.property = route.query.property
    const [statementsRes, payoutsRes] = await Promise.all([
      agencyApi.statements(params),
      agencyApi.payouts(),
    ])
    statements.value = (statementsRes.data as any).data?.results || (statementsRes.data as any).results || (statementsRes.data as any).data || []
    payouts.value = (payoutsRes.data as any).data?.results || (payoutsRes.data as any).results || (payoutsRes.data as any).data || []
  } catch {
    statements.value = []
    payouts.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
