import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm, useWatch } from 'react-hook-form'

import { errorMessage } from '../../client/errors'
import { useAuth } from '../../react/context'
import { Alert, AuthCard, Button, Field, PasswordStrength, TextLink } from '../components'
import { applyApiError } from '../forms'
import { useMessages } from '../context'
import { useSchemas } from '../schemas'
import type { RegisterForm } from '../schemas'

const FIELDS = ['username', 'email', 'full_name', 'password', 'password_confirm']

export function RegisterPage() {
  const { client, paths, hasFeature } = useAuth()
  const m = useMessages()
  const { schemas, rules } = useSchemas()
  const [registeredEmail, setRegisteredEmail] = useState<string | null>(null)
  const form = useForm<RegisterForm>({
    resolver: zodResolver(schemas.register),
    defaultValues: { username: '', email: '', full_name: '', password: '', password_confirm: '' },
  })
  const { errors, isSubmitting } = form.formState
  const password = useWatch({ control: form.control, name: 'password' })

  if (!hasFeature('register')) {
    return (
      <AuthCard title={m.register.closedTitle} subtitle={m.register.closedText} icon="lock">
        <TextLink to={paths.login}>{m.common.backToLogin}</TextLink>
      </AuthCard>
    )
  }

  async function onSubmit(values: RegisterForm) {
    try {
      await client.auth.register({
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
    <AuthCard title={m.register.title} subtitle={m.register.subtitle}>
      <form className="ak-stack" onSubmit={form.handleSubmit(onSubmit)} noValidate>
        {errors.root && <Alert>{errors.root.message}</Alert>}
        <Field
          label={m.fields.username}
          icon="user"
          autoComplete="username"
          autoFocus
          hint={m.register.usernameHint}
          error={errors.username?.message}
          {...form.register('username')}
        />
        <Field label={m.fields.email} icon="mail" type="email" autoComplete="email" error={errors.email?.message} {...form.register('email')} />
        <Field label={m.fields.fullNameOptional} autoComplete="name" error={errors.full_name?.message} {...form.register('full_name')} />
        <Field
          label={m.fields.password}
          icon="lock"
          type="password"
          autoComplete="new-password"
          hint={m.strength.hint}
          extra={<PasswordStrength password={password} minLength={rules.passwordMinLength} />}
          error={errors.password?.message}
          {...form.register('password')}
        />
        <Field
          label={m.fields.passwordConfirm}
          icon="lock"
          type="password"
          autoComplete="new-password"
          error={errors.password_confirm?.message}
          {...form.register('password_confirm')}
        />
        <Button type="submit" block loading={isSubmitting}>
          {m.register.submit}
        </Button>
        <p className="ak-footer-note">
          {m.register.haveAccount} <TextLink to={paths.login}>{m.register.signIn}</TextLink>
        </p>
      </form>
    </AuthCard>
  )
}

function CheckYourInbox({ email }: { email: string }) {
  const { client, paths } = useAuth()
  const m = useMessages()
  const [status, setStatus] = useState<{ tone: 'success' | 'error'; text: string } | null>(null)
  const [sending, setSending] = useState(false)

  async function resend() {
    setSending(true)
    try {
      setStatus({ tone: 'success', text: (await client.auth.resendVerification(email)).message })
    } catch (error) {
      setStatus({ tone: 'error', text: errorMessage(error, m.common.unexpectedError) })
    } finally {
      setSending(false)
    }
  }

  return (
    <AuthCard title={m.register.inboxTitle} subtitle={m.register.inboxText(email)} icon="mailCheck" tone="success">
      <div className="ak-stack">
        {status && <Alert tone={status.tone}>{status.text}</Alert>}
        <Button variant="secondary" block loading={sending} onClick={resend}>
          {m.register.resend}
        </Button>
        <p className="ak-footer-note">
          <TextLink to={paths.login}>{m.common.backToLogin}</TextLink>
        </p>
      </div>
    </AuthCard>
  )
}
