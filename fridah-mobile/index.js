/**
 * @format
 */
import { AppRegistry } from 'react-native'
import App from './App'
import { name as appName } from './app.json'
import { registerBackgroundHandler } from './src/services/push'

// Must run before AppRegistry.registerComponent so Firebase can deliver
// notifications while the app is fully backgrounded or killed. See the
// "Register the background push handler" section of NATIVE_SETUP.md.
// Wrapped defensively: if Firebase somehow isn't linked/configured yet in a
// given build, this must not prevent the app from launching at all.
try {
  registerBackgroundHandler()
} catch {
  // Push is a progressive enhancement — see src/services/push.ts.
}

AppRegistry.registerComponent(appName, () => App)
