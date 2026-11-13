<template>
  <div>
    <section class="max-w-5xl mx-auto px-6 pt-20 pb-16 text-center">
      <p v-reveal="'fade'" class="text-brand-600 dark:text-brand-400 font-semibold text-sm uppercase tracking-widest mb-3">About FRIDAH</p>
      <h1 v-reveal="'up'" class="text-4xl md:text-5xl font-black text-gray-900 dark:text-white">Modernizing property management across Africa</h1>
      <p v-reveal="'up'" class="mt-6 text-lg text-gray-500 dark:text-gray-400 max-w-3xl mx-auto leading-relaxed">
        Our platform was built to modernize property management across Africa by combining rental management, hotel operations, maintenance services, and digital payments into one intelligent, cloud-based solution.
      </p>
    </section>

    <section class="max-w-7xl mx-auto px-6 py-16 grid md:grid-cols-2 gap-6">
      <div v-reveal="'left'" class="p-8 rounded-3xl bg-brand-50 dark:bg-brand-950 border border-brand-100 dark:border-brand-900">
        <div class="text-3xl mb-4">🎯</div>
        <h2 class="text-xl font-bold text-gray-900 dark:text-white mb-3">Our Mission</h2>
        <p class="text-gray-600 dark:text-gray-300 leading-relaxed">To simplify property and hospitality management through innovative technology built specifically for how business is actually done in Kenya — mobile-first, M-Pesa-native, and multilingual.</p>
      </div>
      <div v-reveal="'right'" class="p-8 rounded-3xl bg-gray-900 dark:bg-gray-900 border border-gray-800">
        <div class="text-3xl mb-4">🔭</div>
        <h2 class="text-xl font-bold text-white mb-3">Our Vision</h2>
        <p class="text-gray-300 leading-relaxed">To become Africa's leading smart property management ecosystem — the single platform landlords, hotel owners, tenants, and service providers all trust to run their side of the business.</p>
      </div>
    </section>

    <section class="py-20 bg-gray-50 dark:bg-gray-900/40">
      <div class="max-w-7xl mx-auto px-6">
        <h2 v-reveal="'up'" class="text-3xl font-black text-gray-900 dark:text-white text-center mb-12">Our Core Values</h2>
        <div class="grid grid-cols-2 md:grid-cols-5 gap-5">
          <div v-for="(v, i) in values" :key="v.title" v-reveal="'zoom'" :style="{ transitionDelay: `${i * 70}ms` }"
            class="text-center p-6 rounded-2xl bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800">
            <div class="text-3xl mb-3">{{ v.icon }}</div>
            <p class="font-bold text-sm text-gray-900 dark:text-white mb-1">{{ v.title }}</p>
            <p class="text-xs text-gray-500 dark:text-gray-400">{{ v.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <section class="max-w-7xl mx-auto px-6 py-20">
      <h2 v-reveal="'up'" class="text-3xl font-black text-gray-900 dark:text-white text-center mb-4">The story so far</h2>
      <p v-reveal="'up'" class="text-center text-gray-500 dark:text-gray-400 max-w-2xl mx-auto mb-14">
        Built by a team that has managed real Kenyan rental portfolios and hotels — and got tired of spreadsheets, WhatsApp groups, and manually cross-checking M-Pesa statements.
      </p>
      <div class="relative max-w-2xl mx-auto">
        <div class="absolute left-4 top-0 bottom-0 w-0.5 bg-brand-200 dark:bg-brand-900" />
        <div v-for="(m, i) in milestones" :key="m.title" v-reveal="'left'" :style="{ transitionDelay: `${i * 100}ms` }" class="relative pl-12 pb-10 last:pb-0">
          <div class="absolute left-0 w-8 h-8 rounded-full bg-brand-600 flex items-center justify-center text-white text-xs font-bold">{{ i + 1 }}</div>
          <p class="text-xs font-semibold text-brand-600 dark:text-brand-400 mb-1">{{ m.year }}</p>
          <h3 class="font-bold text-gray-900 dark:text-white">{{ m.title }}</h3>
          <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">{{ m.desc }}</p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
const values = [
  { icon: '💡', title: 'Innovation', desc: 'Always building what landlords actually need next.' },
  { icon: '🔍', title: 'Transparency', desc: 'Clear pricing, clear reporting, no hidden fees.' },
  { icon: '🛡️', title: 'Security', desc: 'Bank-grade encryption on every transaction.' },
  { icon: '🤝', title: 'Customer Success', desc: 'Your growth is how we measure ours.' },
  { icon: '⭐', title: 'Excellence', desc: 'Sweating the details that matter most.' },
]

const milestones = [
  { year: '2023', title: 'The idea', desc: 'Started as an internal tool for managing a small Nairobi rental portfolio.' },
  { year: '2024', title: 'M-Pesa integration', desc: 'Added full Daraja API support for STK push and paybill reconciliation.' },
  { year: '2025', title: 'Hotel module launch', desc: 'Expanded into hospitality with bookings, availability calendars, and dynamic pricing.' },
  { year: '2026', title: 'Full platform', desc: 'Service marketplace, tenant screening, USSD, and WhatsApp support for feature-phone users.' },
]
</script>
