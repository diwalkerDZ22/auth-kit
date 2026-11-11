/** Point d'entrée du module auth réutilisable. */
export { adminApi, authApi, refreshSession } from './api'
export { AuthProvider } from './AuthProvider'
export { useAuth } from './context'
export type { AuthContextValue, AuthStatus } from './context'
export { ApiError, errorMessage, isApiError } from './errors'
export { GuestOnly, RequireAuth, RequirePermission } from './guards'
export { authRoutes } from './routes'
export type * from './types'
