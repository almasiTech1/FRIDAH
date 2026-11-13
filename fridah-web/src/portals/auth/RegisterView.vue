<template>
  <AuthShell title="Create your account" subtitle="Join thousands on FRIDAH">
    <form @submit.prevent="handleRegister">
      <div class="grid grid-cols-2 gap-3">
        <div><label class="label">First name</label><input v-model="form.first_name" class="input" placeholder="John" required /></div>
        <div><label class="label">Last name</label><input v-model="form.last_name" class="input" placeholder="Doe" required /></div>
      </div>
      <div><label class="label">Username</label><input v-model="form.username" class="input" placeholder="johndoe" required /></div>
      <div><label class="label">Email</label><input v-model="form.email" class="input" type="email" placeholder="you@example.com" required /></div>
      <div><label class="label">Safaricom Phone (+254…)</label><input v-model="form.phone_number" class="input" placeholder="+254712345678" required /></div>
      <div>
        <label class="label">I am a…</label>
        <select v-model="form.role" class="input">
          <option value="tenant">Tenant (looking to rent)</option>
          <option value="landlord">Landlord (I own property)</option>
          <option value="service_provider">Service Provider</option>
          <option value="hotel_owner">Hotel / BnB Owner</option>
        </select>
      </div>
      <div v-if="form.role === 'service_provider'"><label class="label">Service Category</label><input v-model="form.service_category" class="input" placeholder="e.g. Plumber, Electrician" required /></div>
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="label">Password</label>
          <div class="fx-pw"><input v-model="form.password" class="input" :type="show ? 'text' : 'password'" placeholder="••••••••" required autocomplete="new-password" />
            <button type="button" :aria-label="show ? 'Hide password' : 'Show password'" @click="show = !show"><component :is="show ? EyeOff : Eye" /></button></div>
          <div class="fx-meter" aria-hidden="true"><i v-for="n in 4" :key="n" :style="n <= strength ? `background:${strengthColor[strength]}` : ''" /></div>
        </div>
        <div>
          <label class="label">Confirm password</label>
          <input v-model="form.password_confirm" class="input" :type="show ? 'text' : 'password'" placeholder="••••••••" required autocomplete="new-password" />
          <p v-if="mismatch" class="text-xs mt-1.5" style="color:#ef4444">Passwords don’t match</p>
        </div>
      </div>

      <div v-if="error" class="fx-banner bad" role="alert"><div><b>{{ error }}</b></div></div>

      <button type="submit" class="fx-submit" :disabled="loading || mismatch">
        <span v-if="loading" class="animate-spin w-5 h-5 border-2 border-current border-t-transparent rounded-full" />
        <span>{{ loading ? '…' : 'Create account' }}</span>
      </button>
    </form>
    <p class="text-center text-sm mt-5">Already have an account? <RouterLink :to="{ path: '/login', query: route.query }" class="fx-link-strong">Sign in</RouterLink></p>
  </AuthShell>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Eye, EyeOff } from 'lucide-vue-next'
import AuthShell from '@/components/ui/AuthShell.vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { roleHome, safeRedirect } from '@/router'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const form = ref({ first_name: '', last_name: '', username: '', email: '', phone_number: '+254', role: 'tenant', password: '', password_confirm: '', service_category: '' })
const show = ref(false)
const strength = computed(() => {
  const p = form.value.password
  return Math.min(4, (p.length >= 8 ? 1 : 0) + (/[A-Z]/.test(p) && /[a-z]/.test(p) ? 1 : 0) + (/\d/.test(p) ? 1 : 0) + (/[^A-Za-z0-9]/.test(p) ? 1 : 0))
})
const strengthColor = ['', '#ef4444', '#f59e0b', '#84cc16', '#22c55e']
const mismatch = computed(() => !!form.value.password_confirm && form.value.password !== form.value.password_confirm)
const loading = ref(false)
const error = ref('')

async function handleRegister() {
  error.value = ''
  loading.value = true
  try {
    const data = await auth.register(form.value)
    router.push(safeRedirect(route.query.redirect) ?? roleHome(data.user.role))
  } catch (e: any) {
    const errs = e?.response?.data?.error?.details
    error.value = errs ? Object.values(errs).flat().join(' ') : (e?.response?.data?.error?.message || 'Registration failed.')
  } finally {
    loading.value = false
  }
}
</script>
