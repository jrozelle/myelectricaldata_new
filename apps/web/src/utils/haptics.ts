/**
 * Haptic feedback utilities for touch interactions
 * Uses the Vibration API for supported devices
 */

type HapticPattern = 'light' | 'medium' | 'heavy' | 'selection' | 'success' | 'warning' | 'error'

const HAPTIC_PATTERNS: Record<HapticPattern, number | number[]> = {
  // Light tap (iOS style)
  light: 10,

  // Medium tap
  medium: 20,

  // Heavy tap
  heavy: 40,

  // Selection change (subtle)
  selection: 5,

  // Success feedback (double tap)
  success: [10, 50, 10],

  // Warning feedback (longer single)
  warning: 30,

  // Error feedback (three short)
  error: [10, 50, 10, 50, 10]
}

/**
 * Triggers haptic feedback if supported by the device
 * @param pattern - The type of haptic feedback to trigger
 */
export function triggerHaptic(pattern: HapticPattern = 'light'): void {
  // Check if the Vibration API is supported
  if (!navigator.vibrate) {
    return
  }

  // Check if user has reduced motion preference
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    return
  }

  const vibrationPattern = HAPTIC_PATTERNS[pattern]

  try {
    navigator.vibrate(vibrationPattern)
  } catch (error) {
    // Silently fail if vibration is not allowed or fails
    console.debug('Haptic feedback failed:', error)
  }
}

/**
 * Cancel any ongoing haptic feedback
 */
export function cancelHaptic(): void {
  if (navigator.vibrate) {
    navigator.vibrate(0)
  }
}

/**
 * Check if haptic feedback is supported
 */
export function isHapticSupported(): boolean {
  return 'vibrate' in navigator
}
