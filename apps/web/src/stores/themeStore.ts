import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type ThemeMode = 'light' | 'dark' | 'system'

interface ThemeState {
  mode: ThemeMode
  isDark: boolean
  toggleTheme: () => void
  setTheme: (isDark: boolean) => void
  setMode: (mode: ThemeMode) => void
}

const getSystemPreference = (): boolean => {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

const applyTheme = (mode: ThemeMode): boolean => {
  const isDark = mode === 'system' ? getSystemPreference() : mode === 'dark'
  document.documentElement.classList.toggle('dark', isDark)
  return isDark
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      mode: 'system',
      isDark: false,
      toggleTheme: () =>
        set((state) => {
          const newIsDark = !state.isDark
          document.documentElement.classList.toggle('dark', newIsDark)
          return { isDark: newIsDark, mode: newIsDark ? 'dark' : 'light' }
        }),
      setTheme: (isDark) => {
        document.documentElement.classList.toggle('dark', isDark)
        set({ isDark, mode: isDark ? 'dark' : 'light' })
      },
      setMode: (mode) => {
        const isDark = applyTheme(mode)
        set({ mode, isDark })
      },
    }),
    {
      name: 'theme-storage',
      onRehydrateStorage: () => (state) => {
        if (state) {
          const isDark = applyTheme(state.mode)
          state.isDark = isDark
        }
      },
    }
  )
)

// Listen for system theme changes
if (typeof window !== 'undefined') {
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    const state = useThemeStore.getState()
    if (state.mode === 'system') {
      document.documentElement.classList.toggle('dark', e.matches)
      useThemeStore.setState({ isDark: e.matches })
    }
  })
}
