import { createContext, useContext } from 'react'

import type { AuthClient } from '../client/client'
import type { AuthConfig, AuthFeature, User } from '../client/types'
import type { AuthPaths } from './paths'

export type AuthStatus = 'loading' | 'authenticated' | 'anonymous'

export interface AuthContextValue {
  status: AuthStatus
  user: User | null
  hasPermission: (code: string) => boolean
  /** Fonctionnalités exposées par le backend (GET /auth/config). Toutes supposées actives tant que la config charge. */
  hasFeature: (feature: AuthFeature) => boolean
  config: AuthConfig | undefined
  logout: () => Promise<void>
  /** Relit /auth/me (après une modification du profil, par exemple). */
  reloadUser: () => Promise<void>
  client: AuthClient
  paths: AuthPaths
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export const ME_QUERY_KEY = ['auth', 'me'] as const
export const CONFIG_QUERY_KEY = ['auth-config'] as const
export const SESSIONS_QUERY_KEY = ['auth', 'sessions'] as const

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth doit être utilisé dans <AuthProvider>')
  return context
}

export function useAuthClient(): AuthClient {
  return useAuth().client
}

export function usePaths(): AuthPaths {
  return useAuth().paths
}
