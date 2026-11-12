import { useState } from 'react'
import { useNavigate } from 'react-router'

import { errorMessage } from '../../client/errors'
import type { VerifyResponse } from '../../client/types'
import { useAuth } from '../../react/context'
import { Alert, AuthCard, Button, TextLink } from '../components'
import { useMessages } from '../context'
import { useLinkToken } from '../useLinkToken'

/**
 * Page ouverte depuis le lien reçu par email (inscription ou connexion).
 * La confirmation demande un clic : les antivirus qui ouvrent les liens des mails
 * ne consomment pas le lien à la place de l'utilisateur.
 * Pour une connexion, l'utilisateur peut aussi la refuser (« Ce n'est pas moi »).
 */
export function VerifyEmailPage() {
  const { client, paths, hasFeature } = useAuth()
  const navigate = useNavigate()
  const m = useMessages()
  const { token, type: linkType } = useLinkToken()
  const [result, setResult] = useState<VerifyResponse | null>(null)
  const [denied, setDenied] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState<'confirm' | 'deny' | null>(null)

  async function run(action: 'confirm' | 'deny') {
    if (!token) return
    setPending(action)
    setError(null)
    try {
      if (action === 'confirm') setResult(await client.auth.verify(token))
      else setDenied((await client.auth.denyLogin(token)).message)
    } catch (err) {
      setError(errorMessage(err, m.common.unexpectedError))
    } finally {
      setPending(null)
    }
  }

  if (!token) {
    return (
      <AuthCard title={m.verify.missingTitle} subtitle={m.verify.missingText} icon="alert" tone="danger">
        <TextLink to={paths.login}>{m.common.backToLogin}</TextLink>
      </AuthCard>
    )
  }

  if (denied) {
    return (
      <AuthCard title={m.verify.deniedTitle} subtitle={denied} icon="shieldAlert" tone="danger">
        {hasFeature('password_reset') && (
          <Button variant="primary" block onClick={() => navigate(paths.forgotPassword)}>
            {m.verify.changePassword}
          </Button>
        )}
      </AuthCard>
    )
  }

  if (result?.purpose === 'signup') {
    return (
      <AuthCard title={m.verify.signupDoneTitle} subtitle={result.message} icon="checkCircle" tone="success">
        <TextLink to={paths.login}>{m.verify.signIn}</TextLink>
      </AuthCard>
    )
  }

  if (result?.purpose === 'login') {
    return (
      <AuthCard title={m.verify.loginDoneTitle} subtitle={m.verify.loginDoneText} icon="shieldCheck" tone="success" />
    )
  }

  if (linkType === 'login') {
    return (
      <AuthCard title={m.verify.loginTitle} subtitle={m.verify.loginSubtitle} icon="shield">
        <div className="ak-stack">
          {error && <Alert>{error}</Alert>}
          <Button block icon="check" loading={pending === 'confirm'} disabled={pending !== null} onClick={() => run('confirm')}>
            {m.verify.approve}
          </Button>
          <Button
            variant="danger-soft"
            block
            icon="x"
            loading={pending === 'deny'}
            disabled={pending !== null}
            onClick={() => run('deny')}
          >
            {m.verify.deny}
          </Button>
        </div>
      </AuthCard>
    )
  }

  return (
    <AuthCard title={m.verify.confirmTitle} subtitle={m.verify.confirmSubtitle} icon="mailCheck">
      <div className="ak-stack">
        {error && <Alert>{error}</Alert>}
        <Button block loading={pending === 'confirm'} onClick={() => run('confirm')}>
          {m.verify.confirm}
        </Button>
      </div>
    </AuthCard>
  )
}
