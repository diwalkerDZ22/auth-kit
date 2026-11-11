import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'

import { useAuth } from './context'
import { Card, FullPageSpinner } from './components/ui'

/** Page réservée aux utilisateurs connectés ; sinon redirection vers /login?next=... */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth()
  const location = useLocation()
  if (status === 'loading') return <FullPageSpinner />
  if (status === 'anonymous') {
    const next = encodeURIComponent(location.pathname + location.search)
    return <Navigate to={`/login?next=${next}`} replace />
  }
  return <>{children}</>
}

/** Page réservée aux utilisateurs qui ont une permission (ex. "users:manage"). */
export function RequirePermission({ permission, children }: { permission: string; children: ReactNode }) {
  const { hasPermission } = useAuth()
  return (
    <RequireAuth>
      {hasPermission(permission) ? (
        children
      ) : (
        <Card title="Accès refusé" subtitle="Votre rôle ne donne pas accès à cette page.">
          <p className="text-sm text-slate-600">Permission requise : <code>{permission}</code></p>
        </Card>
      )}
    </RequireAuth>
  )
}

/** Pages de connexion / inscription : un utilisateur déjà connecté est renvoyé à l'accueil. */
export function GuestOnly({ children }: { children: ReactNode }) {
  const { status } = useAuth()
  if (status === 'loading') return <FullPageSpinner />
  if (status === 'authenticated') return <Navigate to="/" replace />
  return <>{children}</>
}
