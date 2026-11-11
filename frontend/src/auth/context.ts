import { createContext, useContext } from 'react'

import type { User } from './types'

export type AuthStatus = 'loading' | 'authenticated' | 'anonymous'

export interface AuthContextValue {
  status: AuthStatus
  user: User | null
  hasPermission: (code: string) => boolean
  logout: () => Promise<void>
  /** Relit /auth/me (après une modification du profil, par exemple). */
  reloadUser: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export const ME_QUERY_KEY = ['auth', 'me'] as const

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth doit être utilisé dans <AuthProvider>')
  return context
}
