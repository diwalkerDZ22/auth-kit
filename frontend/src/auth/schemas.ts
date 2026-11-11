/**
 * Règles des formulaires, reprises du backend (docs/Sprint5-Auth-complete.md).
 * Elles donnent un retour immédiat ; le backend reste la référence (mots de passe
 * courants, conflits) et ses erreurs `fields` s'affichent sous les mêmes champs.
 */
import { z } from 'zod'

const PASSWORD_MIN_LENGTH = 8
const PASSWORD_MAX_BYTES = 72

const password = z
  .string()
  .min(PASSWORD_MIN_LENGTH, `Le mot de passe doit contenir au moins ${PASSWORD_MIN_LENGTH} caractères.`)
  .refine(
    (value) => new TextEncoder().encode(value).length <= PASSWORD_MAX_BYTES,
    `Le mot de passe ne doit pas dépasser ${PASSWORD_MAX_BYTES} octets.`,
  )

const email = z.string().trim().min(1, 'Champ obligatoire.').pipe(z.email('Adresse email invalide.'))

const required = z.string().min(1, 'Champ obligatoire.')

function confirmed<T extends z.ZodRawShape>(shape: T, field: string, confirmField: string) {
  return z.object(shape).refine((data: Record<string, unknown>) => data[field] === data[confirmField], {
    message: 'Les deux mots de passe ne correspondent pas.',
    path: [confirmField],
  })
}

export const loginSchema = z.object({
  username: required,
  password: required,
})

export const registerSchema = confirmed(
  {
    username: z
      .string()
      .regex(/^[A-Za-z0-9_.-]{3,30}$/, 'De 3 à 30 caractères : lettres, chiffres, « _ », « . » ou « - ».'),
    email,
    full_name: z.string().trim().max(100, 'Trop long.'),
    password,
    password_confirm: required,
  },
  'password',
  'password_confirm',
)

export const emailSchema = z.object({ email })

export const resetPasswordSchema = confirmed(
  { new_password: password, new_password_confirm: required },
  'new_password',
  'new_password_confirm',
)

export const changePasswordSchema = confirmed(
  { current_password: required, new_password: password, new_password_confirm: required },
  'new_password',
  'new_password_confirm',
)

export const profileSchema = z.object({
  full_name: z.string().trim().max(100, 'Trop long.'),
})

export type LoginForm = z.infer<typeof loginSchema>
export type RegisterForm = z.infer<typeof registerSchema>
export type EmailForm = z.infer<typeof emailSchema>
export type ResetPasswordForm = z.infer<typeof resetPasswordSchema>
export type ChangePasswordForm = z.infer<typeof changePasswordSchema>
export type ProfileForm = z.infer<typeof profileSchema>
