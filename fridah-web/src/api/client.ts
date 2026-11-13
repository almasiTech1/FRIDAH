import axios, { type AxiosInstance, type InternalAxiosRequestConfig, type AxiosResponse } from 'axios'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://api.fridah.co.ke/api/v1'

// ---------- Token helpers ----------
export const getAccessToken = () => localStorage.getItem('fridah_access')
export const getRefreshToken = () => localStorage.getItem('fridah_refresh')
export const setTokens = (access: string, refresh: string) => {
  localStorage.setItem('fridah_access', access)
  localStorage.setItem('fridah_refresh', refresh)
}
export const clearTokens = () => {
  localStorage.removeItem('fridah_access')
  localStorage.removeItem('fridah_refresh')
}

// ---------- Axios instance ----------
const api: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 20000,
  headers: { 'Content-Type': 'application/json' },
})

// Request interceptor — attach access token
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getAccessToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Response interceptor — silent token refresh on 401
let isRefreshing = false
let refreshSubscribers: ((token: string) => void)[] = []

const subscribeTokenRefresh = (cb: (token: string) => void) => refreshSubscribers.push(cb)
const onRefreshed = (token: string) => { refreshSubscribers.forEach(cb => cb(token)); refreshSubscribers = [] }

api.interceptors.response.use(
  (response: AxiosResponse) => {
    // Plain DRF ListAPIViews (no custom envelope) return raw pagination:
    // {count, next, previous, results}. Every frontend call site expects the
    // uniform {success, data} envelope used by the rest of the API, so normalize
    // that shape here rather than special-casing dozens of call sites.
    const body = response.data
    if (body && typeof body === 'object' && 'results' in body && !('success' in body)) {
      response.data = { success: true, data: body }
    }
    return response
  },
  async (error) => {
    const original = error.config
    if (error.response?.status !== 401 || original._retry) return Promise.reject(error)
    if (!getRefreshToken()) {
      clearTokens()
      window.location.href = '/login'
      return Promise.reject(error)
    }
    if (isRefreshing) {
      return new Promise((resolve) => {
        subscribeTokenRefresh((token) => {
          original.headers.Authorization = `Bearer ${token}`
          resolve(api(original))
        })
      })
    }
    original._retry = true
    isRefreshing = true
    try {
      const { data } = await axios.post(`${BASE_URL}/auth/refresh/`, { refresh: getRefreshToken() })
      setTokens(data.access, data.refresh || getRefreshToken()!)
      onRefreshed(data.access)
      original.headers.Authorization = `Bearer ${data.access}`
      return api(original)
    } catch {
      clearTokens()
      window.location.href = '/login'
      return Promise.reject(error)
    } finally {
      isRefreshing = false
    }
  }
)

export default api

// ---------- Reusable CRUD helper ----------
export function createCrudService<T>(path: string) {
  return {
    list: (params?: Record<string, unknown>) => api.get<{ success: boolean; data: { results: T[] } }>(path, { params }),
    get: (id: string) => api.get<{ success: boolean; data: T }>(`${path}${id}/`),
    create: (data: Partial<T>) => api.post<{ success: boolean; data: T }>(path, data),
    update: (id: string, data: Partial<T>) => api.patch<{ success: boolean; data: T }>(`${path}${id}/`, data),
    delete: (id: string) => api.delete(`${path}${id}/`),
  }
}
