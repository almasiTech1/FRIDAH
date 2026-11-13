<template>
  <section class="max-w-7xl mx-auto px-6 pb-24">
    <div v-reveal="'up'" class="text-center max-w-2xl mx-auto mb-8">
      <span class="fx-chip neutral" style="padding:5px 14px">Live preview</span>
      <h2 class="text-3xl md:text-4xl font-black mt-4" style="color:var(--text)">Dashboards that feel as good as they look</h2>
      <p class="mt-3" style="color:var(--muted)">Pick a portal and a look. Click the bars, toggle the range, hover the chart — it's the real thing, with sample data.</p>
    </div>

    <div class="fx-showcase-tabs mb-4"><SegTabs v-model="tab" :options="tabs" /></div>
    <div class="fx-looks mb-8">
      <button v-for="s in SKINS" :key="s.id" class="fx-look" :class="{ on: skin.id === s.id }" @click="skin.set(s.id)">
        <span class="fx-swatch"><i v-for="c in s.swatch" :key="c" :style="`background:${c}`" /></span>{{ s.name }}
      </button>
    </div>

    <div v-reveal="'zoom'" class="fx-mock max-w-6xl mx-auto">
      <div class="fx-mock-bar"><i /><i /><i /><span>fridah.co.ke / {{ tab }} / dashboard</span></div>
      <div class="fx-page" :key="tab">
        <header class="fx-head"><div><h2 style="font-size:clamp(22px,3vw,30px)">{{ cur.title }}</h2><p>{{ cur.sub }}</p></div>
          <div class="fx-actions"><RouterLink to="/register" class="fx-btn accent">{{ cur.cta }}</RouterLink></div></header>
        <div class="fx-grid k4">
          <StatCard v-for="(k, i) in cur.kpis" :key="k.label" :label="k.label" :value="k.value" :currency="k.currency" :trend="k.trend" :icon="k.icon" :spark="k.spark" :variant="i === 1 ? 'accent' : i === 3 ? 'inverse' : 'default'" />
        </div>
        <div class="fx-grid main-side">
          <section class="fx-panel">
            <div class="fx-panel-head"><div><h3>{{ cur.chart }}</h3><p>Sample data · click a bar</p></div>
              <SegTabs :model-value="range" :options="[{ label: '3 mo', value: 3 }, { label: '6 mo', value: 6 }]" @update:model-value="(v: number) => { range = v; sel = v - 1 }" /></div>
            <div class="flex items-baseline gap-3 mb-1"><span class="fx-hero-amount">{{ compactKES(vals[sel] ?? 0) }}</span>
              <span class="fx-chip">▲ {{ delta }}%</span></div>
            <InteractiveBars :key="tab + range" v-model="sel" :labels="labels" :values="vals" :height="190" />
          </section>
          <section class="fx-panel">
            <div class="fx-panel-head"><div><h3>{{ cur.donutTitle }}</h3><p>Hover to focus</p></div></div>
            <DonutBreakdown :items="cur.donut" :center-label="cur.donutLabel" />
          </section>
        </div>
      </div>
    </div>
  </section>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { SKINS, useSkinStore } from '@/stores/skin'
import { monthLabels, compactKES } from '@/composables/useCountUp'
import StatCard from '@/components/common/StatCard.vue'
import SegTabs from '@/components/ui/SegTabs.vue'
import InteractiveBars from '@/components/ui/InteractiveBars.vue'
import DonutBreakdown from '@/components/ui/DonutBreakdown.vue'

