/**
 * Règles des formulaires, construites à partir de GET /auth/config (règles du backend) :
 * retour immédiat sans recopier les règles. Le backend reste juge (mots de passe courants,
 * fuites, conflits) et ses erreurs `fields` s'affichent sous les mêmes champs.
 */
import { useMemo } from 'react'
import { z } from 'zod'

import type { AuthConfig } from '../client/types'
import { useAuth } from '../react/context'
import type { Messages } from './messages'
import { useMessages } from './context'

export interface FormRules {
  passwordMinLength: number
  passwordMaxBytes: number
  usernamePattern: RegExp
}

export const DEFAULT_RULES: FormRules = {
  passwordMinLength: 8,
  passwordMaxBytes: 72,
  usernamePattern: /^[A-Za-z0-9_.-]{3,30}$/,
}

export function rulesFromConfig(config: AuthConfig | undefined): FormRules {
  if (!config) return DEFAULT_RULES
  return {
    passwordMinLength: config.password.min_length,
    passwordMaxBytes: config.password.max_bytes,
    usernamePattern: new RegExp(config.username_pattern),
  }
}

export function makeSchemas(rules: FormRules, v: Messages['validation']) {
  const required = z.string().min(1, v.required)
  const email = z.string().trim().min(1, v.required).pipe(z.email(v.email))
  const password = z
    .string()
    .min(rules.passwordMinLength, v.passwordMin(rules.passwordMinLength))
    .refine((value) => new TextEncoder().encode(value).length <= rules.passwordMaxBytes, v.passwordMaxBytes(rules.passwordMaxBytes))

  function confirmed<T extends z.ZodRawShape>(shape: T, field: string, confirmField: string) {
    return z.object(shape).refine((data: Record<string, unknown>) => data[field] === data[confirmField], {
      message: v.mismatch,
      path: [confirmField],
    })
  }

  return {
    login: z.object({ username: required, password: required }),
    register: confirmed(
      {
        username: z.string().regex(rules.usernamePattern, v.username),
        email,
        full_name: z.string().trim().max(100, v.tooLong),
        password,
        password_confirm: required,
      },
      'password',
      'password_confirm',
    ),
    email: z.object({ email }),
    resetPassword: confirmed({ new_password: password, new_password_confirm: required }, 'new_password', 'new_password_confirm'),
    changePassword: confirmed(
      { current_password: required, new_password: password, new_password_confirm: required },
      'new_password',
      'new_password_confirm',
    ),
    profile: z.object({ full_name: z.string().trim().max(100, v.tooLong) }),
  }
}

export type Schemas = ReturnType<typeof makeSchemas>
export type LoginForm = z.infer<Schemas['login']>
export type RegisterForm = z.infer<Schemas['register']>
export type EmailForm = z.infer<Schemas['email']>
export type ResetPasswordForm = z.infer<Schemas['resetPassword']>
export type ChangePasswordForm = z.infer<Schemas['changePassword']>
export type ProfileForm = z.infer<Schemas['profile']>

/** Schémas à jour de la config du backend et des messages du projet. */
export function useSchemas(): { schemas: Schemas; rules: FormRules } {
  const { config } = useAuth()
  const validation = useMessages().validation
  return useMemo(() => {
    const rules = rulesFromConfig(config)
    return { schemas: makeSchemas(rules, validation), rules }
  }, [config, validation])
}
