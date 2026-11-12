/** Outils de test : un vrai client branché sur un faux backend (fetch simulé). */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import type { RouteObject } from 'react-router'

import { createAuthClient } from './client/client'
import type { AuthConfig, User } from './client/types'
import { AuthProvider } from './react/AuthProvider'
import type { AuthPaths } from './react/paths'

export const CONFIG: AuthConfig = {
  features: ['admin', 'devices', 'password_reset', 'register'],
  login_email_required: true,
  access_token_expire_seconds: 1800,
  login_link_expire_seconds: 900,
  password: { min_length: 8, max_bytes: 72, breach_check: false },
  username_pattern: '^[A-Za-z0-9_.-]{3,30}$',
}

export const ALICE: User = {
  id: 1,
  username: 'alice',
  email: 'alice@example.com',
  full_name: 'Alice Martin',
  is_verified: true,
  role: 'user',
  permissions: [],
}

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

export function fakeBackend({ user = null, config = CONFIG }: { user?: User | null; config?: AuthConfig } = {}) {
  return async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/auth/config')) return json(200, config)
    if (url.endsWith('/auth/refresh')) {
      return user
        ? json(200, { access_token: 'token', token_type: 'bearer', expires_in: 1800 })
        : json(401, { code: 'invalid_refresh_token', message: 'Session expirée.' })
    }
    if (url.endsWith('/auth/me')) return json(200, user)
    return json(404, { code: 'not_found', message: 'Ressource introuvable.' })
  }
}

export function renderApp({
  routes,
  initialPath,
  user = null,
  config = CONFIG,
  paths,
  wrap = (node) => node,
}: {
  routes: RouteObject[]
  initialPath: string
  user?: User | null
  config?: AuthConfig
  paths?: Partial<AuthPaths>
  wrap?: (node: ReactNode) => ReactNode
}) {
  const client = createAuthClient({ fetch: fakeBackend({ user, config }) as typeof fetch, channelName: null })
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createMemoryRouter(routes, { initialEntries: [initialPath] })
  const ui = (
    <QueryClientProvider client={queryClient}>
      <AuthProvider client={client} paths={paths}>
        {wrap(<RouterProvider router={router} />)}
      </AuthProvider>
    </QueryClientProvider>
  )
  return { ui, router, client }
}
