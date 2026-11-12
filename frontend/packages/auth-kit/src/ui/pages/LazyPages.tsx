/**
 * Pages chargées à la demande : les formulaires (zod, react-hook-form) ne pèsent pas sur le
 * chargement initial de l'application. createAuthRoutes() les utilise ; les pages « directes »
 * restent exportées pour qui préfère les charger d'emblée.
 */
import { lazy, Suspense } from 'react'
import type { ComponentType, LazyExoticComponent } from 'react'

import { FullPageSpinner } from '../components'

function withSuspense(Page: LazyExoticComponent<ComponentType>) {
  return function LazyPage() {
    return (
      <Suspense fallback={<FullPageSpinner />}>
        <Page />
      </Suspense>
    )
  }
}

export const LazyLoginPage = withSuspense(lazy(() => import('./LoginPage').then((m) => ({ default: m.LoginPage }))))
export const LazyRegisterPage = withSuspense(lazy(() => import('./RegisterPage').then((m) => ({ default: m.RegisterPage }))))
export const LazyForgotPasswordPage = withSuspense(
  lazy(() => import('./EmailRequestPages').then((m) => ({ default: m.ForgotPasswordPage }))),
)
export const LazyResendVerificationPage = withSuspense(
  lazy(() => import('./EmailRequestPages').then((m) => ({ default: m.ResendVerificationPage }))),
)
export const LazyResetPasswordPage = withSuspense(
  lazy(() => import('./ResetPasswordPage').then((m) => ({ default: m.ResetPasswordPage }))),
)
export const LazyVerifyEmailPage = withSuspense(lazy(() => import('./VerifyEmailPage').then((m) => ({ default: m.VerifyEmailPage }))))
export const LazyProfilePage = withSuspense(lazy(() => import('./ProfilePage').then((m) => ({ default: m.ProfilePage }))))
export const LazyAdminUsersPage = withSuspense(lazy(() => import('./AdminUsersPage').then((m) => ({ default: m.AdminUsersPage }))))
