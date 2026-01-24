/**
 * Hook to detect application mode (server vs client)
 *
 * In CLIENT mode:
 * - No login/signup pages
 * - No admin section
 * - No landing page (redirects to dashboard)
 * - Export configuration available
 * - Sync status monitoring
 *
 * In SERVER mode:
 * - Full authentication flow
 * - Admin section
 * - Landing page
 * - No export configuration
 */

export type AppMode = 'server' | 'client'

export interface AppModeInfo {
  mode: AppMode
  isClientMode: boolean
  isServerMode: boolean
}

export function useAppMode(): AppModeInfo {
  const mode: AppMode = import.meta.env.VITE_CLIENT_MODE === 'true' ? 'client' : 'server'

  return {
    mode,
    isClientMode: mode === 'client',
    isServerMode: mode === 'server',
  }
}

/**
 * Get app mode without hook (for use outside React components)
 */
export function getAppMode(): AppMode {
  return import.meta.env.VITE_CLIENT_MODE === 'true' ? 'client' : 'server'
}

export function isClientMode(): boolean {
  return import.meta.env.VITE_CLIENT_MODE === 'true'
}

export function isServerMode(): boolean {
  return import.meta.env.VITE_CLIENT_MODE !== 'true'
}
