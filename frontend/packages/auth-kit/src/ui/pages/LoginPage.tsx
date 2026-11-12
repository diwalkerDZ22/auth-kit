import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useLocation, useNavigate } from 'react-router'

import { errorMessage, isApiError } from '../../client/errors'
import { safeNext } from '../../client/links'
import { useAuth } from '../../react/context'
import { useLoginFlow } from '../../react/hooks'
import { Alert, AuthCard, Button, Field, TextLink } from '../components'
import { applyApiError } from '../forms'
import { Icon } from '../icons'
import { useMessages } from '../context'
import { useSchemas } from '../schemas'
import type { LoginForm } from '../schemas'

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { paths, hasFeature, config } = useAuth()
  const m = useMessages()
  const { schemas } = useSchemas()
  const next = safeNext(location.search, paths.home)
  const [notVerified, setNotVerified] = useState(false)

  const flow = useLoginFlow({ onSuccess: () => navigate(next, { replace: true }) })
  const form = useForm<LoginForm>({ resolver: zodResolver(schemas.login), defaultValues: { username: '', password: '' } })
  const { errors, isSubmitting } = form.formState

  async function onSubmit(values: LoginForm) {
    setNotVerified(false)
    try {
      await flow.submit(values.username, values.password)
    } catch (error) {
      if (isApiError(error) && error.code === 'email_not_verified') setNotVerified(true)
      applyApiError(error, form.setError, ['username', 'password'])
    }
  }

  if (flow.attempt) {
    return (
      <AuthCard title={m.login.waitingTitle} subtitle={flow.attempt.message}>
        <div className="ak-stack ak-stack--lg">
          <div className="ak-waiting">
            <Icon name="mail" size={34} />
          </div>
          <ol className="ak-steps">
            {m.login.waitingSteps.map((step, index) => (
              <li key={step}>
                <span className="ak-step-num">{index + 1}</span>
                <span>{step}</span>
              </li>
            ))}
          </ol>
          <p className="ak-hint ak-center">{m.login.waitingHint}</p>
          <Button variant="secondary" block icon="arrowLeft" onClick={flow.cancel}>
            {m.login.cancel}
          </Button>
        </div>
      </AuthCard>
    )
  }

  const pollError = flow.pollError === 'expired' ? m.login.expired : flow.pollError ? errorMessage(flow.pollError) : null
  const subtitle = config?.login_email_required === false ? m.login.subtitleDirect : m.login.subtitle

  return (
    <AuthCard title={m.login.title} subtitle={subtitle}>
      <form className="ak-stack" onSubmit={form.handleSubmit(onSubmit)} noValidate>
        {pollError && <Alert>{pollError}</Alert>}
        {errors.root && (
          <Alert>
            {errors.root.message}
            {notVerified && hasFeature('register') && (
              <>
                {' '}
                <TextLink to={paths.resendVerification}>{m.login.resendLink}</TextLink>
              </>
            )}
          </Alert>
        )}
        <Field
          label={m.fields.username}
          icon="user"
          autoComplete="username"
          autoFocus
          error={errors.username?.message}
          {...form.register('username')}
        />
        <Field
          label={m.fields.password}
          icon="lock"
          type="password"
          autoComplete="current-password"
          error={errors.password?.message}
          aside={
            hasFeature('password_reset') && (
              <TextLink to={paths.forgotPassword} subtle>
                {m.login.forgot}
              </TextLink>
            )
          }
          {...form.register('password')}
        />
        <Button type="submit" block loading={isSubmitting}>
          {m.login.submit}
        </Button>
        {hasFeature('register') && (
          <p className="ak-footer-note">
            {m.login.noAccount} <TextLink to={paths.register}>{m.login.createAccount}</TextLink>
          </p>
        )}
      </form>
    </AuthCard>
  )
}
