<template>
  <AuthShell :title="$t('auth.welcomeBack')" :subtitle="$t('auth.signInPrompt')">
    <form @submit.prevent="handleLogin">
      <div>
        <label class="label">{{ $t('auth.emailAddress') }}</label>
        <input v-model="form.email" class="input" type="email" placeholder="you@example.com" required autocomplete="email" />
      </div>
      <div>
        <label class="label">{{ $t('auth.password') }}</label>
        <div class="fx-pw">
          <input v-model="form.password" class="input" :type="show ? 'text' : 'password'" placeholder="••••••••" required autocomplete="current-password" />
          <button type="button" :aria-label="show ? 'Hide password' : 'Show password'" @click="show = !show"><component :is="show ? EyeOff : Eye" /></button>
        </div>
      </div>

      <div v-if="error" class="fx-banner bad" role="alert"><div><b>{{ error }}</b></div></div>

      <button type="submit" class="fx-submit" :disabled="loading">
        <span v-if="loading" class="animate-spin w-5 h-5 border-2 border-current border-t-transparent rounded-full" />
        <span>{{ loading ? '…' : $t('auth.signIn') }}</span>
      </button>
    </form>
    <p class="text-center text-sm mt-5">
      {{ $t('auth.noAccount') }}
      <RouterLink :to="{ path: '/register', query: route.query }" class="fx-link-strong">{{ $t('auth.register') }}</RouterLink>
    </p>
  </AuthShell>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { Eye, EyeOff } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { roleHome, safeRedirect } from '@/router'
import AuthShell from '@/components/ui/AuthShell.vue'

const { t } = useI18n()
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const form = ref({ email: '', password: '' })
const show = ref(false)
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    const data = await auth.login(form.value.email, form.value.password)
    router.push(safeRedirect(route.query.redirect) ?? roleHome(data.user.role))
  } catch (e: any) {
    error.value = e?.response?.data?.error?.message || t('auth.invalidCredentials')
  } finally {
    loading.value = false
  }
}
</script>
