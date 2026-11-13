<template>
  <div>
    <section class="max-w-5xl mx-auto px-6 pt-20 pb-14 text-center">
      <p v-reveal="'fade'" class="text-brand-600 dark:text-brand-400 font-semibold text-sm uppercase tracking-widest mb-3">What we offer</p>
      <h1 v-reveal="'up'" class="text-4xl md:text-5xl font-black text-gray-900 dark:text-white">Every module your business needs</h1>
      <p v-reveal="'up'" class="mt-6 text-lg text-gray-500 dark:text-gray-400 max-w-2xl mx-auto">
        From a single rental unit to a multi-property hotel group — FRIDAH scales with you.
      </p>
    </section>

    <section class="max-w-7xl mx-auto px-6 pb-24 space-y-6">
      <div
        v-for="(s, i) in services" :key="s.title"
        v-reveal="i % 2 === 0 ? 'left' : 'right'"
        class="grid md:grid-cols-2 gap-8 items-center rounded-3xl p-8 md:p-12 border border-gray-100 dark:border-gray-800"
        :class="i % 2 === 0 ? 'bg-gray-50 dark:bg-gray-900/40' : 'bg-white dark:bg-gray-900'"
      >
        <div :class="i % 2 === 1 ? 'md:order-2' : ''">
          <div class="w-14 h-14 rounded-2xl flex items-center justify-center text-3xl mb-5" :style="{ background: `${s.color}1a` }">{{ s.icon }}</div>
          <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-3">{{ s.title }}</h2>
          <p class="text-gray-600 dark:text-gray-300 leading-relaxed mb-5">{{ s.description }}</p>
          <ul class="space-y-2">
            <li v-for="item in s.items" :key="item" class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
              <svg class="w-4 h-4 text-brand-600 dark:text-brand-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
              {{ item }}
            </li>
          </ul>
        </div>
        <div :class="i % 2 === 1 ? 'md:order-1' : ''" class="aspect-video rounded-2xl flex items-center justify-center text-6xl" :style="{ background: `${s.color}0f` }">
          {{ s.icon }}
        </div>
      </div>
    </section>

    <section class="py-20 bg-gray-900 dark:bg-brand-950">
      <div class="max-w-4xl mx-auto px-6 text-center">
        <h2 v-reveal="'up'" class="text-3xl font-black text-white mb-4">Not sure which modules you need?</h2>
        <p v-reveal="'up'" class="text-white/70 mb-8">Talk to us — we'll help you figure out the right setup for your portfolio.</p>
        <RouterLink v-reveal="'up'" to="/contact" class="btn-primary bg-brand-500 hover:bg-brand-400 inline-flex">Book a Demo</RouterLink>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
const services = [
  {
    icon: '🏢', title: 'Property Management', color: '#0d9488',
    description: 'Manage apartments, houses, commercial buildings, offices, and estates from a single dashboard — with per-unit tracking, tenant history, and secure document storage.',
    items: ['Unlimited properties & units', 'Tenant & lease management', 'Automated rent escalation', 'Secure document vault with versioning'],
  },
  {
    icon: '🏨', title: 'Hotel Management', color: '#f59e0b',
    description: 'Manage reservations, guests, rooms, housekeeping, and payments for hotels, BnBs, and short-let apartments.',
    items: ['Room type & availability calendars', 'Guest booking & check-in', 'Dynamic seasonal pricing', 'Multi-property support'],
  },
  {
    icon: '🔧', title: 'Maintenance Marketplace', color: '#f97316',
    description: 'Connect property owners with verified technicians for plumbing, electrical, cleaning, and general maintenance work.',
    items: ['Verified provider badges', 'Job photo documentation', 'Automatic escalation if unassigned', 'Provider ratings & reviews'],
  },
  {
    icon: '💳', title: 'Digital Payments', color: '#6366f1',
    description: 'Accept and reconcile payments however your tenants and guests want to pay — no manual bank statement cross-checking.',
    items: ['M-Pesa STK push & paybill', 'Card & bank transfer', 'Auto-reconciliation to invoices', 'Wallet payouts to your M-Pesa'],
  },
  {
    icon: '📊', title: 'Reports & Analytics', color: '#8b5cf6',
    description: 'Real-time financial and operational reporting so you always know exactly where your portfolio stands.',
    items: ['Occupancy & vacancy dashboards', 'Revenue & cash flow reports', 'Tenant risk scoring', 'Maintenance cost breakdowns'],
  },
]
</script>
