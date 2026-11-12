/** Chemins des pages d'authentification. Tous remplaçables : <AuthProvider paths={{ login: '/connexion' }}>. */
export interface AuthPaths {
  home: string
  login: string
  register: string
  forgotPassword: string
  resendVerification: string
  /** Doit correspondre à AUTH_FRONTEND_VERIFY_URL côté backend. */
  verifyEmail: string
  /** Doit correspondre à AUTH_FRONTEND_RESET_URL côté backend. */
  resetPassword: string
  profile: string
  adminUsers: string
}

export const DEFAULT_PATHS: AuthPaths = {
  home: '/',
  login: '/login',
  register: '/register',
  forgotPassword: '/forgot-password',
  resendVerification: '/resend-verification',
  verifyEmail: '/verify-email',
  resetPassword: '/reset-password',
  profile: '/profile',
  adminUsers: '/admin/users',
}

export function resolvePaths(paths?: Partial<AuthPaths>): AuthPaths {
  return { ...DEFAULT_PATHS, ...paths }
}
