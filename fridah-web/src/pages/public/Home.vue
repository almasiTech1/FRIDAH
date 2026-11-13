<template>
  <div>
    <!-- Hero -->
    <section class="relative overflow-hidden bg-gradient-to-b from-brand-50 via-white to-white dark:from-brand-950 dark:via-gray-950 dark:to-gray-950">
      <div class="absolute inset-0 bg-gradient-radial from-brand-100/40 dark:from-brand-900/20 via-transparent to-transparent" />
      <div class="relative max-w-7xl mx-auto px-6 pt-20 pb-24 md:pt-28 md:pb-32 text-center">
        <div v-reveal="'fade'" class="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-brand-100 dark:bg-brand-950 text-brand-700 dark:text-brand-300 text-xs font-semibold mb-6">
          🇰🇪 Built for Kenya's property market
        </div>
        <h1 v-reveal="'up'" class="text-4xl md:text-6xl font-black text-gray-900 dark:text-white leading-tight max-w-4xl mx-auto">
          Manage Properties, Hotels, Rentals &amp; Services from
          <span class="text-brand-600 dark:text-brand-400">One Smart Platform</span>
        </h1>
        <p v-reveal="'up'" class="mt-6 text-lg text-gray-500 dark:text-gray-400 max-w-2xl mx-auto leading-relaxed">
          Simplify property management with automated rent collection, hotel booking, maintenance tracking, financial reporting, and mobile payments — all in one secure platform.
        </p>
        <div v-reveal="'up'" class="mt-10 flex flex-wrap items-center justify-center gap-3">
          <RouterLink to="/register" class="btn-primary bg-brand-600 hover:bg-brand-700 text-base px-6 py-3.5">Get Started</RouterLink>
          <RouterLink to="/login" class="btn-outline text-base px-6 py-3.5">Login</RouterLink>
          <RouterLink to="/contact" class="btn-ghost text-base px-6 py-3.5">Book a Demo</RouterLink>
        </div>

        <!-- Hero photo -->
        <div v-reveal="'zoom'" class="mt-14 max-w-5xl mx-auto">
          <div class="rounded-3xl overflow-hidden shadow-2xl ring-1 ring-black/5 hero-float">
            <img :src="unsplashUrl(houseExteriors[0], 1600)" alt="Modern home managed on FRIDAH" class="w-full h-[280px] md:h-[440px] object-cover kenburns" fetchpriority="high" />
          </div>
        </div>

        <!-- Stats -->
        <div v-reveal="'up'" class="mt-20 grid grid-cols-2 md:grid-cols-4 gap-6 max-w-4xl mx-auto">
          <div v-for="s in stats" :key="s.label" class="glass-card p-6">
            <p class="text-3xl md:text-4xl font-black text-gray-900 dark:text-white">
              <AnimatedCounter :end="s.value" :suffix="s.suffix" :decimals="s.decimals" />
            </p>
            <p class="text-xs md:text-sm text-gray-500 dark:text-gray-400 mt-1">{{ s.label }}</p>
          </div>
        </div>
      </div>
    </section>

    <DashboardShowcase />

    <!-- Features Preview -->
    <section class="py-24 max-w-7xl mx-auto px-6">
      <div v-reveal="'up'" class="text-center max-w-2xl mx-auto mb-14">
        <h2 class="text-3xl md:text-4xl font-black text-gray-900 dark:text-white">Everything you need, in one place</h2>
        <p class="mt-3 text-gray-500 dark:text-gray-400">Six modules working together so nothing falls through the cracks.</p>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        <div v-for="(f, i) in features" :key="f.title" v-reveal="'up'" :style="{ transitionDelay: `${(i % 3) * 80}ms` }">
          <FeatureCard :icon="f.icon" :title="f.title" :description="f.description" :color="f.color" />
        </div>
      </div>
    </section>

    <!-- Find Your Area -->
    <AreaExplorer />

    <!-- Why Choose Us -->
    <!-- Photo showcase -->
    <section class="pb-24 max-w-7xl mx-auto px-6">
      <div v-reveal="'up'" class="text-center max-w-2xl mx-auto mb-10">
        <h2 class="text-3xl md:text-4xl font-black text-gray-900 dark:text-white">Every kind of property, one platform</h2>
        <p class="mt-3 text-gray-500 dark:text-gray-400">From city apartments to boutique hotels and short-stay homes.</p>
      </div>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div v-for="(c, i) in showcase" :key="c.label" v-reveal="'up'" :style="{ transitionDelay: `${i * 90}ms` }"
          class="group relative rounded-3xl overflow-hidden aspect-[3/4] cursor-pointer">
          <img :src="c.src" :alt="c.label" loading="lazy" class="absolute inset-0 w-full h-full object-cover group-hover:scale-110 transition-transform duration-700" />
          <div class="absolute inset-0 bg-gradient-to-t from-black/70 via-black/10 to-transparent"></div>
          <p class="absolute bottom-4 left-4 right-4 text-white font-bold text-lg translate-y-1 group-hover:translate-y-0 transition-transform duration-300">{{ c.label }}</p>
        </div>
      </div>
    </section>


    <section class="py-24 bg-gray-50 dark:bg-gray-900/40">
      <div class="max-w-7xl mx-auto px-6">
        <div v-reveal="'up'" class="text-center max-w-2xl mx-auto mb-14">
          <h2 class="text-3xl md:text-4xl font-black text-gray-900 dark:text-white">Why choose FRIDAH</h2>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-5">
          <div v-for="(w, i) in whyUs" :key="w.title" v-reveal="'zoom'" :style="{ transitionDelay: `${(i % 4) * 80}ms` }"
            class="text-center p-6 rounded-2xl bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800">
            <div class="text-3xl mb-3">{{ w.icon }}</div>
            <p class="font-semibold text-sm text-gray-900 dark:text-white">{{ w.title }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Testimonials -->
    <section class="py-24 max-w-7xl mx-auto px-6">
      <div v-reveal="'up'" class="text-center max-w-2xl mx-auto mb-14">
        <h2 class="text-3xl md:text-4xl font-black text-gray-900 dark:text-white">Loved by property &amp; hotel managers</h2>
      </div>
      <div v-reveal="'zoom'"><TestimonialCarousel :items="testimonials" /></div>
    </section>

    <!-- Partners -->
    <section class="py-16 border-y border-gray-100 dark:border-gray-800 overflow-hidden">
      <p class="text-center text-xs font-semibold uppercase tracking-widest text-gray-400 mb-8">Trusted payment &amp; technology partners</p>
      <div class="flex overflow-hidden">
        <div class="flex gap-16 animate-marquee whitespace-nowrap">
          <span v-for="p in [...partners, ...partners]" :key="p" class="text-xl font-bold text-gray-300 dark:text-gray-700">{{ p }}</span>
        </div>
      </div>
    </section>

    <!-- FAQ -->
    <section class="py-24 max-w-3xl mx-auto px-6">
      <div v-reveal="'up'" class="text-center mb-12">
        <h2 class="text-3xl md:text-4xl font-black text-gray-900 dark:text-white">Frequently asked questions</h2>
      </div>
      <div v-reveal="'up'"><FaqAccordion :items="faqs" /></div>
    </section>

    <!-- CTA -->
    <section class="py-24 max-w-7xl mx-auto px-6">
      <div v-reveal="'zoom'" class="relative overflow-hidden rounded-3xl bg-gray-900 dark:bg-brand-950 px-8 py-16 md:py-20 text-center">
        <div class="absolute inset-0 bg-gradient-radial from-brand-600/20 via-transparent to-transparent" />
        <h2 class="relative text-3xl md:text-4xl font-black text-white max-w-xl mx-auto">Ready to simplify your property management?</h2>
        <p class="relative mt-4 text-white/70 max-w-lg mx-auto">Join landlords and hotel owners across Kenya already running their business on FRIDAH.</p>
        <div class="relative mt-8 flex flex-wrap justify-center gap-3">
          <RouterLink to="/register" class="btn-primary bg-brand-500 hover:bg-brand-400 text-base px-6 py-3.5">Get Started Free</RouterLink>
          <RouterLink to="/contact" class="btn text-base px-6 py-3.5 border-2 border-white/20 text-white hover:bg-white/10">Contact Sales</RouterLink>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import DashboardShowcase from '@/components/public/DashboardShowcase.vue'
import AnimatedCounter from '@/components/public/AnimatedCounter.vue'
import FeatureCard from '@/components/public/FeatureCard.vue'
import TestimonialCarousel from '@/components/public/TestimonialCarousel.vue'
import FaqAccordion from '@/components/public/FaqAccordion.vue'
import AreaExplorer from '@/components/public/AreaExplorer.vue'
import { unsplashUrl, houseExteriors, livingInteriors, hotelRooms, kitchens } from '@/utils/stockImages'

const showcase = [
  { label: 'Apartments', src: unsplashUrl(houseExteriors[1], 700) },
  { label: 'Family Homes', src: unsplashUrl(livingInteriors[2], 700) },
  { label: 'Hotels & BnBs', src: unsplashUrl(hotelRooms[1], 700) },
  { label: 'Modern Kitchens', src: unsplashUrl(kitchens[0], 700) },
]

const stats = [
  { label: 'Properties Managed', value: 10000, suffix: '+' },
  { label: 'Monthly Transactions', value: 50000, suffix: '+' },
  { label: 'System Availability', value: 99.9, suffix: '%', decimals: 1 },
  { label: 'Customer Rating', value: 5, suffix: '/5' },
]

const features = [
  { icon: '🏢', title: 'Rental Management', description: 'Properties, tenants, leases, escalation, deposits, and digital agreements in one workflow.', color: '#0d9488' },
  { icon: '🏨', title: 'Hotel & Airbnb', description: 'Room booking, guest management, QR check-in, housekeeping, and dynamic pricing.', color: '#f59e0b' },
  { icon: '🔧', title: 'Maintenance', description: 'Requests, service marketplace, technician assignment, and inspection reports.', color: '#f97316' },
  { icon: '💳', title: 'Financial Management', description: 'M-Pesa integration, online payments, cash flow reports, and automated invoices.', color: '#6366f1' },
  { icon: '📊', title: 'Analytics', description: 'Occupancy dashboards, revenue analytics, AI insights, and performance reports.', color: '#8b5cf6' },
  { icon: '🔐', title: 'Security & Trust', description: 'Tenant screening, blacklist checks, secure document vaults, and two-factor login.', color: '#059669' },
]

const whyUs = [
  { icon: '🔒', title: 'Secure Payments' },
  { icon: '☁️', title: 'Cloud Based' },
  { icon: '📱', title: 'Mobile Friendly' },
  { icon: '⚡', title: 'Fast Performance' },
  { icon: '📈', title: 'Real-time Reporting' },
  { icon: '🇰🇪', title: 'Kenyan Compliance' },
  { icon: '🏘️', title: 'Hotel + Property in One System' },
  { icon: '🤝', title: 'Local Support Team' },
]

const testimonials = [
  { quote: "Managing over 300 apartments has never been easier. Rent reconciliation used to take my team two full days a month — now it's automatic.", name: 'Wanjiru Kamau', role: 'Property Manager, Nairobi' },
  { quote: "The booking system increased our hotel occupancy by 40%. The availability calendar alone has saved us from so many double-bookings.", name: 'David Otieno', role: 'Hotel Owner, Mombasa' },
  { quote: "My tenants pay through paybill and it just matches automatically. I used to spend hours cross-checking M-Pesa statements every month.", name: 'Grace Njoroge', role: 'Landlord, Kisumu' },
]

const partners = ['M-Pesa', 'Visa', 'Mastercard', 'Airtel Money', 'Safaricom', "Africa's Talking"]

const faqs = [
  { q: 'How does rent collection work?', a: 'Tenants pay via M-Pesa STK push, paybill, or card. Payments are automatically matched to the correct invoice and your wallet balance updates in real time.' },
  { q: 'Can I manage multiple properties?', a: 'Yes — landlords can manage an unlimited number of properties and units from a single dashboard, with per-property document vaults and reporting.' },
  { q: 'Does it support M-Pesa?', a: 'Yes, full Daraja API integration including STK push, paybill auto-reconciliation, and B2C payouts to your wallet.' },
  { q: 'Can hotels use the system?', a: 'Yes — FRIDAH includes a full hotel/BnB module with room types, availability calendars, guest bookings, and dynamic pricing.' },
  { q: 'Is data secure?', a: 'All data is encrypted in transit and at rest, with role-based access control and two-factor authentication available on every account.' },
]
</script>

<style scoped>
/* Gentle idle float on the hero photo + slow Ken Burns zoom - both disabled for reduced-motion users */
.hero-float { animation: hero-float 7s ease-in-out infinite; }
.kenburns { animation: kenburns 18s ease-in-out infinite alternate; }
@keyframes hero-float { 0%,100% { transform: translateY(0) } 50% { transform: translateY(-8px) } }
@keyframes kenburns { from { transform: scale(1) } to { transform: scale(1.08) } }
@media (prefers-reduced-motion: reduce) { .hero-float, .kenburns { animation: none } }
</style>
