import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'

import { useAuth } from './context'

interface GuardProps {
  children: ReactNode
  /** Affiché pendant la restauration de la session. */
  loading?: ReactNode
}

/** Page réservée aux utilisateurs connectés ; sinon redirection vers la page de connexion (?next=...). */
export function RequireAuth({ children, loading = null }: GuardProps) {
  const { status, paths } = useAuth()
  const location = useLocation()
  if (status === 'loading') return <>{loading}</>
  if (status === 'anonymous') {
    const next = encodeURIComponent(location.pathname + location.search)
    return <Navigate to={`${paths.login}?next=${next}`} replace />
  }
  return <>{children}</>
}

/** Page réservée aux utilisateurs qui ont une permission (ex. "users:manage"). */
export function RequirePermission({
  permission,
  children,
  fallback = null,
  loading = null,
}: GuardProps & { permission: string; fallback?: ReactNode }) {
  const { hasPermission } = useAuth()
  return (
    <RequireAuth loading={loading}>
      {hasPermission(permission) ? children : fallback}
    </RequireAuth>
  )
}

/** Pages de connexion / inscription : un utilisateur déjà connecté est renvoyé à l'accueil. */
export function GuestOnly({ children, loading = null }: GuardProps) {
  const { status, paths } = useAuth()
  if (status === 'loading') return <>{loading}</>
  if (status === 'authenticated') return <Navigate to={paths.home} replace />
  return <>{children}</>
}
