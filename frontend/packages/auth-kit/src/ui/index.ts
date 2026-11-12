/**
 * @auth-kit/react/ui : pages prêtes à l'emploi et composants (importer aussi "@auth-kit/react/ui/styles.css").
 */
export {
  Alert, AuthCard, Avatar, Badge, Button, Field, FullPageSpinner, PasswordStrength, Section, Spinner, TextLink,
} from './components'
export { describeDevice } from './devices'
export { applyApiError } from './forms'
export { Icon } from './icons'
export type { IconName } from './icons'
export { FR, mergeMessages } from './messages'
export type { Messages, MessagesOverride } from './messages'
export { AccessDenied } from './pages/AccessDenied'
export { AdminUsersPage } from './pages/AdminUsersPage'
export { ForgotPasswordPage, ResendVerificationPage } from './pages/EmailRequestPages'
export {
  LazyAdminUsersPage, LazyForgotPasswordPage, LazyLoginPage, LazyProfilePage, LazyRegisterPage,
  LazyResendVerificationPage, LazyResetPasswordPage, LazyVerifyEmailPage,
} from './pages/LazyPages'
export { LoginPage } from './pages/LoginPage'
export { ProfilePage } from './pages/ProfilePage'
export { RegisterPage } from './pages/RegisterPage'
export { ResetPasswordPage } from './pages/ResetPasswordPage'
export { VerifyEmailPage } from './pages/VerifyEmailPage'
export { useBrand, useMessages } from './context'
export type { Brand } from './context'
export { AuthUIProvider } from './provider'
export { createAuthRoutes } from './routes'
export { DEFAULT_RULES, makeSchemas, rulesFromConfig, useSchemas } from './schemas'
export type { FormRules, Schemas } from './schemas'
export { passwordScore } from './strength'
export { THEME_INIT_SCRIPT, setThemePreference, useTheme } from './theme'
export { ThemeToggle } from './ThemeToggle'
export { useLinkToken } from './useLinkToken'
export type { ThemePreference } from './theme'
