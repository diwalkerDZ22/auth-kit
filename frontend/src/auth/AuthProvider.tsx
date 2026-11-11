import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useMemo, useState, useSyncExternalStore } from 'react'
import type { ReactNode } from 'react'

import { authApi, refreshSession, tokenStore } from './api'
import { AuthContext, ME_QUERY_KEY } from './context'
import type { AuthContextValue, AuthStatus } from './context'

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const hasSession = useSyncExternalStore(tokenStore.subscribe, tokenStore.hasSession)
  const [restored, setRestored] = useState(false)

  // Au chargement : le cookie httpOnly permet de retrouver la session sans se reconnecter
  useEffect(() => {
    let cancelled = false
    void refreshSession().finally(() => {
      if (!cancelled) setRestored(true)
    })
    return () => {
      cancelled = true
    }
  }, [])

  const me = useQuery({
    queryKey: ME_QUERY_KEY,
    queryFn: authApi.me,
    enabled: restored && hasSession,
    retry: false,
    staleTime: 5 * 60_000,
  })

  // Session fermée (logout, refresh refusé, autre onglet) : on oublie les données du compte
  useEffect(() => {
    if (!hasSession) queryClient.removeQueries({ queryKey: ['auth'] })
  }, [hasSession, queryClient])

  const user = hasSession ? (me.data ?? null) : null
  let status: AuthStatus = 'anonymous'
  if (!restored || (hasSession && me.isPending)) status = 'loading'
  else if (user) status = 'authenticated'

  const logout = useCallback(async () => {
    await authApi.logout()
    queryClient.clear()
  }, [queryClient])

  const reloadUser = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: ME_QUERY_KEY })
  }, [queryClient])

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      hasPermission: (code) => user?.permissions.includes(code) ?? false,
      logout,
      reloadUser,
    }),
    [status, user, logout, reloadUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
