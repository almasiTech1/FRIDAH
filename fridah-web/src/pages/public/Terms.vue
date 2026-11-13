<template>
  <div class="max-w-3xl mx-auto px-6 pt-16 pb-24">
    <p v-reveal="'fade'" class="text-brand-600 dark:text-brand-400 font-semibold text-sm uppercase tracking-widest mb-3">Legal</p>
    <h1 v-reveal="'up'" class="text-4xl font-black text-gray-900 dark:text-white mb-2">Terms of Service</h1>
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
    title: '1. Acceptance of Terms',
    body: `By registering for or using FRIDAH, you agree to these Terms of Service. If you're using the platform on behalf of a company, you're confirming you have authority to bind that company to these terms.`,
  },
  {
    title: '2. User Responsibilities',
    body: `You're responsible for the accuracy of information you provide (property details, lease terms, pricing) and for keeping your account credentials secure. Landlords and hotel owners are responsible for complying with applicable Kenyan housing, tax, and consumer protection law for their listings.

You may not use the platform to post fraudulent listings, launder payments, or harass other users.`,
  },
  {
    title: '3. Payments',
    body: `FRIDAH facilitates payments via M-Pesa and other providers but is not a bank. Funds received into your platform wallet can be withdrawn to your registered M-Pesa number. A platform commission applies to processed transactions as disclosed in your pricing plan.

You're responsible for any taxes owed on income received through the platform.`,
  },
  {
    title: '4. Refund Policy',
    body: `Subscription fees are non-refundable except where required by law. Rent and booking payments are governed by the lease or booking agreement between the landlord/host and tenant/guest - FRIDAH is not a party to that agreement and does not arbitrate disputes over refunds, but provides transaction records to support resolution.`,
  },
  {
    title: '5. Account Suspension',
    body: `We may suspend or terminate accounts that violate these terms, engage in fraudulent activity, or pose a security risk to other users. Where possible, we'll provide notice and an opportunity to resolve the issue first.`,
  },
  {
    title: '6. Limitation of Liability',
    body: `FRIDAH is provided "as is." We work to maintain high availability and data accuracy but are not liable for indirect damages arising from service interruptions, third-party payment provider outages, or user error.`,
  },
  {
    title: '7. Legal Compliance',
    body: `This platform operates under the laws of Kenya. Any disputes will be resolved under Kenyan jurisdiction. We comply with the Data Protection Act, 2019 and applicable Central Bank of Kenya payment regulations.`,
  },
  {
    title: '8. Changes to These Terms',
    body: `We may update these terms from time to time. Continued use of the platform after changes take effect constitutes acceptance of the updated terms.`,
  },
]
</script>
