/**
 * Hooks « headless » : toute la logique des pages, sans interface.
 * Un projet avec son propre design system les utilise directement au lieu de @auth-kit/react/ui.
 */
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useRef, useState } from 'react'

import { isApiError } from '../client/errors'
import type { AdminUserUpdate } from '../client/types'
import { SESSIONS_QUERY_KEY, useAuth, useAuthClient } from './context'

// --- Connexion en deux étapes ------------------------------------------------------------------

export interface LoginFlowOptions {
  /** Appelé quand la session est ouverte (mot de passe seul en mode dev, ou après le clic sur le lien). */
  onSuccess: () => void
  pollIntervalMs?: number
}

export interface LoginAttempt {
  message: string
  deadline: number
}

/**
 * Mot de passe, puis attente du clic sur le lien reçu par email (interrogation de /login/claim).
 * submit() lève l'ApiError du backend (à afficher dans le formulaire).
 */
export function useLoginFlow({ onSuccess, pollIntervalMs = 2_000 }: LoginFlowOptions) {
  const client = useAuthClient()
  const { config } = useAuth()
  const [attempt, setAttempt] = useState<(LoginAttempt & { id: string }) | null>(null)
  const [pollError, setPollError] = useState<unknown>(null)
  const onSuccessRef = useRef(onSuccess)
  useEffect(() => {
    onSuccessRef.current = onSuccess
  })

  const linkTtlMs = (config?.login_link_expire_seconds ?? 15 * 60) * 1000

  const submit = useCallback(
    async (username: string, password: string) => {
      setPollError(null)
      const result = await client.auth.login(username, password)
      if (result.kind === 'session') onSuccessRef.current()
      else setAttempt({ id: result.attemptId, message: result.message, deadline: Date.now() + linkTtlMs })
    },
    [client, linkTtlMs],
  )

  const cancel = useCallback(() => setAttempt(null), [])

  useEffect(() => {
    if (!attempt) return
    let stopped = false
    let timer: ReturnType<typeof setTimeout>
    const { id, deadline } = attempt

    async function poll() {
      if (stopped) return
      if (Date.now() > deadline) {
        setAttempt(null)
        setPollError('expired')
        return
      }
      try {
        const result = await client.auth.claim(id)
        if (stopped) return
        if (result.kind === 'session') {
          setAttempt(null)
          onSuccessRef.current()
          return
        }
        timer = setTimeout(poll, pollIntervalMs)
      } catch (error) {
        if (stopped) return
        // Erreur réseau ou limite atteinte : on réessaie ; sinon la tentative est terminée
        if (isApiError(error) && (error.code === 'network_error' || error.code === 'rate_limited')) {
          timer = setTimeout(poll, pollIntervalMs * 3)
          return
        }
        setAttempt(null)
        setPollError(error)
      }
    }

    timer = setTimeout(poll, pollIntervalMs)
    return () => {
      stopped = true
      clearTimeout(timer)
    }
  }, [attempt, client, pollIntervalMs])

  return {
    /** Non null : le lien a été envoyé, la page attend le clic. */
    attempt: attempt ? { message: attempt.message, deadline: attempt.deadline } : null,
    /** Fin de l'attente sans session : "expired" (délai dépassé) ou ApiError (lien refusé, remplacé...). */
    pollError,
    submit,
    cancel,
  }
}

// --- Appareils connectés -----------------------------------------------------------------------

export function useDevices() {
  const client = useAuthClient()
  const queryClient = useQueryClient()
  const sessions = useQuery({ queryKey: SESSIONS_QUERY_KEY, queryFn: client.auth.listSessions })
  const refresh = () => queryClient.invalidateQueries({ queryKey: SESSIONS_QUERY_KEY })

  const revoke = useMutation({ mutationFn: (id: string) => client.auth.revokeSession(id), onSuccess: refresh })
  const revokeOthers = useMutation({ mutationFn: () => client.auth.revokeOtherSessions(), onSuccess: refresh })

  return { sessions, revoke, revokeOthers, refresh }
}

// --- Administration ----------------------------------------------------------------------------

export function useDebounced<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return debounced
}

export function useAdminUsers({ search, page, pageSize = 20 }: { search: string; page: number; pageSize?: number }) {
  const client = useAuthClient()
  const users = useQuery({
    queryKey: ['admin', 'users', search, page, pageSize],
    queryFn: () => client.admin.listUsers({ search, limit: pageSize, offset: page * pageSize }),
    placeholderData: keepPreviousData,
  })
  const total = users.data?.total ?? 0
  return { users, total, pageCount: Math.max(1, Math.ceil(total / pageSize)) }
}

export function useAdminRoles() {
  const client = useAuthClient()
  return useQuery({ queryKey: ['admin', 'roles'], queryFn: client.admin.listRoles, staleTime: 10 * 60_000 })
}

export function useUpdateUser(userId: number) {
  const client = useAuthClient()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (changes: AdminUserUpdate) => client.admin.updateUser(userId, changes),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'users'] }),
  })
}
