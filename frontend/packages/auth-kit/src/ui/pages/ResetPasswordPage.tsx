import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm, useWatch } from 'react-hook-form'

import { useAuth } from '../../react/context'
import { Alert, AuthCard, Button, Field, PasswordStrength, TextLink } from '../components'
import { applyApiError } from '../forms'
import { useMessages } from '../context'
import { useSchemas } from '../schemas'
import { useLinkToken } from '../useLinkToken'
import type { ResetPasswordForm } from '../schemas'

export function ResetPasswordPage() {
  const { client, paths } = useAuth()
  const m = useMessages()
  const { schemas, rules } = useSchemas()
  const { token } = useLinkToken()
  const [done, setDone] = useState<string | null>(null)
  const form = useForm<ResetPasswordForm>({
    resolver: zodResolver(schemas.resetPassword),
    defaultValues: { new_password: '', new_password_confirm: '' },
  })
  const { errors, isSubmitting } = form.formState
  const password = useWatch({ control: form.control, name: 'new_password' })

  async function onSubmit(values: ResetPasswordForm) {
    if (!token) return
    try {
      setDone((await client.auth.resetPassword(token, values.new_password)).message)
    } catch (error) {
      applyApiError(error, form.setError, ['new_password'])
    }
  }

  if (!token) {
    return (
      <AuthCard title={m.reset.missingTitle} subtitle={m.reset.missingText} icon="alert" tone="danger">
        <TextLink to={paths.forgotPassword}>{m.reset.requestNew}</TextLink>
      </AuthCard>
    )
  }

  if (done) {
    return (
      <AuthCard title={m.reset.doneTitle} subtitle={done} icon="checkCircle" tone="success">
        <TextLink to={paths.login}>{m.reset.signIn}</TextLink>
      </AuthCard>
    )
  }

  return (
    <AuthCard title={m.reset.title} subtitle={m.reset.subtitle} icon="key">
      <form className="ak-stack" onSubmit={form.handleSubmit(onSubmit)} noValidate>
        {errors.root && (
          <Alert>
            {errors.root.message} <TextLink to={paths.forgotPassword}>{m.reset.requestNew}</TextLink>
          </Alert>
        )}
        <Field
          label={m.fields.newPassword}
          icon="lock"
          type="password"
          autoComplete="new-password"
          autoFocus
          hint={m.strength.hint}
          extra={<PasswordStrength password={password} minLength={rules.passwordMinLength} />}
          error={errors.new_password?.message}
          {...form.register('new_password')}
        />
        <Field
          label={m.fields.passwordConfirm}
          icon="lock"
          type="password"
          autoComplete="new-password"
          error={errors.new_password_confirm?.message}
          {...form.register('new_password_confirm')}
        />
        <Button type="submit" block loading={isSubmitting}>
          {m.reset.submit}
        </Button>
      </form>
    </AuthCard>
  )
}
