import { create } from 'zustand'
import AsyncStorage from '@react-native-async-storage/async-storage'
import { Appearance } from 'react-native'

const STORAGE_KEY = 'fridah_theme_mode'

interface ThemeState {
  mode: 'light' | 'dark'
  initialized: boolean
  init: () => Promise<void>
  toggle: () => void
  setMode: (mode: 'light' | 'dark') => void
}

export const useThemeStore = create<ThemeState>((set, get) => ({
  mode: 'light',
  initialized: false,

  init: async () => {
    try {
      const stored = await AsyncStorage.getItem(STORAGE_KEY)
      if (stored === 'light' || stored === 'dark') {
        set({ mode: stored, initialized: true })
        return
      }
    } catch {
      // fall through to OS preference
    }
    const osScheme = Appearance.getColorScheme()
    set({ mode: osScheme === 'dark' ? 'dark' : 'light', initialized: true })
  },

  toggle: () => {
    const next = get().mode === 'dark' ? 'light' : 'dark'
    set({ mode: next })
    AsyncStorage.setItem(STORAGE_KEY, next).catch(() => {})
  },

  setMode: (mode) => {
    set({ mode })
    AsyncStorage.setItem(STORAGE_KEY, mode).catch(() => {})
  },
}))
