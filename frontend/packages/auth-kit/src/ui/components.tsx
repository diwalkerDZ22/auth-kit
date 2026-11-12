/** Composants d'interface (classes ak-*, voir styles.css). Réutilisables dans les pages du projet. */
import { forwardRef, useId, useState } from 'react'
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from 'react'
import { Link } from 'react-router'
import type { LinkProps } from 'react-router'

import { Icon } from './icons'
import type { IconName } from './icons'
import { useBrand, useMessages } from './context'
import { passwordScore } from './strength'

// --- Mise en page ------------------------------------------------------------------------------

/** Carte centrée des pages d'authentification (connexion, inscription, liens email). */
export function AuthCard({
  title,
  subtitle,
  icon,
  tone = 'primary',
  children,
}: {
  title: string
  subtitle?: ReactNode
  icon?: IconName
  tone?: 'primary' | 'danger' | 'success'
  children?: ReactNode
}) {
  const brand = useBrand()
  return (
    <div className="ak-scope ak-auth">
      <div className="ak-card">
        {(brand.name || brand.logo) && (
          <div className="ak-brand">
            {brand.logo ?? (
              <span className="ak-brand-mark">
                <Icon name="shield" size={18} />
              </span>
            )}
            {brand.name}
          </div>
        )}
        {icon && (
          <span className={`ak-hero-icon${tone === 'primary' ? '' : ` ak-hero-icon--${tone}`}`}>
            <Icon name={icon} size={24} />
          </span>
        )}
        <h1 className="ak-title">{title}</h1>
        {subtitle && <p className="ak-subtitle">{subtitle}</p>}
        {children && <div className="ak-body">{children}</div>}
      </div>
    </div>
  )
}

/** Bloc des pages connectées (profil, administration). */
export function Section({
  title,
  description,
  footer,
  children,
}: {
  title?: string
  description?: ReactNode
  footer?: ReactNode
  children: ReactNode
}) {
  return (
    <section className="ak-section">
      {title && (
        <div className="ak-section-head">
          <h2 className="ak-section-title">{title}</h2>
          {description && <p className="ak-section-desc">{description}</p>}
        </div>
      )}
      <div className="ak-section-body">{children}</div>
      {footer && <div className="ak-section-foot">{footer}</div>}
    </section>
  )
}

// --- Formulaires -------------------------------------------------------------------------------

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  error?: string
  hint?: ReactNode
  icon?: IconName
  /** Contenu à droite du libellé (ex. lien « Mot de passe oublié ? »). */
  aside?: ReactNode
  /** Sous le champ, avant l'aide (ex. jauge de solidité). */
  extra?: ReactNode
}

export const Field = forwardRef<HTMLInputElement, FieldProps>(function Field(
  { label, error, hint, icon, aside, extra, id, type, className = '', ...props },
  ref,
) {
  const generatedId = useId()
  const inputId = id ?? props.name ?? generatedId
  const m = useMessages().fields
  const [revealed, setRevealed] = useState(false)
  const isPassword = type === 'password'
  const describedBy = error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined

  return (
    <div className="ak-field">
      <div className="ak-label-row">
        <label htmlFor={inputId} className="ak-label">
          {label}
        </label>
        {aside}
      </div>
      <div className="ak-input-wrap">
        {icon && (
          <span className="ak-input-icon">
            <Icon name={icon} size={17} />
          </span>
        )}
        <input
          ref={ref}
          id={inputId}
          type={isPassword && revealed ? 'text' : type}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className={`ak-input${icon ? ' ak-input--icon' : ''}${isPassword ? ' ak-input--action' : ''} ${className}`}
          {...props}
        />
        {isPassword && (
          <button
            type="button"
            className="ak-input-action"
            onClick={() => setRevealed((value) => !value)}
            aria-label={revealed ? m.hidePassword : m.showPassword}
            aria-pressed={revealed}
          >
            <Icon name={revealed ? 'eyeOff' : 'eye'} size={17} />
          </button>
        )}
      </div>
      {extra}
      {error ? (
        <p id={`${inputId}-error`} className="ak-error">
          <Icon name="alert" size={14} />
          {error}
        </p>
      ) : (
        hint && (
          <p id={`${inputId}-hint`} className="ak-hint">
            {hint}
          </p>
        )
      )}
    </div>
  )
})

export function PasswordStrength({ password, minLength }: { password: string; minLength?: number }) {
  const m = useMessages().strength
  const score = passwordScore(password, minLength)
  if (!password) return null
  return (
    <div className="ak-strength" data-score={score} aria-live="polite">
      <div className="ak-strength-bars" aria-hidden="true">
        {[0, 1, 2, 3].map((i) => (
          <span key={i} className="ak-strength-bar" />
        ))}
      </div>
      <span className="ak-strength-label">{m.levels[score]}</span>
    </div>
  )
}

// --- Boutons, liens ----------------------------------------------------------------------------

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  loading?: boolean
  variant?: 'primary' | 'secondary' | 'danger' | 'danger-soft' | 'ghost'
  size?: 'md' | 'sm'
  block?: boolean
  icon?: IconName
}

export function Button({
  loading,
  variant = 'primary',
  size = 'md',
  block,
  icon,
  children,
  className = '',
  disabled,
  type = 'button',
  ...props
}: ButtonProps) {
  const classes = ['ak-btn', `ak-btn--${variant}`, size === 'sm' && 'ak-btn--sm', block && 'ak-btn--block', className]
  return (
    <button
      type={type}
      className={classes.filter(Boolean).join(' ')}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading ? <Spinner /> : icon && <Icon name={icon} size={size === 'sm' ? 15 : 17} />}
      {children}
    </button>
  )
}

export function TextLink({ className = '', subtle, ...props }: LinkProps & { subtle?: boolean }) {
  return <Link className={`ak-link${subtle ? ' ak-link--subtle' : ''} ${className}`} {...props} />
}

// --- Retours -----------------------------------------------------------------------------------

const ALERT_ICONS: Record<string, IconName> = { error: 'alert', success: 'checkCircle', info: 'info', warning: 'alert' }

export function Alert({ tone = 'error', children }: { tone?: 'error' | 'success' | 'info' | 'warning'; children: ReactNode }) {
  return (
    <div role={tone === 'error' ? 'alert' : 'status'} className={`ak-alert ak-alert--${tone}`}>
      <Icon name={ALERT_ICONS[tone]} size={17} />
      <div>{children}</div>
    </div>
  )
}

export function Badge({
  tone = 'gray',
  plain,
  children,
}: {
  tone?: 'green' | 'red' | 'amber' | 'indigo' | 'gray'
  plain?: boolean
  children: ReactNode
}) {
  return <span className={`ak-badge ak-badge--${tone}${plain ? ' ak-badge--plain' : ''}`}>{children}</span>
}

export function Spinner({ large }: { large?: boolean }) {
  return <span className={`ak-spinner${large ? ' ak-spinner--lg' : ''}`} aria-hidden="true" />
}

export function FullPageSpinner() {
  const m = useMessages().common
  return (
    <div className="ak-scope ak-fullpage" role="status">
      <Spinner large />
      <span className="ak-sr-only">{m.loading}</span>
    </div>
  )
}

export function Avatar({ name, small }: { name: string; small?: boolean }) {
  const initials = name
    .split(/[\s._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('')
  return (
    <span className={`ak-avatar${small ? ' ak-avatar--sm' : ''}`} aria-hidden="true">
      {initials || '?'}
    </span>
  )
}
