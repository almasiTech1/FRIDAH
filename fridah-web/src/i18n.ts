import { createI18n } from 'vue-i18n'
import en from './locales/en.json'
import sw from './locales/sw.json'

const STORAGE_KEY = 'fridah-locale'

export function getInitialLocale(): 'en' | 'sw' {
  const stored = localStorage.getItem(STORAGE_KEY)
  return stored === 'sw' ? 'sw' : 'en'
}

export const i18n = createI18n({
  legacy: false,
  locale: getInitialLocale(),
  fallbackLocale: 'en',
  messages: { en, sw },
})

export function setLocale(locale: 'en' | 'sw') {
  ;(i18n.global.locale as any).value = locale
  localStorage.setItem(STORAGE_KEY, locale)
  document.documentElement.setAttribute('lang', locale)
}
