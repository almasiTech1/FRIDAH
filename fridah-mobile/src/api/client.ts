import axios, {
  AxiosInstance,
  InternalAxiosRequestConfig,
  AxiosResponse,
} from 'axios'
import AsyncStorage from '@react-native-async-storage/async-storage'

// React Native doesn't provide Node's `process.env` types/runtime by default;
// Metro can inline process.env.X via babel-plugin-transform-inline-environment-variables
// if configured, but referencing it untyped broke under stricter TS. Fall back safely.
declare const process: { env?: Record<string, string | undefined> } | undefined
const BASE_URL =
  (typeof process !== 'undefined' && process?.env?.FRIDAH_API_URL) || 'https://api.fridah.co.ke/api/v1'

// ─── Token helpers ──────────────────────────────────────────────────────────
export const getAccessToken = async (): Promise<string | null> =>
  AsyncStorage.getItem('fridah_access')

export const getRefreshToken = async (): Promise<string | null> =>
  AsyncStorage.getItem('fridah_refresh')

export const setTokens = async (access: string, refresh: string) => {
  await AsyncStorage.setMany({
    fridah_access: access,
    fridah_refresh: refresh,
  })
}

export const clearTokens = async () => {
  await AsyncStorage.removeMany(['fridah_access', 'fridah_refresh'])
}

// ─── Axios instance ──────────────────────────────────────────────────────────
const api: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 20000,
  headers: { 'Content-Type': 'application/json' },
})

// Request interceptor — attach access token
api.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  const token = await getAccessToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Response interceptor — silent refresh on 401
let isRefreshing = false
let subscribers: ((token: string) => void)[] = []

const subscribeRefresh = (cb: (token: string) => void) =>
  subscribers.push(cb)
const onRefreshed = (token: string) => {
  subscribers.forEach(cb => cb(token))
  subscribers = []
}

api.interceptors.response.use(
  (res: AxiosResponse) => {
    // Plain DRF ListAPIViews (no custom envelope) return raw pagination
    // {count, next, previous, results}. Every call site expects the uniform
    // {success, data} envelope used by the rest of the API, so normalize here
    // rather than special-casing dozens of call sites. (Mirrors the same fix
    // applied to the web client.)
    const body = res.data
    if (body && typeof body === 'object' && 'results' in body && !('success' in body)) {
      res.data = { success: true, data: body }
    }
    return res
  },
  async error => {
    const original = error.config
    if (error.response?.status !== 401 || original._retry) {
      return Promise.reject(error)
    }
    const refreshToken = await getRefreshToken()
    if (!refreshToken) {
      await clearTokens()
      return Promise.reject(error)
    }
    if (isRefreshing) {
      return new Promise(resolve => {
        subscribeRefresh(token => {
          original.headers.Authorization = `Bearer ${token}`
          resolve(api(original))
        })
      })
    }
    original._retry = true
    isRefreshing = true
    try {
      const { data } = await axios.post(`${BASE_URL}/auth/refresh/`, {
        refresh: refreshToken,
      })
      const newAccess = data.access
      const newRefresh = data.refresh || refreshToken
      await setTokens(newAccess, newRefresh)
      onRefreshed(newAccess)
      original.headers.Authorization = `Bearer ${newAccess}`
      return api(original)
    } catch {
      await clearTokens()
      return Promise.reject(error)
    } finally {
      isRefreshing = false
    }
  },
)

export default api
