/** Types des réponses du backend auth-kit. */

export interface User {
  id: number
  username: string
  email: string
  full_name: string | null
  is_verified: boolean
  role: string
  permissions: string[]
}

export interface AccessToken {
  access_token: string
  token_type: 'bearer'
  expires_in: number
}

/** Résultat de POST /auth/token : lien envoyé par email, ou tokens directs (mode dev). */
export type LoginResult =
  | { kind: 'email'; attemptId: string; message: string }
  | { kind: 'session' }

/** Résultat de POST /auth/login/claim. */
export type ClaimResult = { kind: 'pending' } | { kind: 'session' }

export interface MessageResponse {
  message: string
}

export interface VerifyResponse extends MessageResponse {
  purpose: 'signup' | 'login'
}

export interface RegisterPayload {
  username: string
  email: string
  full_name?: string | null
  password: string
}

export interface AdminUser {
  id: number
  username: string
  email: string
  full_name: string | null
  role: string
  disabled: boolean
  is_verified: boolean
}

export interface AdminUserList {
  items: AdminUser[]
  total: number
  limit: number
  offset: number
}

export interface Role {
  name: string
  description: string | null
  permissions: string[]
}