const skin = useSkinStore()
const tab = ref('landlord'); const range = ref(6); const sel = ref(5)
const tabs = [{ label: 'Landlord', value: 'landlord' }, { label: 'Tenant', value: 'tenant' }, { label: 'Agency', value: 'agency' }, { label: 'Hotel', value: 'hotel' }, { label: 'Admin', value: 'admin' }]
const DATA: Record<string, any> = {
  landlord: { title: 'Good afternoon, Wanjiru', sub: 'Your portfolio at a glance', cta: 'Add property', chart: 'Rent collected', series: [310, 340, 328, 372, 395, 428, 441, 470, 505].map((n) => n * 1000),
    kpis: [{ label: 'Properties', value: 8, icon: '🏢', trend: 4 }, { label: 'Collected (month)', value: 428000, currency: true, icon: '💰', trend: 15, spark: [3, 4, 3.5, 5, 6, 7] }, { label: 'Overdue', value: 52000, currency: true, icon: '⏰', trend: -8 }, { label: 'Occupancy', value: '92%', icon: '🔑', trend: 3 }],
    donutTitle: 'Collected vs overdue', donutLabel: 'Billed', donut: [{ label: 'Collected', value: 428000 }, { label: 'Overdue', value: 52000, color: '#ef4444' }] },
  tenant: { title: 'Good afternoon, Brian', sub: 'Your rental overview', cta: 'Pay rent', chart: 'Your rent payments', series: Array(9).fill(0).map((_, i) => 25000 + (i % 3) * 500),
    kpis: [{ label: 'Pending balance', value: 25000, currency: true, icon: '💳', trend: 0 }, { label: 'Next due', value: '5th', icon: '📅' }, { label: 'Open requests', value: 1, icon: '🔧' }, { label: 'Paid this year', value: 250000, currency: true, icon: '✅', trend: 12 }],
    donutTitle: 'Where your rent goes', donutLabel: 'Monthly', donut: [{ label: 'Rent', value: 25000 }, { label: 'Water', value: 1800 }, { label: 'Service charge', value: 2500 }] },
  agency: { title: 'Good afternoon, Prime Managers', sub: '12 managed properties', cta: 'Generate statement', chart: 'Collected rent', series: [820, 790, 860, 905, 940, 1010, 1040, 1100, 1180].map((n) => n * 1000),
    kpis: [{ label: 'Managed properties', value: 12, icon: '🏘️', trend: 8 }, { label: 'Property owners', value: 5, icon: '👥' }, { label: 'Draft statements', value: 3, icon: '🧾' }, { label: 'Pending payouts', value: 2, icon: '💸', trend: 0 }],
    donutTitle: 'Portfolio occupancy', donutLabel: 'Units', donut: [{ label: 'Occupied', value: 86 }, { label: 'Vacant', value: 9 }] },
  hotel: { title: 'Hello, Barbara', sub: 'Hotel & BnB overview', cta: 'View bookings', chart: 'Revenue', series: [96, 110, 104, 128, 140, 144, 152, 160, 171].map((n) => n * 1000),
    kpis: [{ label: 'Revenue (month)', value: 144000, currency: true, icon: '💵', trend: 9 }, { label: 'Bookings', value: 24, icon: '📆', trend: 6 }, { label: 'Check-ins today', value: 3, icon: '🛎️' }, { label: 'Current guests', value: 7, icon: '🧳' }],
    donutTitle: 'Listings', donutLabel: 'Total', donut: [{ label: 'Hotels', value: 1 }, { label: 'BnBs', value: 3 }] },
  admin: { title: 'Good afternoon, Admin', sub: 'Platform control centre', cta: 'Manage users', chart: 'Platform commission', series: [210, 240, 255, 290, 330, 360, 372, 395, 420].map((n) => n * 1000),
    kpis: [{ label: 'Active people', value: 342, icon: '👥', trend: 8 }, { label: 'Waiting for review', value: 25, icon: '🛡️' }, { label: 'Active leases', value: 210, icon: '📄', trend: 5 }, { label: 'Net commission', value: 600000, currency: true, icon: '📈', trend: 12 }],
    donutTitle: 'Users by role', donutLabel: 'People', donut: [{ label: 'Tenants', value: 280 }, { label: 'Landlords', value: 45 }, { label: 'Providers', value: 10 }, { label: 'Hotels', value: 7 }] },
}
const cur = computed(() => DATA[tab.value])
const vals = computed(() => cur.value.series.slice(-range.value))
const labels = computed(() => monthLabels(range.value))
const delta = computed(() => { const i = sel.value; return i > 0 && vals.value[i - 1] ? Math.round(((vals.value[i] - vals.value[i - 1]) / vals.value[i - 1]) * 100) : 0 })
watch(tab, () => { sel.value = range.value - 1 })
</script>
