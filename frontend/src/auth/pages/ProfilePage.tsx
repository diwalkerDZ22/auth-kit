import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router'

import { authApi } from '../api'
import { ME_QUERY_KEY, useAuth } from '../context'
import { Alert, Button, Card, Field } from '../components/ui'
import { applyApiError } from '../forms'
import { changePasswordSchema, profileSchema } from '../schemas'
import type { ChangePasswordForm, ProfileForm } from '../schemas'

export function ProfilePage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [loggingOut, setLoggingOut] = useState(false)
  if (!user) return null

  async function onLogout() {
    setLoggingOut(true)
    try {
      await logout()
    } finally {
      navigate('/login', { replace: true })
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">{user.full_name || user.username}</h1>
            <p className="mt-1 text-sm text-slate-600">
              {user.username} · {user.email}
            </p>
            <p className="mt-2 inline-block rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700">
              Rôle : {user.role}
            </p>
          </div>
          <Button variant="secondary" loading={loggingOut} onClick={onLogout}>
            Se déconnecter
          </Button>
        </div>
      </section>
      <ProfileSection fullName={user.full_name ?? ''} />
      <PasswordSection />
    </div>
  )
}

function ProfileSection({ fullName }: { fullName: string }) {
  const queryClient = useQueryClient()
  const [saved, setSaved] = useState(false)
  const form = useForm<ProfileForm>({ resolver: zodResolver(profileSchema), defaultValues: { full_name: fullName } })
  const { errors } = form.formState

  const mutation = useMutation({
    mutationFn: (values: ProfileForm) => authApi.updateMe(values.full_name || null),
    onSuccess: (user) => {
      queryClient.setQueryData(ME_QUERY_KEY, user)
      setSaved(true)
    },
    onError: (error) => applyApiError(error, form.setError, ['full_name']),
  })

  return (
    <Card title="Profil">
      <form
        className="space-y-4"
        onSubmit={form.handleSubmit((values) => {
          setSaved(false)
          mutation.mutate(values)
        })}
        noValidate
      >
        {saved && <Alert tone="success">Profil enregistré.</Alert>}
        {errors.root && <Alert>{errors.root.message}</Alert>}
        <Field label="Nom complet" autoComplete="name" error={errors.full_name?.message} {...form.register('full_name')} />
        <Button type="submit" loading={mutation.isPending}>
          Enregistrer
        </Button>
      </form>
    </Card>
  )
}

function PasswordSection() {
  const [saved, setSaved] = useState(false)
  const form = useForm<ChangePasswordForm>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: { current_password: '', new_password: '', new_password_confirm: '' },
  })
  const { errors } = form.formState

  const mutation = useMutation({
    mutationFn: (values: ChangePasswordForm) => authApi.changePassword(values.current_password, values.new_password),
    onSuccess: () => {
      form.reset()
      setSaved(true)
    },
    onError: (error) => applyApiError(error, form.setError, ['current_password', 'new_password']),
  })

  return (
    <Card title="Mot de passe" subtitle="Vos autres sessions ouvertes seront fermées.">
      <form
        className="space-y-4"
        onSubmit={form.handleSubmit((values) => {
          setSaved(false)
          mutation.mutate(values)
        })}
        noValidate
      >
        {saved && <Alert tone="success">Mot de passe modifié.</Alert>}
        {errors.root && <Alert>{errors.root.message}</Alert>}
        <Field
          label="Mot de passe actuel"
          type="password"
          autoComplete="current-password"
          error={errors.current_password?.message}
          {...form.register('current_password')}
        />
        <Field
          label="Nouveau mot de passe"
          type="password"
          autoComplete="new-password"
          error={errors.new_password?.message}
          {...form.register('new_password')}
        />
        <Field
          label="Confirmer"
          type="password"
          autoComplete="new-password"
          error={errors.new_password_confirm?.message}
          {...form.register('new_password_confirm')}
        />
        <Button type="submit" loading={mutation.isPending}>
          Changer le mot de passe
        </Button>
      </form>
    </Card>
  )
}
