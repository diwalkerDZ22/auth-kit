import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router'

import { authApi } from '../api'
import { Alert, Button, Card, Field } from '../components/ui'
import { errorMessage } from '../errors'
import { applyApiError } from '../forms'
import { registerSchema } from '../schemas'
import type { RegisterForm } from '../schemas'

const FIELDS = ['username', 'email', 'full_name', 'password', 'password_confirm']

export function RegisterPage() {
  const [registeredEmail, setRegisteredEmail] = useState<string | null>(null)
  const form = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
    defaultValues: { username: '', email: '', full_name: '', password: '', password_confirm: '' },
  })
  const { errors, isSubmitting } = form.formState

  async function onSubmit(values: RegisterForm) {
    try {
      await authApi.register({
        username: values.username,
        email: values.email,
        full_name: values.full_name || null,
        password: values.password,
      })
      setRegisteredEmail(values.email)
    } catch (error) {
      applyApiError(error, form.setError, FIELDS)
    }
  }

  if (registeredEmail) return <CheckYourInbox email={registeredEmail} />

  return (
    <Card title="Créer un compte">
      <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)} noValidate>
        {errors.root && <Alert>{errors.root.message}</Alert>}
        <Field
          label="Nom d'utilisateur"
          autoComplete="username"
          hint="3 à 30 caractères : lettres, chiffres, « _ », « . » ou « - »."
          error={errors.username?.message}
          {...form.register('username')}
        />
        <Field label="Email" type="email" autoComplete="email" error={errors.email?.message} {...form.register('email')} />
        <Field label="Nom complet (facultatif)" autoComplete="name" error={errors.full_name?.message} {...form.register('full_name')} />
        <Field
          label="Mot de passe"
          type="password"
          autoComplete="new-password"
          hint="Au moins 8 caractères. Une phrase de plusieurs mots est plus sûre."
          error={errors.password?.message}
          {...form.register('password')}
        />
        <Field
          label="Confirmer le mot de passe"
          type="password"
          autoComplete="new-password"
          error={errors.password_confirm?.message}
          {...form.register('password_confirm')}
        />
        <Button type="submit" className="w-full" loading={isSubmitting}>
          Créer le compte
        </Button>
        <p className="text-center text-sm text-slate-600">
          Déjà inscrit ?{' '}
          <Link to="/login" className="font-medium text-indigo-600 hover:underline">
            Se connecter
          </Link>
        </p>
      </form>
    </Card>
  )
}

function CheckYourInbox({ email }: { email: string }) {
  const [status, setStatus] = useState<{ tone: 'success' | 'error'; text: string } | null>(null)
  const [sending, setSending] = useState(false)

  async function resend() {
    setSending(true)
    try {
      const { message } = await authApi.resendVerification(email)
      setStatus({ tone: 'success', text: message })
    } catch (error) {
      setStatus({ tone: 'error', text: errorMessage(error) })
    } finally {
      setSending(false)
    }
  }

  return (
    <Card title="Vérifiez votre boîte mail" subtitle={<>Un lien d'activation a été envoyé à <strong>{email}</strong>. Il est valable 24 heures.</>}>
      <div className="space-y-4">
        {status && <Alert tone={status.tone}>{status.text}</Alert>}
        <Button variant="secondary" className="w-full" loading={sending} onClick={resend}>
          Renvoyer l'email
        </Button>
        <p className="text-center text-sm">
          <Link to="/login" className="text-indigo-600 hover:underline">
            Retour à la connexion
          </Link>
        </p>
      </div>
    </Card>
  )
}
