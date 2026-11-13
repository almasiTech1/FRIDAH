import React, { useEffect, useState } from 'react'
import { View, ActivityIndicator, StyleSheet, Text } from 'react-native'
import { GestureHandlerRootView } from 'react-native-gesture-handler'
import { SafeAreaProvider } from 'react-native-safe-area-context'
import AsyncStorage from '@react-native-async-storage/async-storage'
import { RootNavigator } from '@/navigation/RootNavigator'
import { useAuthStore } from '@/stores/authStore'
import { useThemeStore } from '@/stores/themeStore'
import { colors } from '@/theme'
import { initPushNotifications } from '@/services/push'
import '@/i18n'

export default function App() {
  const { fetchMe, user } = useAuthStore()
  const { mode, init: initTheme } = useThemeStore()
  const [initializing, setInitializing] = useState(true)

  useEffect(() => {
    const bootstrap = async () => {
      try {
        await initTheme()
        const token = await AsyncStorage.getItem('fridah_access')
        if (token) await fetchMe()
      } catch {
        // No token or expired — will land on login
      } finally {
        setInitializing(false)
      }
    }
    bootstrap()
  }, [])

  // Push notifications need a logged-in user (to know their device token belongs
  // to them and where to route notification taps), so this fires once `user`
  // first becomes available rather than at cold-start.
  useEffect(() => {
    if (user) {
      initPushNotifications()
    }
  }, [user?.id])

  if (initializing) {
    return (
      <View style={styles.splash}>
        <View style={styles.logoBox}>
          <Text style={styles.logoText}>F</Text>
        </View>
        <Text style={styles.brandName}>FRIDAH</Text>
        <Text style={styles.tagline}>Kenya's Property Super App</Text>
        <ActivityIndicator size="small" color="rgba(255,255,255,0.6)" style={{ marginTop: 40 }} />
      </View>
    )
  }

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <RootNavigator />
      </SafeAreaProvider>
    </GestureHandlerRootView>
  )
}

const styles = StyleSheet.create({
  splash: {
    flex: 1,
    backgroundColor: '#111827',
    alignItems: 'center',
    justifyContent: 'center',
  },
  logoBox: {
    width: 80,
    height: 80,
    borderRadius: 24,
    backgroundColor: '#10b981',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 20,
    shadowColor: '#10b981',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.6,
    shadowRadius: 20,
    elevation: 10,
  },
  logoText: {
    color: colors.white,
    fontSize: 40,
    fontWeight: '900',
  },
  brandName: {
    color: colors.white,
    fontSize: 32,
    fontWeight: '900',
    letterSpacing: 4,
  },
  tagline: {
    color: 'rgba(255,255,255,0.45)',
    fontSize: 13,
    marginTop: 8,
    fontWeight: '500',
  },
})
