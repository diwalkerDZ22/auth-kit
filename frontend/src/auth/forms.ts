import type { FieldValues, Path, UseFormSetError } from 'react-hook-form'

import { errorMessage, isApiError } from './errors'

/**
 * Affiche une erreur du backend dans un formulaire :
 * - erreurs `fields` sous les champs correspondants ;
 * - le reste dans l'erreur globale `root`.
 */
export function applyApiError<T extends FieldValues>(error: unknown, setError: UseFormSetError<T>, fieldNames: string[]) {
  if (isApiError(error) && Object.keys(error.fields).length) {
    let shown = false
    for (const [field, message] of Object.entries(error.fields)) {
      if (fieldNames.includes(field)) {
        setError(field as Path<T>, { type: 'server', message })
        shown = true
      }
    }
    if (shown) return
  }
  setError('root', { type: 'server', message: errorMessage(error) })
}

/** Valeur de ?next= si c'est un chemin interne, sinon "/" (évite les redirections ouvertes). */
export function safeNext(search: string): string {
  const next = new URLSearchParams(search).get('next')
  return next && next.startsWith('/') && !next.startsWith('//') ? next : '/'
}

/** Lit `?token=` (fonction pure : utilisable dans un initialiseur useState). */
export function readTokenFromUrl(): string | null {
  return new URL(window.location.href).searchParams.get('token')
}

/** Retire `?token=` de l'URL (historique, en-tête Referer). À appeler dans un useEffect. */
export function stripTokenFromUrl(): void {
  const url = new URL(window.location.href)
  if (!url.searchParams.has('token')) return
  url.searchParams.delete('token')
  window.history.replaceState(window.history.state, '', url.pathname + url.search + url.hash)
}
