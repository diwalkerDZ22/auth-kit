/**
 * Client de l'API auth-kit, sans React et sans état global : une instance par application.
 *
 *   const client = createAuthClient({ baseUrl: '/api' })
 *
 * - Access token en mémoire uniquement (jamais de localStorage).
 * - Refresh token dans un cookie httpOnly géré par le navigateur.
 * - Un 401 invalid_token déclenche un seul refresh partagé, puis la requête est rejouée.
 * - client.request() sert aussi pour les routes métier du projet (token ajouté, refresh géré).
 */
import { ApiError, networkError } from './errors'
import type {
  AccessToken,
  AdminUser,
  AdminUserList,
  AdminUserUpdate,
  AuthConfig,
  ClaimResult,
  LoginEmailSent,
  LoginResult,
  MessageResponse,
  RegisterPayload,
  RevokeOthersResponse,
  RevokeResponse,
  Role,
  User,
  UserSession,
  VerifyResponse,
} from './types'

export interface AuthClientOptions {
  /** Préfixe commun des appels (proxy du frontend ou URL de l'API). Défaut : "/api". */
  baseUrl?: string
  /** Préfixes montés par kit.install() côté backend. */
  authPrefix?: string
  adminPrefix?: string
  /** fetch à utiliser (tests, SSR). Défaut : globalThis.fetch. */
  fetch?: typeof fetch
  /** Canal de synchronisation entre onglets (déconnexion). null : désactivé. */
  channelName?: string | null
  /** Verrou partagé entre onglets pour le refresh (Web Locks API). */
  lockName?: string
  /** Refresh programmé ce délai avant l'expiration de l'access token. */
  refreshMarginMs?: number
}

export interface RequestOptions {
  method?: string
  json?: unknown
  form?: Record<string, string>
  query?: Record<string, string | number | boolean | undefined>
  headers?: Record<string, string>
  /** Ajoute le header CSRF (routes qui lisent le cookie). */
  csrf?: boolean
  /** false : ne tente pas de refresh sur un 401 invalid_token. */
  retryOnExpired?: boolean
}

export interface RawResponse<T> {
  status: number
  data: T
}

export type AuthClient = ReturnType<typeof createAuthClient>

const CSRF_HEADERS = { 'X-CSRF-Protection': '1' }

