import { useEffect, useState } from 'react'
import { AccessibilityInfo } from 'react-native'

/** True when the user has asked the OS to reduce motion. Animations must be skipped when it is. */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false)
  useEffect(() => {
    let mounted = true
    AccessibilityInfo.isReduceMotionEnabled().then((v) => { if (mounted) setReduced(v) }).catch(() => {})
    const sub = AccessibilityInfo.addEventListener('reduceMotionChanged', setReduced)
    return () => { mounted = false; sub.remove() }
  }, [])
  return reduced
}
