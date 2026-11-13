import { createNavigationContainerRef } from '@react-navigation/native'

export const navigationRef = createNavigationContainerRef()

/** Navigate once the container has mounted; silently no-ops otherwise (e.g. app still on the splash screen). */
export function navigateSafely(name: string, params?: Record<string, unknown>) {
  if (navigationRef.isReady()) {
    // @ts-expect-error - route names are dynamic across the several role-specific navigators
    navigationRef.navigate(name, params)
  }
}
