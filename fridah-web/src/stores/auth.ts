import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, agencyApi } from '@/api/services'
import { setTokens, clearTokens } from '@/api/client'
import type { User, Role, Agency } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const loading = ref(false)
  const agencies = ref<Agency[]>([])

  const isAuthenticated = computed(() => !!user.value)
  const role = computed((): Role | null => user.value?.role ?? null)
  const isKycVerified = computed(() => user.value?.is_kyc_verified ?? false)
  const isAgencyStaff = computed(() => agencies.value.length > 0)

  async function login(email: string, password: string) {
    loading.value = true
    try {
      const { data } = await authApi.login(email, password)
      setTokens(data.data.tokens.access, data.data.tokens.refresh)
      user.value = data.data.user
      await fetchAgencies()
      return data.data
    } finally {
      loading.value = false
    }
  }

  async function fetchAgencies() {
    try {
      const { data } = await agencyApi.list()
      agencies.value = (data as any).data?.results || (data as any).data || []
    } catch {
      agencies.value = []
    }
  }

  async function logout() {
    const refresh = localStorage.getItem('fridah_refresh') || ''
    try { await authApi.logout(refresh) } catch {}
    clearTokens()
    user.value = null
    agencies.value = []
  }

  async function fetchMe() {
    try {
      const { data } = await authApi.me()
      user.value = data.data
      await fetchAgencies()
    } catch {
      clearTokens()
      user.value = null
    }
  }

  async function register(payload: Record<string, unknown>) {
    loading.value = true
    try {
      const { data } = await authApi.register(payload)
      setTokens(data.data.tokens.access, data.data.tokens.refresh)
      user.value = data.data.user
      return data.data
    } finally {
      loading.value = false
    }
  }

  function hasRole(...roles: Role[]) {
    return !!user.value && roles.includes(user.value.role)
  }

  return {
    user, loading, agencies, isAuthenticated, role, isKycVerified, isAgencyStaff,
    login, logout, fetchMe, fetchAgencies, register, hasRole,
  }
})
