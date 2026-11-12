/**
 * Thème clair / sombre / système.
 *
 * Le choix est appliqué par <html data-theme="light|dark"> (absent : suit le système) et mémorisé
 * dans localStorage. Pour éviter un flash au chargement, mettre THEME_INIT_SCRIPT dans <head>.
 */
import { useSyncExternalStore } from 'react'


export type ThemePreference = 'light' | 'dark' | 'system'

const STORAGE_KEY = 'auth-kit-theme'

/** À placer dans <head> : <script>{THEME_INIT_SCRIPT}</script> (avant le CSS de préférence). */
export const THEME_INIT_SCRIPT =
  `try{var t=localStorage.getItem('${STORAGE_KEY}');if(t==='light'||t==='dark')document.documentElement.dataset.theme=t}catch(e){}`

function readPreference(): ThemePreference {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored === 'light' || stored === 'dark' ? stored : 'system'
  } catch {
    return 'system'   // stockage bloqué (navigation privée, cookies refusés)
  }
}

let preference: ThemePreference = typeof window === 'undefined' ? 'system' : readPreference()
const listeners = new Set<() => void>()

function apply(value: ThemePreference) {
  if (typeof document === 'undefined') return
  const root = document.documentElement
  if (value === 'system') delete root.dataset.theme
  else root.dataset.theme = value
}

export function setThemePreference(value: ThemePreference) {
  preference = value
  try {
    if (value === 'system') localStorage.removeItem(STORAGE_KEY)
    else localStorage.setItem(STORAGE_KEY, value)
  } catch {
    // le choix vaut pour cette page seulement
  }
  apply(value)
  listeners.forEach((listener) => listener())
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  const media = typeof window !== 'undefined' && window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null
  media?.addEventListener('change', listener)
  return () => {
    listeners.delete(listener)
    media?.removeEventListener('change', listener)
  }
}

function systemIsDark(): boolean {
  return typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-color-scheme: dark)').matches
}

export function useTheme() {
  const current = useSyncExternalStore(subscribe, () => preference, () => 'system' as ThemePreference)
  const systemDark = useSyncExternalStore(subscribe, systemIsDark, () => false)
  const resolved: 'light' | 'dark' = current === 'system' ? (systemDark ? 'dark' : 'light') : current
  return { preference: current, resolved, setPreference: setThemePreference }
}
