<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950 p-4">
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gray-900 dark:bg-white mb-4">
          <span class="text-white dark:text-gray-900 text-xl font-bold">F</span>
        </div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Set your own password</h1>
        <p class="text-gray-500 dark:text-gray-400 text-sm mt-1">
          You signed in with a temporary password issued by a FRIDAH administrator. Choose a new one to continue.
        </p>
      </div>

      <div class="card card-body dark:bg-gray-900 dark:border-gray-800">
        <form class="space-y-4" @submit.prevent="submit">
          <div>
            <label class="label dark:text-gray-300" for="cp-old">Temporary password</label>
            <input id="cp-old" v-model="form.old" class="input dark:bg-gray-800 dark:border-gray-700 dark:text-white" type="password" required autocomplete="current-password" />
          </div>
          <div>
            <label class="label dark:text-gray-300" for="cp-new">New password</label>
            <input id="cp-new" v-model="form.next" class="input dark:bg-gray-800 dark:border-gray-700 dark:text-white" type="password" required minlength="8" autocomplete="new-password" />
            <p class="text-xs text-gray-400 mt-1">At least 8 characters; not a common password or similar to your name or email.</p>
          </div>
          <div>
            <label class="label dark:text-gray-300" for="cp-confirm">Confirm new password</label>
            <input id="cp-confirm" v-model="form.confirm" class="input dark:bg-gray-800 dark:border-gray-700 dark:text-white" type="password" required autocomplete="new-password" />
          </div>

          <div v-if="error" class="p-3 bg-red-50 border border-red-100 rounded-lg text-sm text-red-700" role="alert">{{ error }}</div>

          <button type="submit" class="btn-primary w-full bg-gray-900 hover:bg-gray-700 justify-center" :disabled="saving">
            {{ saving ? 'Saving…' : 'Save and continue' }}
          </button>
          <button type="button" class="w-full text-sm text-gray-500 hover:text-gray-700" @click="signOut">Sign out</button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '@/api/services'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const form = ref({ old: '', next: '', confirm: '' })
const saving = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  if (form.value.next !== form.value.confirm) { error.value = 'The new passwords do not match.'; return }
  saving.value = true
  try {
    await authApi.changePassword(form.value.old, form.value.next)
    await auth.fetchMe()
    await auth.fetchAgencies()   // was refused while the temporary password was active
    router.replace('/login')     // guest guard sends signed-in users to their home portal
  } catch (e: any) {
    const d = e?.response?.data
    const pick = (v: any) => (Array.isArray(v) ? v.join(' ') : v)
    error.value = d?.error?.message || pick(d?.new_password) || pick(d?.old_password) || pick(d?.non_field_errors) || 'Could not change your password.'
  } finally { saving.value = false }
}

async function signOut() { await auth.logout(); router.replace('/login') }
</script>
