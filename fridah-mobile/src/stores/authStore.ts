import { create } from 'zustand'
import AsyncStorage from '@react-native-async-storage/async-storage'
import { authApi, agencyApi } from '@/api/services'
import { setTokens, clearTokens, getRefreshToken } from '@/api/client'
import type { User, Role, Agency } from '@/types'

interface AuthState {
  user: User | null
  loading: boolean
  initialized: boolean
  agencies: Agency[]
  login: (email: string, password: string) => Promise<User>
  logout: () => Promise<void>
  register: (data: Record<string, unknown>) => Promise<User>
  fetchMe: () => Promise<void>
  fetchAgencies: () => Promise<void>
  updateUser: (data: Partial<User>) => void
  isKycVerified: () => boolean
  isAgencyStaff: () => boolean
  hasRole: (...roles: Role[]) => boolean
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  loading: false,
  initialized: false,
  agencies: [],

  login: async (email, password) => {
    set({ loading: true })
    try {
      const { data } = await authApi.login(email, password)
      const { user, tokens } = data.data
      await setTokens(tokens.access, tokens.refresh)
      await AsyncStorage.setItem('fridah_user', JSON.stringify(user))
      set({ user, loading: false })
      await get().fetchAgencies()
      return user
    } catch (e) {
      set({ loading: false })
      throw e
    }
  },

  logout: async () => {
    const refresh = await getRefreshToken()
    if (refresh) {
      try { await authApi.logout(refresh) } catch {}
    }
    await clearTokens()
    await AsyncStorage.removeItem('fridah_user')
    set({ user: null, agencies: [] })
  },

  register: async (data) => {
    set({ loading: true })
    try {
      const { data: res } = await authApi.register(data)
      const { user, tokens } = res.data
      await setTokens(tokens.access, tokens.refresh)
      await AsyncStorage.setItem('fridah_user', JSON.stringify(user))
      set({ user, loading: false })
      return user
    } catch (e) {
      set({ loading: false })
      throw e
    }
  },

  fetchMe: async () => {
    try {
      const { data } = await authApi.me()
      const user = data.data
      await AsyncStorage.setItem('fridah_user', JSON.stringify(user))
      set({ user, initialized: true })
      await get().fetchAgencies()
    } catch {
      await clearTokens()
      set({ user: null, initialized: true })
    }
  },

  fetchAgencies: async () => {
    try {
      const { data } = await agencyApi.list()
      const agencies = (data as any).data?.results || (data as any).data || []
      set({ agencies })
    } catch {
      set({ agencies: [] })
    }
  },

  updateUser: (data) => {
    const current = get().user
    if (current) {
      const updated = { ...current, ...data }
      set({ user: updated })
      AsyncStorage.setItem('fridah_user', JSON.stringify(updated))
    }
  },

  isKycVerified: () => get().user?.is_kyc_verified ?? false,
  isAgencyStaff: () => get().agencies.length > 0,

  hasRole: (...roles) => {
    const role = get().user?.role
    return role ? roles.includes(role) : false
  },
}))
