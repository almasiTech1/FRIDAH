<template>
  <div>
    <section class="max-w-5xl mx-auto px-6 pt-20 pb-14 text-center">
      <p v-reveal="'fade'" class="text-brand-600 dark:text-brand-400 font-semibold text-sm uppercase tracking-widest mb-3">Blog</p>
      <h1 v-reveal="'up'" class="text-4xl md:text-5xl font-black text-gray-900 dark:text-white">Insights for property &amp; hotel managers</h1>
      <p v-reveal="'up'" class="mt-6 text-lg text-gray-500 dark:text-gray-400 max-w-2xl mx-auto">
        Practical guides on investment, compliance, payments, and running a better rental or hospitality business in Kenya.
      </p>
    </section>

    <section class="max-w-4xl mx-auto px-6 pb-10">
      <div class="flex flex-wrap gap-2 justify-center">
        <button
          v-for="cat in categories" :key="cat"
          class="px-4 py-2 rounded-full text-sm font-semibold transition-colors"
          :class="activeCategory === cat ? 'bg-brand-600 text-white' : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300'"
          @click="activeCategory = cat"
        >
          {{ cat }}
        </button>
      </div>
    </section>

    <section class="max-w-6xl mx-auto px-6 pb-24 grid md:grid-cols-2 lg:grid-cols-3 gap-6">
      <article
        v-for="(post, i) in filteredPosts" :key="post.title" v-reveal="'up'" :style="{ transitionDelay: `${(i % 6) * 60}ms` }"
        class="rounded-3xl overflow-hidden border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 hover:shadow-card-hover hover:-translate-y-1 transition-all duration-300"
      >
        <div class="aspect-video flex items-center justify-center text-5xl" :style="{ background: `${post.color}12` }">{{ post.emoji }}</div>
        <div class="p-6">
          <div class="flex items-center gap-2 text-xs text-gray-400 mb-2">
            <span class="font-semibold text-brand-600 dark:text-brand-400">{{ post.category }}</span>
            <span>·</span>
            <span>{{ post.date }}</span>
            <span>·</span>
            <span>{{ post.readTime }} read</span>
          </div>
          <h2 class="font-bold text-gray-900 dark:text-white mb-2 leading-snug">{{ post.title }}</h2>
          <p class="text-sm text-gray-500 dark:text-gray-400 leading-relaxed">{{ post.excerpt }}</p>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const categories = ['All', 'Investment', 'Hospitality', 'Tenant Rights', 'Tax & Compliance', 'Payments', 'Security']
const activeCategory = ref('All')

const posts = [
  { title: '5 signs a rental property is a good investment in Nairobi', category: 'Investment', emoji: '📈', color: '#0d9488', date: 'Jul 2026', readTime: '6 min', excerpt: 'Beyond location: the occupancy, escalation, and maintenance-cost signals that actually predict long-term returns.' },
  { title: 'Hotel management best practices for independent Kenyan hotels', category: 'Hospitality', emoji: '🏨', color: '#f59e0b', date: 'Jul 2026', readTime: '8 min', excerpt: 'How smaller hotels can compete on guest experience without the overhead of a chain-level operations team.' },
  { title: "Know your rights: a tenant's guide to deposits in Kenya", category: 'Tenant Rights', emoji: '⚖️', color: '#6366f1', date: 'Jun 2026', readTime: '5 min', excerpt: 'What landlords can and cannot deduct from your deposit, and how to document a fair move-out inspection.' },
  { title: 'Affordable Housing Levy: what landlords need to know for 2026', category: 'Tax & Compliance', emoji: '📋', color: '#8b5cf6', date: 'Jun 2026', readTime: '7 min', excerpt: 'A practical walkthrough of the levy, who it applies to, and how to keep your paperwork audit-ready.' },
  { title: 'M-Pesa payment guide: STK push vs paybill for rent collection', category: 'Payments', emoji: '💳', color: '#059669', date: 'May 2026', readTime: '6 min', excerpt: 'The trade-offs between the two most common M-Pesa collection methods, and how auto-reconciliation changes the calculus.' },
  { title: 'Security tips every landlord should share with new tenants', category: 'Security', emoji: '🔐', color: '#dc2626', date: 'May 2026', readTime: '4 min', excerpt: 'A simple move-in checklist covering locks, emergency contacts, and reporting suspicious activity.' },
]

const filteredPosts = computed(() =>
  activeCategory.value === 'All' ? posts : posts.filter((p) => p.category === activeCategory.value)
)
</script>
