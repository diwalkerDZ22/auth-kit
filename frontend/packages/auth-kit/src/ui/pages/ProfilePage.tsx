import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { useNavigate } from 'react-router'

import { errorMessage } from '../../client/errors'
import type { UserSession } from '../../client/types'
import { ME_QUERY_KEY, SESSIONS_QUERY_KEY, useAuth } from '../../react/context'
import { useDevices } from '../../react/hooks'
import { Alert, Avatar, Badge, Button, Field, PasswordStrength, Section, Spinner } from '../components'
import { applyApiError } from '../forms'
import { describeDevice } from '../devices'
import { Icon } from '../icons'
import { useMessages } from '../context'
import { useSchemas } from '../schemas'
import type { ChangePasswordForm, ProfileForm } from '../schemas'

export function ProfilePage() {
  const { user, logout, paths, hasFeature } = useAuth()
  const m = useMessages().profile
  const navigate = useNavigate()
  const [loggingOut, setLoggingOut] = useState(false)
  if (!user) return null

  async function onLogout() {
    setLoggingOut(true)
    try {
      await logout()
    } finally {
      navigate(paths.login, { replace: true })
    }
  }

  return (
    <div className="ak-scope ak-page">
      <section className="ak-section">
        <div className="ak-profile-hero">
          <Avatar name={user.full_name || user.username} />
          <div className="ak-grow">
            <h1 className="ak-page-title ak-ellipsis">{user.full_name || user.username}</h1>
            <p className="ak-item-meta ak-ellipsis">
              @{user.username} · {user.email}
            </p>
            <div className="ak-row" style={{ marginTop: 10 }}>
              <Badge tone="indigo" plain>
                {m.role} : {user.role}
              </Badge>
            </div>
          </div>
          <Button variant="secondary" icon="logout" loading={loggingOut} onClick={onLogout}>
            {m.logout}
          </Button>
        </div>
      </section>
      <div className="ak-grid-2" style={{ marginTop: 20 }}>
        <ProfileSection fullName={user.full_name ?? ''} />
        <PasswordSection />
      </div>
      {hasFeature('devices') && <DevicesSection />}
    </div>
  )
}

function ProfileSection({ fullName }: { fullName: string }) {
  const { client } = useAuth()
  const m = useMessages()
  const { schemas } = useSchemas()
  const queryClient = useQueryClient()
  const [saved, setSaved] = useState(false)
  const form = useForm<ProfileForm>({ resolver: zodResolver(schemas.profile), defaultValues: { full_name: fullName } })
  const { errors } = form.formState

  const mutation = useMutation({
    mutationFn: (values: ProfileForm) => client.auth.updateMe(values.full_name || null),
    onSuccess: (user) => {
      queryClient.setQueryData(ME_QUERY_KEY, user)
      setSaved(true)
    },
    onError: (error) => applyApiError(error, form.setError, ['full_name']),
  })

  return (
    <Section title={m.profile.profileTitle} description={m.profile.profileDesc}>
      <form
        className="ak-stack"
        onSubmit={form.handleSubmit((values) => {
          setSaved(false)
          mutation.mutate(values)
        })}
        noValidate
      >
        {saved && <Alert tone="success">{m.profile.saved}</Alert>}
        {errors.root && <Alert>{errors.root.message}</Alert>}
        <Field label={m.fields.fullName} icon="user" autoComplete="name" error={errors.full_name?.message} {...form.register('full_name')} />
        <div>
          <Button type="submit" loading={mutation.isPending}>
            {m.profile.save}
          </Button>
        </div>
      </form>
    </Section>
  )
}

