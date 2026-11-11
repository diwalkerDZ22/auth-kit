import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router'

import { authApi } from '../api'
import { Alert, Button, Card, Field } from '../components/ui'
import { applyApiError, readTokenFromUrl, stripTokenFromUrl } from '../forms'
import { resetPasswordSchema } from '../schemas'
import type { ResetPasswordForm } from '../schemas'

export function ResetPasswordPage() {
  const [token] = useState(readTokenFromUrl)
  const [done, setDone] = useState<string | null>(null)
  const form = useForm<ResetPasswordForm>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { new_password: '', new_password_confirm: '' },
  })
  const { errors, isSubmitting } = form.formState

  useEffect(stripTokenFromUrl, [])

  async function onSubmit(values: ResetPasswordForm) {
    if (!token) return
    try {
      setDone((await authApi.resetPassword(token, values.new_password)).message)
    } catch (error) {
      applyApiError(error, form.setError, ['new_password'])
    }
  }

  if (!token) {
    return (
      <Card title="Lien incomplet" subtitle="Ce lien ne contient pas de jeton de réinitialisation.">
        <Link to="/forgot-password" className="text-sm text-indigo-600 hover:underline">
          Demander un nouveau lien
        </Link>
      </Card>
    )
  }

  if (done) {
    return (
      <Card title="Mot de passe modifié">
        <div className="space-y-4">
          <Alert tone="success">{done}</Alert>
          <Link to="/login" className="block text-center text-sm font-medium text-indigo-600 hover:underline">
            Se connecter
          </Link>
        </div>
      </Card>
    )
  }

  return (
    <Card title="Nouveau mot de passe" subtitle="Toutes vos sessions ouvertes seront fermées.">
      <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)} noValidate>
        {errors.root && (
          <Alert>
            {errors.root.message}{' '}
            <Link to="/forgot-password" className="font-medium underline">
              Demander un nouveau lien
            </Link>
          </Alert>
        )}
        <Field
          label="Nouveau mot de passe"
          type="password"
          autoComplete="new-password"
          hint="Au moins 8 caractères."
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
        <Button type="submit" className="w-full" loading={isSubmitting}>
          Enregistrer
        </Button>
      </form>
    </Card>
  )
}
