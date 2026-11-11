/**
 * Client de l'API auth-kit.
 *
 * - Access token en mémoire uniquement (jamais de localStorage).
 * - Refresh token dans un cookie httpOnly géré par le navigateur.
 * - Un 401 invalid_token déclenche un seul refresh partagé, puis la requête est rejouée.
 */
import { ApiError, NETWORK_ERROR } from './errors'
import type {
  AccessToken,
  AdminUser,
  AdminUserList,
  ClaimResult,
  LoginResult,
  MessageResponse,
  RegisterPayload,
  Role,
  User,
  VerifyResponse,
} from './types'

const API_BASE: string = import.meta.env.VITE_API_BASE ?? '/api'
const CSRF_HEADERS = { 'X-CSRF-Protection': '1' }
/** Refresh programmé une minute avant l'expiration de l'access token. */
const REFRESH_MARGIN_MS = 60_000

// --- Stockage en mémoire de l'access token -------------------------------------------------

let accessToken: string | null = null
let refreshTimer: ReturnType<typeof setTimeout> | undefined
const listeners = new Set<() => void>()

function notify() {
  listeners.forEach((listener) => listener())
}

/** Pour useSyncExternalStore : l'UI se met à jour quand la session s'ouvre ou se ferme. */
export const tokenStore = {
  subscribe(listener: () => void) {
    listeners.add(listener)
    return () => listeners.delete(listener)
  },
  hasSession: () => accessToken !== null,
}

function openSession(token: AccessToken) {
  accessToken = token.access_token
  clearTimeout(refreshTimer)
  const delay = Math.max(token.expires_in * 1000 - REFRESH_MARGIN_MS, 5_000)
  refreshTimer = setTimeout(() => void refreshSession(), delay)
  notify()
}

function closeSession() {
  clearTimeout(refreshTimer)
  if (accessToken === null) return
  accessToken = null
  notify()
}

// --- Synchronisation entre onglets ----------------------------------------------------------

const channel = typeof BroadcastChannel !== 'undefined' ? new BroadcastChannel('auth-kit') : null
channel?.addEventListener('message', (event) => {
  if (event.data === 'logout') closeSession()
})

// --- Requêtes --------------------------------------------------------------------------------

interface RequestOptions {
  method?: string
  json?: unknown
  form?: Record<string, string>
  query?: Record<string, string | number | undefined>
  csrf?: boolean
  /** false : ne tente pas de refresh sur un 401 (routes publiques, refresh lui-même). */
  retryOnExpired?: boolean
}

interface RawResponse<T> {
  status: number
  data: T
}

async function send<T>(path: string, options: RequestOptions = {}): Promise<RawResponse<T>> {
  const headers: Record<string, string> = {}
  let body: BodyInit | undefined
  if (options.json !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(options.json)
  } else if (options.form) {
    body = new URLSearchParams(options.form)
  }
  if (options.csrf) Object.assign(headers, CSRF_HEADERS)
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`

  let url = `${API_BASE}${path}`
  if (options.query) {
    const params = new URLSearchParams()
    for (const [key, value] of Object.entries(options.query)) {
      if (value !== undefined && value !== '') params.set(key, String(value))
    }
    if (params.size) url += `?${params}`
  }

  let response: Response
  try {
    response = await fetch(url, { method: options.method ?? 'GET', headers, body, credentials: 'include' })
  } catch {
    throw NETWORK_ERROR
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
  if (error.code === 'invalid_token' && options.retryOnExpired !== false && (await refreshSession())) {
    return send<T>(path, { ...options, retryOnExpired: false })
  }
  throw error
}

async function request<T>(path: string, options?: RequestOptions): Promise<T> {
  return (await send<T>(path, options)).data
}

// --- Session ---------------------------------------------------------------------------------

let refreshInFlight: Promise<boolean> | null = null

/** Rouvre la session à partir du cookie. Un seul appel à la fois, partagé. */
export function refreshSession(): Promise<boolean> {
  refreshInFlight ??= (async () => {
    try {
      const token = await request<AccessToken>('/auth/refresh', { method: 'POST', csrf: true, retryOnExpired: false })
      openSession(token)
      return true
    } catch {
      closeSession()
      return false
    } finally {
      refreshInFlight = null
    }
  })()
  return refreshInFlight
}

// --- Routes d'authentification ---------------------------------------------------------------

export const authApi = {
  register: (payload: RegisterPayload) =>
    request<User>('/auth/register', { method: 'POST', json: payload, retryOnExpired: false }),

  verify: (token: string) =>
    request<VerifyResponse>('/auth/verify', { method: 'POST', json: { token }, retryOnExpired: false }),

  resendVerification: (email: string) =>
    request<MessageResponse>('/auth/resend-verification', { method: 'POST', json: { email }, retryOnExpired: false }),

  /** Étape 1 de la connexion : le backend envoie un lien par email (ou ouvre la session en mode dev). */
  async login(username: string, password: string): Promise<LoginResult> {
    const data = await request<AccessToken & { code?: string; attempt_id?: string; message?: string }>(
      '/auth/token',
      { method: 'POST', form: { username, password }, retryOnExpired: false },
    )
    if (data.code === 'login_email_sent' && data.attempt_id) {
      return { kind: 'email', attemptId: data.attempt_id, message: data.message ?? '' }
    }
    openSession(data)
    return { kind: 'session' }
  },

  /** Étape 2 : la page interroge cette route jusqu'au clic sur le lien. */
  async claim(attemptId: string): Promise<ClaimResult> {
    const { status, data } = await send<AccessToken>('/auth/login/claim', {
      method: 'POST',
      json: { attempt_id: attemptId },
      retryOnExpired: false,
    })
    if (status === 202) return { kind: 'pending' }
    openSession(data)
    return { kind: 'session' }
  },

  async logout(): Promise<void> {
    try {
      await request<MessageResponse>('/auth/logout', { method: 'POST', csrf: true, retryOnExpired: false })
    } finally {
      closeSession()
      channel?.postMessage('logout')
    }
  },

  me: () => request<User>('/auth/me'),

  updateMe: (fullName: string | null) =>
    request<User>('/auth/me', { method: 'PATCH', json: { full_name: fullName } }),

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    const token = await request<AccessToken>('/auth/password/change', {
      method: 'POST',
      json: { current_password: currentPassword, new_password: newPassword },
    })
    openSession(token)
  },

  forgotPassword: (email: string) =>
    request<MessageResponse>('/auth/password/forgot', { method: 'POST', json: { email }, retryOnExpired: false }),

  resetPassword: (token: string, newPassword: string) =>
    request<MessageResponse>('/auth/password/reset', {
      method: 'POST',
      json: { token, new_password: newPassword },
      retryOnExpired: false,
    }),
}

// --- Administration (permission users:manage) ------------------------------------------------

export const adminApi = {
  listUsers: (params: { search?: string; limit: number; offset: number }) =>
    request<AdminUserList>('/admin/users', { query: params }),

  updateUser: (id: number, changes: { role?: string; disabled?: boolean }) =>
    request<AdminUser>(`/admin/users/${id}`, { method: 'PATCH', json: changes }),

  listRoles: () => request<Role[]>('/admin/roles'),
}
