<template>
  <div>
    <section class="max-w-5xl mx-auto px-6 pt-20 pb-14 text-center">
      <p v-reveal="'fade'" class="text-brand-600 dark:text-brand-400 font-semibold text-sm uppercase tracking-widest mb-3">Careers</p>
      <h1 v-reveal="'up'" class="text-4xl md:text-5xl font-black text-gray-900 dark:text-white">Build the future of property management</h1>
      <p v-reveal="'up'" class="mt-6 text-lg text-gray-500 dark:text-gray-400 max-w-2xl mx-auto">
        We're a small, remote-friendly team based in Nairobi, building tools that real landlords and hotel owners use every day.
      </p>
    </section>

    <section class="max-w-7xl mx-auto px-6 py-16">
      <div class="grid sm:grid-cols-2 md:grid-cols-4 gap-5">
        <div v-for="(b, i) in benefits" :key="b.title" v-reveal="'zoom'" :style="{ transitionDelay: `${i * 70}ms` }"
          class="text-center p-6 rounded-2xl bg-gray-50 dark:bg-gray-900/40 border border-gray-100 dark:border-gray-800">
          <div class="text-3xl mb-3">{{ b.icon }}</div>
          <p class="font-bold text-sm text-gray-900 dark:text-white mb-1">{{ b.title }}</p>
          <p class="text-xs text-gray-500 dark:text-gray-400">{{ b.desc }}</p>
        </div>
      </div>
    </section>

    <section class="max-w-4xl mx-auto px-6 py-16">
      <h2 v-reveal="'up'" class="text-3xl font-black text-gray-900 dark:text-white text-center mb-10">Open Positions</h2>
      <div class="space-y-3">
        <div
          v-for="(job, i) in jobs" :key="job.title" v-reveal="'up'" :style="{ transitionDelay: `${i * 60}ms` }"
          class="flex items-center justify-between p-5 rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 hover:shadow-card-hover transition-shadow duration-300"
        >
          <div>
            <p class="font-bold text-gray-900 dark:text-white">{{ job.title }}</p>
            <p class="text-sm text-gray-500 dark:text-gray-400">{{ job.dept }} · {{ job.location }} · {{ job.type }}</p>
          </div>
          <a :href="`mailto:careers@fridah.co.ke?subject=Application: ${encodeURIComponent(job.title)}`" class="btn-outline text-sm flex-shrink-0">Apply</a>
        </div>
        <p v-if="jobs.length === 0" class="text-center text-gray-400 py-10">No open positions right now — check back soon, or send us your CV anyway.</p>
      </div>
    </section>

    <section class="py-16 bg-gray-900 dark:bg-brand-950 text-center">
      <h2 v-reveal="'up'" class="text-2xl font-black text-white mb-3">Don't see a role that fits?</h2>
      <p v-reveal="'up'" class="text-white/70 mb-6 max-w-md mx-auto">We're always interested in hearing from great people. Send us your CV and tell us what you'd want to work on.</p>
      <a v-reveal="'up'" href="mailto:careers@fridah.co.ke" class="btn-primary bg-brand-500 hover:bg-brand-400 inline-flex">careers@fridah.co.ke</a>
    </section>
  </div>
</template>

<script setup lang="ts">
const benefits = [
  { icon: '🏡', title: 'Remote-friendly', desc: 'Work from anywhere in Kenya' },
  { icon: '💰', title: 'Competitive pay', desc: 'Market-rate salaries' },
  { icon: '📚', title: 'Learning budget', desc: 'Courses and conferences covered' },
  { icon: '🏥', title: 'Health cover', desc: 'Comprehensive medical insurance' },
]

const jobs = [
  { title: 'Backend Engineer (Django)', dept: 'Engineering', location: 'Nairobi / Remote', type: 'Full-time' },
  { title: 'Product Designer', dept: 'Design', location: 'Nairobi', type: 'Full-time' },
  { title: 'Customer Success Associate', dept: 'Support', location: 'Nairobi', type: 'Full-time' },
  { title: 'Mobile Engineer (React Native)', dept: 'Engineering', location: 'Remote', type: 'Contract' },
]
</script>
