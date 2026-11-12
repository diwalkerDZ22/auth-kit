/** @auth-kit/react/react : état d'authentification, gardes de routes et hooks, sans interface. */
export { AuthProvider } from './AuthProvider'
export type { AuthProviderProps } from './AuthProvider'
export { CONFIG_QUERY_KEY, ME_QUERY_KEY, SESSIONS_QUERY_KEY, useAuth, useAuthClient, usePaths } from './context'
export type { AuthContextValue, AuthStatus } from './context'
export { GuestOnly, RequireAuth, RequirePermission } from './guards'
export {
  useAdminRoles, useAdminUsers, useDebounced, useDevices, useLoginFlow, useUpdateUser,
} from './hooks'
export type { LoginAttempt, LoginFlowOptions } from './hooks'
export { DEFAULT_PATHS, resolvePaths } from './paths'
export { ADMIN_PERMISSION } from './permissions'
export type { AuthPaths } from './paths'
