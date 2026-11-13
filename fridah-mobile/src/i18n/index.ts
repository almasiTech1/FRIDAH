import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import AsyncStorage from '@react-native-async-storage/async-storage'
import { NativeModules, Platform } from 'react-native'
import en from './locales/en.json'
import sw from './locales/sw.json'

const STORAGE_KEY = 'fridah_locale'

function getDeviceLocale(): 'en' | 'sw' {
  try {
    const tag =
      Platform.OS === 'ios'
        ? NativeModules.SettingsManager?.settings?.AppleLocale ||
          NativeModules.SettingsManager?.settings?.AppleLanguages?.[0]
        : NativeModules.I18nManager?.localeIdentifier
    return typeof tag === 'string' && tag.toLowerCase().startsWith('sw') ? 'sw' : 'en'
  } catch {
    return 'en'
  }
}

i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, sw: { translation: sw } },
  lng: getDeviceLocale(),
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
})

// Restore a previously chosen language, overriding the device-locale guess above.
AsyncStorage.getItem(STORAGE_KEY).then((stored) => {
  if (stored === 'en' || stored === 'sw') i18n.changeLanguage(stored)
}).catch(() => {})

export async function setAppLocale(locale: 'en' | 'sw') {
  await i18n.changeLanguage(locale)
  await AsyncStorage.setItem(STORAGE_KEY, locale).catch(() => {})
}

export default i18n