export function createAuthClient(options: AuthClientOptions = {}) {
  const baseUrl = (options.baseUrl ?? '/api').replace(/\/$/, '')
  const authPrefix = options.authPrefix ?? '/auth'
  const adminPrefix = options.adminPrefix ?? '/admin'
  const doFetch = options.fetch ?? ((input: RequestInfo | URL, init?: RequestInit) => globalThis.fetch(input, init))
  const lockName = options.lockName ?? 'auth-kit-refresh'
  const refreshMarginMs = options.refreshMarginMs ?? 60_000

  // --- Session en mémoire ------------------------------------------------------------------

  let accessToken: string | null = null
  let refreshTimer: ReturnType<typeof setTimeout> | undefined
  const listeners = new Set<() => void>()

  function notify() {
    listeners.forEach((listener) => listener())
  }

  function openSession(token: AccessToken) {
    accessToken = token.access_token
    clearTimeout(refreshTimer)
    const delay = Math.max(token.expires_in * 1000 - refreshMarginMs, 5_000)
    refreshTimer = setTimeout(() => void refreshSession(), delay)
    notify()
  }

  function closeSession() {
    clearTimeout(refreshTimer)
    if (accessToken === null) return
    accessToken = null
    notify()
  }

  const channelName = options.channelName === undefined ? 'auth-kit' : options.channelName
  const channel = channelName && typeof BroadcastChannel !== 'undefined' ? new BroadcastChannel(channelName) : null
  channel?.addEventListener('message', (event: MessageEvent) => {
    if (event.data === 'logout') closeSession()
  })

  // --- Requêtes ----------------------------------------------------------------------------

  async function send<T>(path: string, request: RequestOptions = {}): Promise<RawResponse<T>> {
    const headers: Record<string, string> = { ...request.headers }
    let body: BodyInit | undefined
    if (request.json !== undefined) {
      headers['Content-Type'] = 'application/json'
      body = JSON.stringify(request.json)
    } else if (request.form) {
      body = new URLSearchParams(request.form)
    }
    if (request.csrf) Object.assign(headers, CSRF_HEADERS)
    if (accessToken) headers.Authorization = `Bearer ${accessToken}`

    let url = `${baseUrl}${path}`
    if (request.query) {
      const params = new URLSearchParams()
      for (const [key, value] of Object.entries(request.query)) {
        if (value !== undefined && value !== '') params.set(key, String(value))
      }
      if (params.size) url += `?${params}`
    }

    let response: Response
    try {
      response = await doFetch(url, { method: request.method ?? 'GET', headers, body, credentials: 'include' })
    } catch {
      throw networkError()
    }

    const data = response.status === 204 ? null : await response.json().catch(() => null)
    if (response.ok) return { status: response.status, data: data as T }

    const error = new ApiError(
      response.status,
      data?.code ?? 'http_error',
      data?.message ?? 'Une erreur est survenue.',
      data?.fields ?? {},
    )
    // Access token expiré ou révoqué : un refresh, puis on rejoue la requête une fois
    if (error.code === 'invalid_token' && request.retryOnExpired !== false && (await refreshSession())) {
      return send<T>(path, { ...request, retryOnExpired: false })
    }
    throw error
  }

  async function request<T>(path: string, request?: RequestOptions): Promise<T> {
    return (await send<T>(path, request)).data
  }

  const auth = (path: string) => `${authPrefix}${path}`
  const admin = (path: string) => `${adminPrefix}${path}`
  const publicCall = { retryOnExpired: false }

  // --- Refresh partagé entre onglets ---------------------------------------------------------

  let refreshInFlight: Promise<boolean> | null = null

  /**
   * Un seul refresh à la fois pour tous les onglets (Web Locks API) : le cookie est partagé,
   * deux onglets qui le font tourner en même temps enverraient l'ancien token. Le backend
   * accepte aussi l'ancien token quelques secondes (refresh_reuse_grace_seconds), en filet.
   */
  function withRefreshLock<T>(task: () => Promise<T>): Promise<T> {
    if (typeof navigator !== 'undefined' && navigator.locks) return navigator.locks.request(lockName, task)
    return task()
  }

  /** Rouvre la session à partir du cookie. Un seul appel à la fois, partagé (onglet et navigateur). */
  function refreshSession(): Promise<boolean> {
    refreshInFlight ??= withRefreshLock(async () => {
      try {
        openSession(await request<AccessToken>(auth('/refresh'), { method: 'POST', csrf: true, ...publicCall }))
        return true
      } catch {
        closeSession()
        return false
      }
    }).finally(() => {
      refreshInFlight = null
    })
    return refreshInFlight
  }

  return {
    /** Appel authentifié vers n'importe quelle route (y compris les routes métier du projet). */
    request,
    /** Comme request, avec le statut HTTP (ex. distinguer 200 et 202). */
    send,
    refreshSession,

    session: {
      /** Pour useSyncExternalStore : l'UI se met à jour quand la session s'ouvre ou se ferme. */
      subscribe(listener: () => void) {
        listeners.add(listener)
        return () => {
          listeners.delete(listener)
        }
      },
      hasSession: () => accessToken !== null,
      getAccessToken: () => accessToken,
    },

    auth: {
      config: () => request<AuthConfig>(auth('/config'), publicCall),

      /** Même réponse que l'email soit libre ou déjà inscrit (le titulaire est prévenu par mail). */
      register: (payload: RegisterPayload) =>
        request<MessageResponse>(auth('/register'), { method: 'POST', json: payload, ...publicCall }),

      verify: (token: string) =>
        request<VerifyResponse>(auth('/verify'), { method: 'POST', json: { token }, ...publicCall }),

      /** « Ce n'est pas moi » : annule la demande de connexion du lien reçu par email. */
      denyLogin: (token: string) =>
        request<MessageResponse>(auth('/login/deny'), { method: 'POST', json: { token }, ...publicCall }),

      resendVerification: (email: string) =>
        request<MessageResponse>(auth('/resend-verification'), { method: 'POST', json: { email }, ...publicCall }),

      /** Étape 1 : le backend envoie un lien par email (ou ouvre la session en mode dev). */
      async login(username: string, password: string): Promise<LoginResult> {
        const { status, data } = await send<AccessToken | LoginEmailSent>(auth('/token'), {
          method: 'POST',
          form: { username, password },
          ...publicCall,
        })
        if (status === 202 && 'attempt_id' in data) {
          return { kind: 'email', attemptId: data.attempt_id, message: data.message }
        }
        openSession(data as AccessToken)
        return { kind: 'session' }
      },

      /** Étape 2 : la page interroge cette route jusqu'au clic sur le lien. */
      async claim(attemptId: string): Promise<ClaimResult> {
        const { status, data } = await send<AccessToken>(auth('/login/claim'), {
          method: 'POST',
          json: { attempt_id: attemptId },
          ...publicCall,
        })
        if (status === 202) return { kind: 'pending' }
        openSession(data)
        return { kind: 'session' }
      },

      async logout(): Promise<void> {
        try {
          await request<MessageResponse>(auth('/logout'), { method: 'POST', csrf: true, ...publicCall })
        } finally {
          closeSession()
          channel?.postMessage('logout')
        }
      },

      me: () => request<User>(auth('/me')),

      updateMe: (fullName: string | null) => request<User>(auth('/me'), { method: 'PATCH', json: { full_name: fullName } }),

      async changePassword(currentPassword: string, newPassword: string): Promise<void> {
        openSession(
          await request<AccessToken>(auth('/password/change'), {
            method: 'POST',
            json: { current_password: currentPassword, new_password: newPassword },
          }),
        )
      },

      forgotPassword: (email: string) =>
        request<MessageResponse>(auth('/password/forgot'), { method: 'POST', json: { email }, ...publicCall }),

      resetPassword: (token: string, newPassword: string) =>
        request<MessageResponse>(auth('/password/reset'), {
          method: 'POST',
          json: { token, new_password: newPassword },
          ...publicCall,
        }),

      listSessions: () => request<UserSession[]>(auth('/sessions')),

      /** Déconnecte un autre appareil (pour celui-ci : logout()). */
      revokeSession: (id: string) =>
        request<RevokeResponse>(auth(`/sessions/${encodeURIComponent(id)}`), { method: 'DELETE' }),

      revokeOtherSessions: () => request<RevokeOthersResponse>(auth('/sessions'), { method: 'DELETE' }),
    },

    admin: {
      listUsers: (params: { search?: string; limit: number; offset: number }) =>
        request<AdminUserList>(admin('/users'), { query: params }),

      updateUser: (id: number, changes: AdminUserUpdate) =>
        request<AdminUser>(admin(`/users/${id}`), { method: 'PATCH', json: changes }),

      listRoles: () => request<Role[]>(admin('/roles')),
    },

    /** Ferme le canal entre onglets et le minuteur (tests, démontage). */
    destroy() {
      clearTimeout(refreshTimer)
      channel?.close()
      listeners.clear()
    },
  }
}
