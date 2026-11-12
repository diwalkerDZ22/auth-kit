/** Pages « saisissez votre email » : mot de passe oublié et renvoi du mail de vérification. */
import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'

import type { MessageResponse } from '../../client/types'
import { useAuth } from '../../react/context'
import { Alert, AuthCard, Button, Field, TextLink } from '../components'
import { applyApiError } from '../forms'
import type { IconName } from '../icons'
import { useMessages } from '../context'
import { useSchemas } from '../schemas'
import type { EmailForm } from '../schemas'

function EmailRequestPage(props: {
  title: string
  subtitle: string
  submitLabel: string
  icon: IconName
  send: (email: string) => Promise<MessageResponse>
}) {
  const { paths } = useAuth()
  const m = useMessages()
  const { schemas } = useSchemas()
  const [done, setDone] = useState<string | null>(null)
  const form = useForm<EmailForm>({ resolver: zodResolver(schemas.email), defaultValues: { email: '' } })
  const { errors, isSubmitting } = form.formState

  async function onSubmit({ email }: EmailForm) {
    try {
      setDone((await props.send(email)).message)
    } catch (error) {
      applyApiError(error, form.setError, ['email'])
    }
  }

  return (
    <AuthCard title={props.title} subtitle={props.subtitle} icon={props.icon}>
      {done ? (
        <div className="ak-stack">
          <Alert tone="success">{done}</Alert>
          <p className="ak-footer-note">
            <TextLink to={paths.login}>{m.common.backToLogin}</TextLink>
          </p>
        </div>
      ) : (
        <form className="ak-stack" onSubmit={form.handleSubmit(onSubmit)} noValidate>
          {errors.root && <Alert>{errors.root.message}</Alert>}
          <Field
            label={m.fields.email}
            icon="mail"
            type="email"
            autoComplete="email"
            autoFocus
            error={errors.email?.message}
            {...form.register('email')}
          />
          <Button type="submit" block loading={isSubmitting}>
            {props.submitLabel}
          </Button>
          <p className="ak-footer-note">
            <TextLink to={paths.login}>{m.common.backToLogin}</TextLink>
          </p>
        </form>
      )}
    </AuthCard>
  )
}

export function ForgotPasswordPage() {
  const { client } = useAuth()
  const m = useMessages().forgot
  return <EmailRequestPage title={m.title} subtitle={m.subtitle} submitLabel={m.submit} icon="key" send={client.auth.forgotPassword} />
}

export function ResendVerificationPage() {
  const { client } = useAuth()
  const m = useMessages().resend
  return <EmailRequestPage title={m.title} subtitle={m.subtitle} submitLabel={m.submit} icon="mail" send={client.auth.resendVerification} />
}
