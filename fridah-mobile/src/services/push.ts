/**
 * FRIDAH push notifications (Firebase Cloud Messaging).
 *
 * IMPORTANT — this module is written against @react-native-firebase/messaging's
 * documented v26 modular API and passes TypeScript, but it has NOT been run on a
 * device or simulator. This repo snapshot has no ios/ or android/ native project
 * folders, so the native linking (CocoaPods, Gradle, google-services.json,
 * GoogleService-Info.plist, notification permission entries) that Firebase
 * requires simply doesn't exist here yet. See NATIVE_SETUP.md for the exact
 * steps needed before this can actually be built and tested.
 *
 * Background-message handling (`setBackgroundMessageHandler`) must be registered
 * at the top level of the JS bundle, before the app component renders — normally
 * in index.js. This repo has no index.js either (see NATIVE_SETUP.md), so
 * `registerBackgroundHandler()` is exported separately and documented for
 * whoever wires up that entry file.
 */
import { Platform } from 'react-native'
import AsyncStorage from '@react-native-async-storage/async-storage'
import {
  getMessaging, requestPermission, getToken, onMessage, onTokenRefresh,
  onNotificationOpenedApp, getInitialNotification, setBackgroundMessageHandler,
  AuthorizationStatus, registerDeviceForRemoteMessages,
} from '@react-native-firebase/messaging'
import { authApi } from '@/api/services'
import { useAuthStore } from '@/stores/authStore'
import { navigateSafely } from '@/navigation/navigationRef'

const DEVICE_ID_KEY = 'fridah_device_id'

interface ChatPushData {
  type?: string
  thread_id?: string
}

async function getOrCreateDeviceId(): Promise<string> {
  let id = await AsyncStorage.getItem(DEVICE_ID_KEY)
  if (!id) {
    id = `${Platform.OS}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
    await AsyncStorage.setItem(DEVICE_ID_KEY, id)
  }
  return id
}

/** Maps a chat message notification to the right role-specific Messages tab and its params. */
function chatMessageTarget(): { screen: string; params?: Record<string, unknown> } | null {
  const isAgencyStaff = useAuthStore.getState().isAgencyStaff()
  const role = useAuthStore.getState().user?.role
  if (isAgencyStaff) return { screen: 'AgencyMessages' }
  if (role === 'tenant') return { screen: 'TenantMessages' }
  if (role === 'landlord') return { screen: 'LandlordMessages' }
  if (role === 'service_provider') return { screen: 'ProviderMessages' }
  if (role === 'hotel_owner') return { screen: 'HotelMessages' }
  return null // admin chat screen hasn't been built yet
}

function handleNotificationTap(data: ChatPushData | undefined) {
  if (!data || data.type !== 'chat_message' || !data.thread_id) return
  const target = chatMessageTarget()
  if (!target) return
  navigateSafely(target.screen, { threadId: data.thread_id })
}

/**
 * Call once after a successful login/session restore (e.g. from App.tsx). Requests
 * notification permission, registers the device's FCM token with the backend
 * (POST /me/device/), and wires up foreground/background/quit-state tap handling.
 * Safe to call multiple times — later calls just refresh the registration.
 */
export async function initPushNotifications() {
  try {
    const messaging = getMessaging()

    const authStatus = await requestPermission(messaging)
    const enabled =
      authStatus === AuthorizationStatus.AUTHORIZED || authStatus === AuthorizationStatus.PROVISIONAL
    if (!enabled) return

    if (Platform.OS === 'ios') {
      // Required on iOS before requesting a token.
      await registerDeviceForRemoteMessages(messaging)
    }

    const token = await getToken(messaging)
    const deviceId = await getOrCreateDeviceId()
    await authApi.registerDevice(deviceId, token, Platform.OS)

    onTokenRefresh(messaging, async (newToken) => {
      try {
        await authApi.registerDevice(deviceId, newToken, Platform.OS)
      } catch {
        // Best-effort — the next app open will retry via initPushNotifications().
      }
    })

    // Foreground: the OS won't show a banner automatically, so at minimum this is
    // where an in-app toast/badge-refresh would hook in. Kept deliberately quiet
    // (no Alert popup) so a chat notification doesn't interrupt whatever the
    // person is doing; the unread badge on the Messages tab reflects it instead.
    onMessage(messaging, async () => {
      // Intentionally minimal — no native local-notification library is wired up
      // yet for foreground display. See NATIVE_SETUP.md.
    })

    // App was backgrounded (not quit) and the person tapped the notification.
    onNotificationOpenedApp(messaging, (remoteMessage) => {
      handleNotificationTap(remoteMessage.data as ChatPushData | undefined)
    })

    // App was fully quit and opened via tapping the notification.
    const initialMessage = await getInitialNotification(messaging)
    if (initialMessage) {
      handleNotificationTap(initialMessage.data as ChatPushData | undefined)
    }
  } catch {
    // Push is a progressive enhancement — never block login/app usage if it fails
    // (e.g. Firebase not linked natively yet, permission denied, emulator without
    // Play Services, etc).
  }
}

/**
 * Registers the background message handler. Firebase requires this to be called
 * at the top level of the JS bundle (outside any component), before AppRegistry
 * registers the root component — conventionally in index.js. Import and call this
 * from that file once it exists (see NATIVE_SETUP.md); it is *not* called from
 * App.tsx because by then it would already be too late for Firebase to pick it up
 * reliably for the fully-backgrounded/killed-app case.
 */
export function registerBackgroundHandler() {
  const messaging = getMessaging()
  setBackgroundMessageHandler(messaging, async () => {
    // No local work needed here today — the message already carries its own
    // OS-rendered notification (title/body) from the backend's FCM payload, and
    // tap handling is covered by onNotificationOpenedApp / getInitialNotification
    // above. This handler exists so Firebase considers background delivery
    // "handled" rather than logging a warning.
  })
}
