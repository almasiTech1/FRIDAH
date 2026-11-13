import { defineStore } from 'pinia'

const STORAGE_KEY = 'fridah-theme'

function getInitialTheme(): 'light' | 'dark' {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'light' || stored === 'dark') return stored
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export const useThemeStore = defineStore('theme', {
  state: () => ({
    theme: getInitialTheme() as 'light' | 'dark',
  }),
  getters: {
    isDark: (state) => state.theme === 'dark',
  },
  actions: {
    apply() {
      document.documentElement.classList.toggle('dark', this.theme === 'dark')
    },
    toggle() {
      this.theme = this.theme === 'dark' ? 'light' : 'dark'
      localStorage.setItem(STORAGE_KEY, this.theme)
      this.apply()
    },
    init() {
      this.apply()
    },
  },
})
