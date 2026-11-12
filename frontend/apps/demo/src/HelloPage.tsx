import { useQuery } from '@tanstack/react-query'

import { errorMessage } from '@auth-kit/react/client'
import { useAuthClient } from '@auth-kit/react/react'
import { Alert, Button, Section, Spinner } from '@auth-kit/react/ui'

/** Exemple : route métier du projet (GET /hello), appelée avec le client du kit (token et refresh gérés). */
export function HelloPage() {
  const client = useAuthClient()
  const hello = useQuery({ queryKey: ['demo', 'hello'], queryFn: () => client.request<{ message: string }>('/hello') })

  return (
    <div className="ak-scope ak-page">
      <div className="ak-page-header">
        <div>
          <h1 className="ak-page-title">API protégée</h1>
          <p className="ak-item-meta">
            <code>GET /hello</code> est une route du projet, protégée par <code>Depends(kit.current_user)</code>.
          </p>
        </div>
      </div>
      <Section
        title="Réponse du backend"
        description="client.request() ajoute l'access token et rafraîchit la session si besoin."
        footer={
          <Button variant="secondary" size="sm" loading={hello.isFetching} onClick={() => void hello.refetch()}>
            Rappeler
          </Button>
        }
      >
        {hello.isPending ? (
          <Spinner />
        ) : hello.isError ? (
          <Alert>{errorMessage(hello.error)}</Alert>
        ) : (
          <Alert tone="success">{hello.data.message}</Alert>
        )}
      </Section>
    </div>
  )
}
