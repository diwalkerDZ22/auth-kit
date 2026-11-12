import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useMemo, useState, useSyncExternalStore } from 'react'
import type { ReactNode } from 'react'

import type { AuthClient } from '../client/client'
import { AuthContext, CONFIG_QUERY_KEY, ME_QUERY_KEY } from './context'
import type { AuthContextValue, AuthStatus } from './context'
import { resolvePaths } from './paths'
import type { AuthPaths } from './paths'

export interface AuthProviderProps {
  client: AuthClient
  paths?: Partial<AuthPaths>
  children: ReactNode
}

/** À placer dans un <QueryClientProvider>. */
export function AuthProvider({ client, paths, children }: AuthProviderProps) {
  const queryClient = useQueryClient()
  const hasSession = useSyncExternalStore(client.session.subscribe, client.session.hasSession)
  const [restored, setRestored] = useState(false)
  const resolvedPaths = useMemo(() => resolvePaths(paths), [paths])

  // Au chargement : le cookie httpOnly permet de retrouver la session sans se reconnecter
  useEffect(() => {
    let cancelled = false
    void client.refreshSession().finally(() => {
      if (!cancelled) setRestored(true)
    })
    return () => {
      cancelled = true
    }
  }, [client])

  const config = useQuery({ queryKey: CONFIG_QUERY_KEY, queryFn: client.auth.config, staleTime: Infinity, retry: 1 })

  const me = useQuery({
    queryKey: ME_QUERY_KEY,
    queryFn: client.auth.me,
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
    await client.auth.logout()
    queryClient.removeQueries({ queryKey: ['auth'] })
    queryClient.removeQueries({ queryKey: ['admin'] })
  }, [client, queryClient])

  const reloadUser = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: ME_QUERY_KEY })
  }, [queryClient])

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      hasPermission: (code) => user?.permissions.includes(code) ?? false,
      hasFeature: (feature) => config.data?.features.includes(feature) ?? true,
      config: config.data,
      logout,
      reloadUser,
      client,
      paths: resolvedPaths,
    }),
    [status, user, config.data, logout, reloadUser, client, resolvedPaths],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
