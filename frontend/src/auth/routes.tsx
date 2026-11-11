/**
 * Routes du module auth, à intégrer dans le routeur de l'application :
 *   createBrowserRouter([{ element: <Layout />, children: [...authRoutes, ...mesRoutes] }])
 */
import type { RouteObject } from 'react-router'

import { GuestOnly, RequireAuth, RequirePermission } from './guards'
import { AdminUsersPage } from './pages/AdminUsersPage'
import { ForgotPasswordPage, ResendVerificationPage } from './pages/EmailRequestPages'
import { LoginPage } from './pages/LoginPage'
import { ProfilePage } from './pages/ProfilePage'
import { RegisterPage } from './pages/RegisterPage'
import { ResetPasswordPage } from './pages/ResetPasswordPage'
import { VerifyEmailPage } from './pages/VerifyEmailPage'

export const authRoutes: RouteObject[] = [
  { path: '/login', element: <GuestOnly><LoginPage /></GuestOnly> },
  { path: '/register', element: <GuestOnly><RegisterPage /></GuestOnly> },
  { path: '/forgot-password', element: <GuestOnly><ForgotPasswordPage /></GuestOnly> },
  { path: '/resend-verification', element: <GuestOnly><ResendVerificationPage /></GuestOnly> },
  // Accessibles connecté ou non : le lien peut être ouvert sur n'importe quel appareil
  { path: '/verify-email', element: <VerifyEmailPage /> },
  { path: '/reset-password', element: <ResetPasswordPage /> },
  { path: '/profile', element: <RequireAuth><ProfilePage /></RequireAuth> },
  { path: '/admin/users', element: <RequirePermission permission="users:manage"><AdminUsersPage /></RequirePermission> },
]
