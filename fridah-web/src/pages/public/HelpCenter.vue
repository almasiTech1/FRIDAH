<template>
  <div>
    <section class="max-w-5xl mx-auto px-6 pt-20 pb-10 text-center">
      <p v-reveal="'fade'" class="text-brand-600 dark:text-brand-400 font-semibold text-sm uppercase tracking-widest mb-3">Help Center</p>
      <h1 v-reveal="'up'" class="text-4xl md:text-5xl font-black text-gray-900 dark:text-white">How can we help?</h1>
      <div v-reveal="'up'" class="mt-8 max-w-xl mx-auto relative">
        <svg class="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0"/>
        </svg>
        <input v-model="query" placeholder="Search articles…" class="input pl-12 py-3.5 text-base" />
      </div>
    </section>

    <section class="max-w-6xl mx-auto px-6 py-10">
      <div class="grid sm:grid-cols-2 md:grid-cols-3 gap-5">
        <div
          v-for="(cat, i) in categories" :key="cat.title" v-reveal="'up'" :style="{ transitionDelay: `${(i % 6) * 60}ms` }"
          class="p-6 rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 hover:shadow-card-hover hover:-translate-y-1 transition-all duration-300 cursor-pointer"
          @click="activeCategory = cat.title"
        >
          <div class="text-3xl mb-3">{{ cat.icon }}</div>
          <h3 class="font-bold text-gray-900 dark:text-white mb-1">{{ cat.title }}</h3>
          <p class="text-sm text-gray-500 dark:text-gray-400">{{ cat.count }} articles</p>
        </div>
      </div>
    </section>

    <section class="max-w-3xl mx-auto px-6 py-16">
      <h2 v-reveal="'up'" class="text-2xl font-black text-gray-900 dark:text-white mb-8">
        {{ activeCategory ? activeCategory : 'Popular articles' }}
      </h2>
      <div v-reveal="'up'"><FaqAccordion :items="filteredArticles" /></div>
      <p v-if="filteredArticles.length === 0" class="text-center text-gray-400 py-10">No articles match your search.</p>
    </section>

    <section class="py-16 bg-gray-50 dark:bg-gray-900/40 text-center">
      <h2 v-reveal="'up'" class="text-2xl font-black text-gray-900 dark:text-white mb-3">Still need help?</h2>
      <p v-reveal="'up'" class="text-gray-500 dark:text-gray-400 mb-6">Our support team typically responds within a few hours.</p>
      <RouterLink v-reveal="'up'" to="/contact" class="btn-primary bg-brand-600 hover:bg-brand-700 inline-flex">Contact Support</RouterLink>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import FaqAccordion from '@/components/public/FaqAccordion.vue'

const query = ref('')
const activeCategory = ref('')

const categories = [
  { title: 'Getting Started', icon: '🚀', count: 8 },
  { title: 'Payments', icon: '💳', count: 12 },
  { title: 'Hotels', icon: '🏨', count: 6 },
  { title: 'Rentals', icon: '🏢', count: 10 },
  { title: 'Maintenance', icon: '🔧', count: 5 },
  { title: 'FAQs', icon: '❓', count: 15 },
]

const articles = [
  { category: 'Getting Started', q: 'How do I create my first property?', a: 'From your landlord dashboard, go to Properties → Add Property and fill in the location, unit count, and type. You can add individual units right after.' },
  { category: 'Getting Started', q: 'How do I invite a tenant to the platform?', a: 'When you create a lease, enter the tenant\'s phone number - they\'ll receive an SMS invite to download the app and complete registration.' },
  { category: 'Payments', q: 'How does paybill auto-reconciliation work?', a: 'Tenants pay to your paybill using their invoice number as the account reference. FRIDAH automatically matches the payment and updates the invoice within seconds.' },
  { category: 'Payments', q: 'How do I withdraw my wallet balance?', a: 'Go to Wallet → Request Payout, enter the amount and your M-Pesa number. Payouts are processed via M-Pesa B2C, usually within minutes.' },
  { category: 'Hotels', q: 'How do I set up room availability?', a: 'Add room types under your listing, set the total room count for each, then use the Availability Calendar to track bookings day by day.' },
  { category: 'Rentals', q: 'How does the lease renewal workflow work?', a: 'FRIDAH automatically creates a renewal offer 60 days before a lease ends and notifies your tenant. They can accept or decline with one tap in the app.' },
  { category: 'Maintenance', q: 'How do I assign a maintenance request to a provider?', a: 'Open the request from your Maintenance tab, choose a verified provider from the marketplace, and they\'ll be notified immediately.' },
  { category: 'FAQs', q: 'Is my data secure?', a: 'Yes - all data is encrypted in transit and at rest, with role-based access control and optional two-factor authentication.' },
]

const filteredArticles = computed(() => {
  let list = articles
  if (activeCategory.value) list = list.filter((a) => a.category === activeCategory.value)
  if (query.value.trim()) {
    const q = query.value.toLowerCase()
    list = list.filter((a) => a.q.toLowerCase().includes(q) || a.a.toLowerCase().includes(q))
  }
  return list
})
</script>
