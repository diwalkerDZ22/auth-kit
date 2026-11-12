/**
 * Routes du module, à intégrer dans le routeur de l'application :
 *   createBrowserRouter([{ element: <Layout />, children: [...createAuthRoutes(paths), ...mesRoutes] }])
 * Passer les mêmes chemins à <AuthProvider paths={...}>.
 */
import type { ReactNode } from 'react'
import type { RouteObject } from 'react-router'

import { ADMIN_PERMISSION } from '../react/permissions'
import { GuestOnly, RequireAuth, RequirePermission } from '../react/guards'
import { resolvePaths } from '../react/paths'
import type { AuthPaths } from '../react/paths'
import { FullPageSpinner } from './components'
import { AccessDenied } from './pages/AccessDenied'
import {
  LazyAdminUsersPage,
  LazyForgotPasswordPage,
  LazyLoginPage,
  LazyProfilePage,
  LazyRegisterPage,
  LazyResendVerificationPage,
  LazyResetPasswordPage,
  LazyVerifyEmailPage,
} from './pages/LazyPages'

const spinner: ReactNode = <FullPageSpinner />

export function createAuthRoutes(paths?: Partial<AuthPaths>): RouteObject[] {
  const p = resolvePaths(paths)
  const guest = (page: ReactNode) => <GuestOnly loading={spinner}>{page}</GuestOnly>
  return [
    { path: p.login, element: guest(<LazyLoginPage />) },
    { path: p.register, element: guest(<LazyRegisterPage />) },
    { path: p.forgotPassword, element: guest(<LazyForgotPasswordPage />) },
    { path: p.resendVerification, element: guest(<LazyResendVerificationPage />) },
    // Accessibles connecté ou non : le lien peut être ouvert sur n'importe quel appareil
    { path: p.verifyEmail, element: <LazyVerifyEmailPage /> },
    { path: p.resetPassword, element: <LazyResetPasswordPage /> },
    { path: p.profile, element: <RequireAuth loading={spinner}><LazyProfilePage /></RequireAuth> },
    {
      path: p.adminUsers,
      element: (
        <RequirePermission permission={ADMIN_PERMISSION} loading={spinner} fallback={<AccessDenied />}>
          <LazyAdminUsersPage />
        </RequirePermission>
      ),
    },
  ]
}
