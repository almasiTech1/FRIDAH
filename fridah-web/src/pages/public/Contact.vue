<template>
  <div>
    <section class="max-w-5xl mx-auto px-6 pt-20 pb-14 text-center">
      <p v-reveal="'fade'" class="text-brand-600 dark:text-brand-400 font-semibold text-sm uppercase tracking-widest mb-3">Contact Us</p>
      <h1 v-reveal="'up'" class="text-4xl md:text-5xl font-black text-gray-900 dark:text-white">We'd love to hear from you</h1>
      <p v-reveal="'up'" class="mt-6 text-lg text-gray-500 dark:text-gray-400 max-w-2xl mx-auto">
        Questions about pricing, a demo request, or support for an existing account — reach out any way that's convenient.
      </p>
    </section>

    <section class="max-w-6xl mx-auto px-6 pb-24 grid lg:grid-cols-5 gap-8">
      <div v-reveal="'left'" class="lg:col-span-3 card card-body">
        <h2 class="section-title">Send us a message</h2>
        <form v-if="!submitted" class="space-y-4" @submit.prevent="submit">
          <div class="grid sm:grid-cols-2 gap-4">
            <div><label class="label">Name</label><input v-model="form.name" required class="input" placeholder="Jane Wanjiku" /></div>
            <div><label class="label">Email</label><input v-model="form.email" type="email" required class="input" placeholder="jane@example.com" /></div>
          </div>
          <div class="grid sm:grid-cols-2 gap-4">
            <div><label class="label">Phone</label><input v-model="form.phone" class="input" placeholder="+254 7XX XXX XXX" /></div>
            <div>
              <label class="label">Subject</label>
              <select v-model="form.subject" class="input">
                <option>General Inquiry</option>
                <option>Request a Demo</option>
                <option>Pricing Question</option>
                <option>Technical Support</option>
                <option>Partnership</option>
              </select>
            </div>
          </div>
          <div><label class="label">Message</label><textarea v-model="form.message" required rows="5" class="input" placeholder="How can we help?" /></div>
          <button type="submit" class="btn-primary bg-brand-600 hover:bg-brand-700" :disabled="loading">
            {{ loading ? 'Sending…' : 'Send Message' }}
          </button>
        </form>
        <div v-else class="text-center py-10">
          <div class="text-4xl mb-3">✅</div>
          <p class="font-bold text-gray-900 dark:text-white">Message sent!</p>
          <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">We'll get back to you within one business day.</p>
        </div>
      </div>

      <div v-reveal="'right'" class="lg:col-span-2 space-y-4">
        <div class="card card-body flex items-start gap-4">
          <span class="text-2xl">📍</span>
          <div><p class="font-semibold text-gray-900 dark:text-white text-sm">Office</p><p class="text-sm text-gray-500 dark:text-gray-400">Westlands, Nairobi, Kenya</p></div>
        </div>
        <div class="card card-body flex items-start gap-4">
          <span class="text-2xl">📞</span>
          <div><p class="font-semibold text-gray-900 dark:text-white text-sm">Phone</p><a href="tel:+254700000000" class="text-sm text-brand-600 dark:text-brand-400 hover:underline">+254 700 000 000</a></div>
        </div>
        <div class="card card-body flex items-start gap-4">
          <span class="text-2xl">💬</span>
          <div><p class="font-semibold text-gray-900 dark:text-white text-sm">WhatsApp</p><a href="https://wa.me/254700000000" target="_blank" rel="noopener" class="text-sm text-brand-600 dark:text-brand-400 hover:underline">Chat with us</a></div>
        </div>
        <div class="card card-body flex items-start gap-4">
          <span class="text-2xl">✉️</span>
          <div><p class="font-semibold text-gray-900 dark:text-white text-sm">Email</p><a href="mailto:support@fridah.co.ke" class="text-sm text-brand-600 dark:text-brand-400 hover:underline">support@fridah.co.ke</a></div>
        </div>
        <div class="card card-body flex items-start gap-4">
          <span class="text-2xl">🕐</span>
          <div><p class="font-semibold text-gray-900 dark:text-white text-sm">Support Hours</p><p class="text-sm text-gray-500 dark:text-gray-400">Mon–Fri, 8am–6pm EAT</p></div>
        </div>
        <div class="rounded-2xl overflow-hidden h-52 border border-gray-100 dark:border-gray-800">
          <GoogleMapView :markers="officeMarker" :center="officeLocation" :zoom="14" minimal />
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import GoogleMapView from '@/components/public/GoogleMapView.vue'
import type { MapMarker } from '@/components/public/GoogleMapView.vue'

const officeLocation = { lat: -1.2648, lng: 36.8028 } // Westlands, Nairobi
const officeMarker: MapMarker[] = [
  { id: 'office', ...officeLocation, title: 'FRIDAH Office', subtitle: 'Westlands, Nairobi, Kenya' },
]

const form = ref({ name: '', email: '', phone: '', subject: 'General Inquiry', message: '' })
const loading = ref(false)
const submitted = ref(false)

async function submit() {
  loading.value = true
  // No contact-form backend endpoint exists yet - UI-complete stub.
  // Wire to a real endpoint (e.g. POST /api/v1/contact/) when available.
  await new Promise((r) => setTimeout(r, 700))
  loading.value = false
  submitted.value = true
}
</script>
