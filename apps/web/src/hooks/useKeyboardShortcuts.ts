import { useEffect, useCallback } from 'react'

export interface KeyboardShortcut {
  key: string
  ctrlKey?: boolean
  metaKey?: boolean
  shiftKey?: boolean
  altKey?: boolean
  description: string
  action: () => void
  preventDefault?: boolean
}

interface UseKeyboardShortcutsOptions {
  shortcuts: KeyboardShortcut[]
  enabled?: boolean
}

/**
 * Hook to manage keyboard shortcuts
 * @param options - Configuration with shortcuts array and enabled flag
 */
export function useKeyboardShortcuts({ shortcuts, enabled = true }: UseKeyboardShortcutsOptions) {
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) return

      // Ignore shortcuts when typing in input fields
      const target = event.target as HTMLElement
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        return
      }

      // Find matching shortcut
      const matchingShortcut = shortcuts.find((shortcut) => {
        const keyMatch = event.key.toLowerCase() === shortcut.key.toLowerCase()

        // For shortcuts without modifiers specified, ensure NO modifiers are pressed
        const ctrlMatch = shortcut.ctrlKey === undefined
          ? !event.ctrlKey
          : shortcut.ctrlKey === event.ctrlKey
        const metaMatch = shortcut.metaKey === undefined
          ? !event.metaKey
          : shortcut.metaKey === event.metaKey
        const shiftMatch = shortcut.shiftKey === undefined
          ? !event.shiftKey
          : shortcut.shiftKey === event.shiftKey
        const altMatch = shortcut.altKey === undefined
          ? !event.altKey
          : shortcut.altKey === event.altKey

        return keyMatch && ctrlMatch && metaMatch && shiftMatch && altMatch
      })

      if (matchingShortcut) {
        if (matchingShortcut.preventDefault !== false) {
          event.preventDefault()
        }
        matchingShortcut.action()
      }
    },
    [shortcuts, enabled]
  )

  useEffect(() => {
    if (!enabled) return

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown, enabled])

  return { shortcuts }
}

/**
 * Format shortcut for display
 * @param shortcut - Keyboard shortcut configuration
 * @returns Formatted string like "Ctrl+C" or "?"
 */
export function formatShortcut(shortcut: KeyboardShortcut): string {
  const parts: string[] = []

  if (shortcut.ctrlKey) parts.push('Ctrl')
  if (shortcut.metaKey) parts.push('Cmd')
  if (shortcut.altKey) parts.push('Alt')
  if (shortcut.shiftKey) parts.push('Shift')

  // Special key names
  const keyName =
    shortcut.key === ' '
      ? 'Space'
      : shortcut.key === 'Escape'
      ? 'Esc'
      : shortcut.key.length === 1
      ? shortcut.key.toUpperCase()
      : shortcut.key

  parts.push(keyName)

  return parts.join('+')
}
