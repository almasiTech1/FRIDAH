<template>
  <div>
    <form v-if="!submitted" class="flex flex-col sm:flex-row gap-3" @submit.prevent="submit">
      <input
        v-model="email" type="email" required placeholder="Enter your email"
        class="flex-1 rounded-xl border-2 border-white/20 bg-white/10 px-4 py-3 text-sm text-white placeholder:text-white/50 focus:border-white/50 focus:ring-0 outline-none transition-colors"
      />
      <button type="submit" class="btn-primary bg-white text-brand-700 hover:bg-brand-50 justify-center whitespace-nowrap" :disabled="loading">
        {{ loading ? 'Subscribing…' : 'Subscribe' }}
      </button>
    </form>
    <p v-else class="text-sm text-white/90 flex items-center gap-2">
      <svg class="w-5 h-5 text-brand-200" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
      Thanks for subscribing! Check your inbox to confirm.
    </p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const email = ref('')
const loading = ref(false)
const submitted = ref(false)

async function submit() {
  loading.value = true
  // No newsletter backend endpoint exists yet - this is a UI-complete stub.
  // Wire to a real endpoint (e.g. POST /api/v1/newsletter/subscribe/) when available.
  await new Promise((r) => setTimeout(r, 600))
  loading.value = false
  submitted.value = true
}
</script>
