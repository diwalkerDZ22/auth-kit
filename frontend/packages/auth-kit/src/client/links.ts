/** Lecture des liens reçus par email et des redirections, sans dépendance à React. */

/** Valeur de ?next= si c'est un chemin interne, sinon fallback (évite les redirections ouvertes). */
export function safeNext(search: string, fallback = '/'): string {
  const next = new URLSearchParams(search).get('next')
  return next && next.startsWith('/') && !next.startsWith('//') && !next.startsWith('/\\') ? next : fallback
}

/** Lit `?token=` (fonction pure : utilisable dans un initialiseur useState). */
export function readTokenFromUrl(): string | null {
  return new URL(window.location.href).searchParams.get('token')
}

/** Type du lien reçu par email (`?type=signup|login`), pour adapter la page de confirmation. */
export function readLinkTypeFromUrl(): 'signup' | 'login' | null {
  const type = new URL(window.location.href).searchParams.get('type')
  return type === 'signup' || type === 'login' ? type : null
}

/** Retire `?token=` de l'URL (historique, en-tête Referer). À appeler dans un useEffect. */
export function stripTokenFromUrl(): void {
  const url = new URL(window.location.href)
  if (!url.searchParams.has('token')) return
  url.searchParams.delete('token')
  window.history.replaceState(window.history.state, '', url.pathname + url.search + url.hash)
}
