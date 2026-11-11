import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useLocation, useNavigate } from 'react-router'

import { authApi } from '../api'
import { Alert, Button, Card, Field, Spinner } from '../components/ui'
import { errorMessage, isApiError } from '../errors'
import { applyApiError, safeNext } from '../forms'
import { loginSchema } from '../schemas'
import type { LoginForm } from '../schemas'

const POLL_INTERVAL_MS = 2_000
/** Durée de validité du lien de connexion (LOGIN_TOKEN_EXPIRE_MINUTES côté backend). */
const POLL_TIMEOUT_MS = 15 * 60_000

function pollDeadline(): number {
  return Date.now() + POLL_TIMEOUT_MS
}

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const next = safeNext(location.search)
  const [attempt, setAttempt] = useState<{ id: string; message: string; deadline: number } | null>(null)
  const [notVerified, setNotVerified] = useState(false)
  const [pollError, setPollError] = useState<string | null>(null)

  const form = useForm<LoginForm>({ resolver: zodResolver(loginSchema), defaultValues: { username: '', password: '' } })
  const { errors, isSubmitting } = form.formState

  async function onSubmit(values: LoginForm) {
    setNotVerified(false)
    setPollError(null)
    try {
      const result = await authApi.login(values.username, values.password)
      if (result.kind === 'session') navigate(next, { replace: true })
      else setAttempt({ id: result.attemptId, message: result.message, deadline: pollDeadline() })
    } catch (error) {
      if (isApiError(error) && error.code === 'email_not_verified') setNotVerified(true)
      applyApiError(error, form.setError, ['username', 'password'])
    }
  }

  // Attente du clic sur le lien reçu par email : on interroge /auth/login/claim
  useEffect(() => {
    if (!attempt) return
    let stopped = false
    let timer: ReturnType<typeof setTimeout>
    const { id, deadline } = attempt

    async function poll() {
      if (stopped) return
      if (Date.now() > deadline) {
        setAttempt(null)
        setPollError('Le lien de connexion a expiré, recommencez.')
        return
      }
      try {
        const result = await authApi.claim(id)
        if (stopped) return
        if (result.kind === 'session') {
          navigate(next, { replace: true })
          return
        }
        timer = setTimeout(poll, POLL_INTERVAL_MS)
      } catch (error) {
        if (stopped) return
        // Erreur réseau ou limite atteinte : on réessaie ; sinon la tentative est terminée
        if (isApiError(error) && (error.code === 'network_error' || error.code === 'rate_limited')) {
          timer = setTimeout(poll, POLL_INTERVAL_MS * 3)
          return
        }
        setAttempt(null)
        setPollError(errorMessage(error))
      }
    }

    timer = setTimeout(poll, POLL_INTERVAL_MS)
    return () => {
      stopped = true
      clearTimeout(timer)
    }
  }, [attempt, navigate, next])

  if (attempt) {
    return (
      <Card title="Vérifiez vos emails" subtitle={attempt.message}>
        <div className="space-y-4">
          <div className="flex items-center gap-3 rounded-lg bg-slate-50 px-4 py-3 text-sm text-slate-700">
            <Spinner />
            Cliquez sur le lien reçu (sur n'importe quel appareil) : cette page se connectera toute seule.
          </div>
          <Button variant="secondary" className="w-full" onClick={() => setAttempt(null)}>
            Annuler et recommencer
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <Card title="Connexion" subtitle="Un lien de confirmation vous sera envoyé par email.">
      <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)} noValidate>
        {pollError && <Alert>{pollError}</Alert>}
        {errors.root && (
          <Alert>
            {errors.root.message}
            {notVerified && (
              <>
                {' '}
                <Link to="/resend-verification" className="font-medium underline">
                  Renvoyer l'email de vérification
                </Link>
              </>
            )}
          </Alert>
        )}
        <Field label="Nom d'utilisateur" autoComplete="username" error={errors.username?.message} {...form.register('username')} />
        <Field
          label="Mot de passe"
          type="password"
          autoComplete="current-password"
          error={errors.password?.message}
          {...form.register('password')}
        />
        <div className="text-right text-sm">
          <Link to="/forgot-password" className="text-indigo-600 hover:underline">
            Mot de passe oublié ?
          </Link>
        </div>
        <Button type="submit" className="w-full" loading={isSubmitting}>
          Se connecter
        </Button>
        <p className="text-center text-sm text-slate-600">
          Pas encore de compte ?{' '}
          <Link to="/register" className="font-medium text-indigo-600 hover:underline">
            Créer un compte
          </Link>
        </p>
      </form>
    </Card>
  )
}