function PasswordSection() {
  const { client } = useAuth()
  const m = useMessages()
  const { schemas, rules } = useSchemas()
  const queryClient = useQueryClient()
  const [saved, setSaved] = useState(false)
  const form = useForm<ChangePasswordForm>({
    resolver: zodResolver(schemas.changePassword),
    defaultValues: { current_password: '', new_password: '', new_password_confirm: '' },
  })
  const { errors } = form.formState
  const password = useWatch({ control: form.control, name: 'new_password' })

  const mutation = useMutation({
    mutationFn: (values: ChangePasswordForm) => client.auth.changePassword(values.current_password, values.new_password),
    onSuccess: () => {
      form.reset()
      setSaved(true)
      // Les autres appareils viennent d'être déconnectés
      void queryClient.invalidateQueries({ queryKey: SESSIONS_QUERY_KEY })
    },
    onError: (error) => applyApiError(error, form.setError, ['current_password', 'new_password']),
  })

  return (
    <Section title={m.profile.passwordTitle} description={m.profile.passwordDesc}>
      <form
        className="ak-stack"
        onSubmit={form.handleSubmit((values) => {
          setSaved(false)
          mutation.mutate(values)
        })}
        noValidate
      >
        {saved && <Alert tone="success">{m.profile.passwordSaved}</Alert>}
        {errors.root && <Alert>{errors.root.message}</Alert>}
        <Field
          label={m.fields.currentPassword}
          type="password"
          autoComplete="current-password"
          error={errors.current_password?.message}
          {...form.register('current_password')}
        />
        <Field
          label={m.fields.newPassword}
          type="password"
          autoComplete="new-password"
          extra={<PasswordStrength password={password} minLength={rules.passwordMinLength} />}
          error={errors.new_password?.message}
          {...form.register('new_password')}
        />
        <Field
          label={m.fields.passwordConfirm}
          type="password"
          autoComplete="new-password"
          error={errors.new_password_confirm?.message}
          {...form.register('new_password_confirm')}
        />
        <div>
          <Button type="submit" loading={mutation.isPending}>
            {m.profile.passwordSubmit}
          </Button>
        </div>
      </form>
    </Section>
  )
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

function DevicesSection() {
  const m = useMessages().profile
  const { sessions, revoke, revokeOthers } = useDevices()
  const others = sessions.data?.filter((s) => !s.current) ?? []
  const error = sessions.error ?? revoke.error ?? revokeOthers.error
  const notice = revokeOthers.data?.message ?? revoke.data?.message

  return (
    <div style={{ marginTop: 20 }}>
      <Section
        title={m.devicesTitle}
        description={m.devicesDesc}
        footer={
          others.length > 0 && (
            <Button variant="danger-soft" size="sm" icon="logout" loading={revokeOthers.isPending} onClick={() => revokeOthers.mutate()}>
              {m.disconnectOthers}
            </Button>
          )
        }
      >
        <div className="ak-stack">
          {notice && <Alert tone="success">{notice}</Alert>}
          {error && <Alert>{errorMessage(error)}</Alert>}
          {sessions.isPending ? (
            <Spinner />
          ) : (
            <ul className="ak-list">
              {sessions.data?.map((session) => (
                <DeviceRow
                  key={session.id}
                  session={session}
                  revoking={revoke.isPending && revoke.variables === session.id}
                  onRevoke={() => revoke.mutate(session.id)}
                />
              ))}
            </ul>
          )}
        </div>
      </Section>
    </div>
  )
}

function DeviceRow({ session, revoking, onRevoke }: { session: UserSession; revoking: boolean; onRevoke: () => void }) {
  const m = useMessages().profile
  const device = describeDevice(session.user_agent)
  return (
    <li className="ak-list-item">
      <span className={`ak-icon-tile${session.current ? ' ak-icon-tile--current' : ''}`}>
        <Icon name={device.mobile ? 'phone' : 'laptop'} size={20} />
      </span>
      <div className="ak-grow">
        <p className="ak-item-title">
          {device.label ?? m.unknownDevice}
          {session.current && <Badge tone="green">{m.thisDevice}</Badge>}
        </p>
        <p className="ak-item-meta">
          {session.ip ?? m.unknownIp} · {m.activeOn(formatDate(session.last_used_at))} · {m.signedInOn(formatDate(session.created_at))}
        </p>
      </div>
      {!session.current && (
        <Button variant="secondary" size="sm" loading={revoking} onClick={onRevoke}>
          {m.disconnect}
        </Button>
      )}
    </li>
  )
}
