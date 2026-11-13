<template>
  <div class="max-w-3xl mx-auto px-6 pt-16 pb-24">
    <p v-reveal="'fade'" class="text-brand-600 dark:text-brand-400 font-semibold text-sm uppercase tracking-widest mb-3">Legal</p>
    <h1 v-reveal="'up'" class="text-4xl font-black text-gray-900 dark:text-white mb-2">Privacy Policy</h1>
    <p v-reveal="'up'" class="text-sm text-gray-400 mb-12">Last updated: July 2026</p>

    <div v-reveal="'up'" class="space-y-10">
      <section v-for="s in sections" :key="s.title">
        <h2 class="text-xl font-bold text-gray-900 dark:text-white mb-3">{{ s.title }}</h2>
        <p class="text-gray-600 dark:text-gray-300 leading-relaxed whitespace-pre-line">{{ s.body }}</p>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
const sections = [
  {
    title: '1. Data We Collect',
    body: `We collect information you provide directly, such as your name, phone number, email, national ID (for KYC verification), and property or booking details. We also collect payment transaction metadata (amounts, references, timestamps) from M-Pesa and other payment providers - we never store your M-Pesa PIN or card CVV.

We automatically collect device information, IP address, and usage data to keep the platform secure and improve performance.`,
  },
  {
    title: '2. How We Use Your Data',
    body: `Your data is used to operate the platform: processing rent and booking payments, matching maintenance requests to providers, computing tenant risk scores, sending notifications (SMS, WhatsApp, push, email), and complying with Kenyan tax and financial regulations.

We do not sell your personal data to third parties.`,
  },
  {
    title: '3. Cookies',
    body: `We use essential cookies to keep you logged in and remember your preferences (such as dark mode and language). We use limited analytics cookies to understand how the platform is used, so we can improve it. You can decline non-essential cookies via the banner shown on your first visit.`,
  },
  {
    title: '4. Data Sharing',
    body: `We share data with payment processors (Safaricom M-Pesa, card networks) strictly to process transactions, with SMS/WhatsApp providers (Africa's Talking, Meta) to deliver notifications you've opted into, and with law enforcement only when legally required.

Landlords and tenants on the platform can see limited information about each other necessary to complete a tenancy (e.g. name, phone number, payment history relevant to a specific lease).`,
  },
  {
    title: '5. Data Security',
    body: `All data is encrypted in transit (TLS) and at rest. Financial operations use database-level locking to prevent race conditions. Access to sensitive data (documents, KYC information) is restricted by role-based permissions and logged.`,
  },
  {
    title: '6. Your Rights',
    body: `You can request a copy of your data, ask us to correct inaccurate information, or request account deletion by contacting support@fridah.co.ke. Some data (e.g. transaction records) may be retained longer where required by Kenyan financial regulations.`,
  },
  {
    title: '7. Changes to This Policy',
    body: `We'll notify you by email or in-app notification of material changes to this policy before they take effect.`,
  },
  {
    title: '8. Contact Us',
    body: `Questions about this policy can be sent to privacy@fridah.co.ke or via our Contact page.`,
  },
]
</script>
