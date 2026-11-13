<template>
  <div>
    <section class="max-w-5xl mx-auto px-6 pt-20 pb-14 text-center">
      <p v-reveal="'fade'" class="text-brand-600 dark:text-brand-400 font-semibold text-sm uppercase tracking-widest mb-3">Pricing</p>
      <h1 v-reveal="'up'" class="text-4xl md:text-5xl font-black text-gray-900 dark:text-white">Simple, transparent pricing</h1>
      <p v-reveal="'up'" class="mt-6 text-lg text-gray-500 dark:text-gray-400 max-w-2xl mx-auto">
        Start free, upgrade as your portfolio grows. No hidden fees, no surprise charges.
      </p>
    </section>

    <section class="max-w-6xl mx-auto px-6 pb-24 grid md:grid-cols-3 gap-6 items-start">
      <div v-reveal="'up'"><PricingCard name="Starter" tagline="For individual landlords" price="Free" :features="starterFeatures" /></div>
      <div v-reveal="'zoom'"><PricingCard name="Professional" tagline="For growing portfolios" price="KES 4,500" period="/ month" :features="proFeatures" highlighted /></div>
      <div v-reveal="'up'"><PricingCard name="Enterprise" tagline="For large operators" price="Custom" :features="enterpriseFeatures" /></div>
    </section>

    <!-- Interactive calculator -->
    <section class="py-20 bg-gray-50 dark:bg-gray-900/40">
      <div class="max-w-3xl mx-auto px-6">
        <div v-reveal="'up'" class="text-center mb-10">
          <h2 class="text-3xl font-black text-gray-900 dark:text-white">Estimate your cost</h2>
          <p class="text-gray-500 dark:text-gray-400 mt-2">Drag the slider to see roughly what you'd pay per month.</p>
        </div>
        <div v-reveal="'zoom'" class="card card-body">
          <div class="flex items-center justify-between mb-2">
            <label class="label mb-0">Number of units</label>
            <span class="text-2xl font-black text-brand-600 dark:text-brand-400">{{ units }}</span>
          </div>
          <input type="range" min="1" max="500" v-model.number="units" class="w-full accent-brand-600 mb-8" />

          <div class="flex items-center gap-3 mb-8">
            <button
              v-for="opt in ['rental', 'hotel', 'both']" :key="opt"
              class="flex-1 py-2.5 rounded-xl text-sm font-semibold capitalize transition-colors"
              :class="portfolioType === opt ? 'bg-brand-600 text-white' : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300'"
              @click="portfolioType = opt as any"
            >
              {{ opt === 'both' ? 'Both' : opt }}
            </button>
          </div>

          <div class="rounded-2xl bg-brand-50 dark:bg-brand-950 p-6 flex items-center justify-between">
            <div>
              <p class="text-sm text-gray-500 dark:text-gray-400">Estimated plan</p>
              <p class="font-bold text-gray-900 dark:text-white">{{ recommendedPlan }}</p>
            </div>
            <div class="text-right">
              <p class="text-sm text-gray-500 dark:text-gray-400">Estimated monthly cost</p>
              <p class="text-2xl font-black text-brand-600 dark:text-brand-400">{{ formattedCost }}</p>
            </div>
          </div>
          <p class="text-xs text-gray-400 mt-4 text-center">This is an estimate only — final pricing is confirmed when you talk to sales.</p>
        </div>
      </div>
    </section>

    <section class="max-w-3xl mx-auto px-6 py-24">
      <h2 v-reveal="'up'" class="text-3xl font-black text-gray-900 dark:text-white text-center mb-10">Pricing questions</h2>
      <div v-reveal="'up'"><FaqAccordion :items="pricingFaqs" /></div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import PricingCard from '@/components/public/PricingCard.vue'
import FaqAccordion from '@/components/public/FaqAccordion.vue'

const starterFeatures = ['Up to 20 units', 'Basic reports', 'M-Pesa payments', 'Email support']
const proFeatures = ['Unlimited units', 'Hotel/BnB module', 'Advanced analytics', 'Maintenance marketplace', 'Priority support']
const enterpriseFeatures = ['Unlimited everything', 'Dedicated account manager', 'API integration', 'White-label option']

const units = ref(20)
const portfolioType = ref<'rental' | 'hotel' | 'both'>('rental')

const recommendedPlan = computed(() => {
  if (units.value <= 20 && portfolioType.value === 'rental') return 'Starter'
  if (units.value <= 150) return 'Professional'
  return 'Enterprise'
})

const estimatedCost = computed(() => {
  if (recommendedPlan.value === 'Starter') return 0
  if (recommendedPlan.value === 'Enterprise') return null // "Custom"
  const base = 4500
  const perUnit = portfolioType.value === 'both' ? 60 : 45
  return base + Math.max(units.value - 20, 0) * perUnit
})

const formattedCost = computed(() => {
  if (estimatedCost.value === null) return 'Custom pricing'
  if (estimatedCost.value === 0) return 'Free'
  return `KES ${estimatedCost.value.toLocaleString()}`
})

const pricingFaqs = [
  { q: 'Can I switch plans later?', a: 'Yes, you can upgrade or downgrade at any time from your account settings — changes take effect on your next billing cycle.' },
  { q: 'Is there a setup fee?', a: 'No setup fees on Starter or Professional plans. Enterprise onboarding is scoped individually depending on your integration needs.' },
  { q: 'Do you offer a free trial on Professional?', a: 'Yes, Professional includes a 14-day free trial with full feature access, no card required to start.' },
  { q: 'What payment methods do you accept for subscriptions?', a: 'M-Pesa, Visa, and Mastercard.' },
]
</script>
