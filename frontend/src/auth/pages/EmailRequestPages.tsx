/** Pages « saisissez votre email » : mot de passe oublié et renvoi du mail de vérification. */
import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router'

import { authApi } from '../api'
import { Alert, Button, Card, Field } from '../components/ui'
import { applyApiError } from '../forms'
import { emailSchema } from '../schemas'
import type { EmailForm } from '../schemas'
import type { MessageResponse } from '../types'

function EmailRequestPage(props: {
  title: string
  subtitle: string
  submitLabel: string
  send: (email: string) => Promise<MessageResponse>
}) {
  const [done, setDone] = useState<string | null>(null)
  const form = useForm<EmailForm>({ resolver: zodResolver(emailSchema), defaultValues: { email: '' } })
  const { errors, isSubmitting } = form.formState

  async function onSubmit({ email }: EmailForm) {
    try {
      setDone((await props.send(email)).message)
    } catch (error) {
      applyApiError(error, form.setError, ['email'])
    }
  }

  return (
    <Card title={props.title} subtitle={props.subtitle}>
      {done ? (
        <div className="space-y-4">
          <Alert tone="success">{done}</Alert>
          <p className="text-center text-sm">
            <Link to="/login" className="text-indigo-600 hover:underline">
              Retour à la connexion
            </Link>
          </p>
        </div>
      ) : (
        <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)} noValidate>
          {errors.root && <Alert>{errors.root.message}</Alert>}
          <Field label="Email" type="email" autoComplete="email" error={errors.email?.message} {...form.register('email')} />
          <Button type="submit" className="w-full" loading={isSubmitting}>
            {props.submitLabel}
          </Button>
          <p className="text-center text-sm">
            <Link to="/login" className="text-indigo-600 hover:underline">
              Retour à la connexion
            </Link>
          </p>
        </form>
      )}
    </Card>
  )
}

export function ForgotPasswordPage() {
  return (
    <EmailRequestPage
      title="Mot de passe oublié"
      subtitle="Saisissez votre email : vous recevrez un lien pour choisir un nouveau mot de passe (valable 30 minutes)."
      submitLabel="Envoyer le lien"
      send={authApi.forgotPassword}
    />
  )
}

export function ResendVerificationPage() {
  return (
    <EmailRequestPage
      title="Renvoyer l'email de vérification"
      subtitle="Saisissez l'email utilisé à l'inscription."
      submitLabel="Renvoyer"
      send={authApi.resendVerification}
    />
  )
}
