/**
 * Types des réponses du backend, dérivés du contrat OpenAPI (api.gen.ts, généré : npm run gen:api).
 * Ne pas les réécrire à la main : ils suivent le backend.
 */
import type { components } from './api.gen'

type Schemas = components['schemas']

export type User = Schemas['UserMe']
export type AccessToken = Schemas['AccessToken']
export type LoginEmailSent = Schemas['LoginEmailSent']
export type MessageResponse = Schemas['MessageOut']
export type VerifyResponse = Schemas['VerifyOut']
export type UserSession = Schemas['SessionOut']
export type RevokeResponse = Schemas['RevokeOut']
export type RevokeOthersResponse = Schemas['RevokeOthersOut']
export type AuthConfig = Schemas['AuthConfigOut']
export type AuthFeature = AuthConfig['features'][number]
export type RegisterPayload = Schemas['UserCreate']
export type AdminUser = Schemas['AdminUserOut']
export type AdminUserList = Schemas['AdminUserList']
export type AdminUserUpdate = Schemas['AdminUserUpdate']
export type Role = Schemas['RoleOut']

/** Résultat de POST /auth/token : lien envoyé par email, ou session ouverte (mode dev). */
export type LoginResult =
  | { kind: 'email'; attemptId: string; message: string }
  | { kind: 'session' }

/** Résultat de POST /auth/login/claim. */
export type ClaimResult = { kind: 'pending' } | { kind: 'session' }
