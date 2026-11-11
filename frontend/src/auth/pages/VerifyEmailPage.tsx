import { useEffect, useState } from 'react'
import { Link } from 'react-router'

import { authApi } from '../api'
import { Alert, Button, Card } from '../components/ui'
import { errorMessage } from '../errors'
import { readTokenFromUrl, stripTokenFromUrl } from '../forms'
import type { VerifyResponse } from '../types'

/**
 * Page ouverte depuis le lien reçu par email (inscription ou connexion).
 * La confirmation demande un clic : les antivirus qui ouvrent les liens des mails
 * ne consomment pas le lien à la place de l'utilisateur.
 */
export function VerifyEmailPage() {
  const [token] = useState(readTokenFromUrl)
  const [result, setResult] = useState<VerifyResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(stripTokenFromUrl, [])

  async function confirm() {
    if (!token) return
    setLoading(true)
    setError(null)
    try {
      setResult(await authApi.verify(token))
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  if (!token) {
    return (
      <Card title="Lien incomplet" subtitle="Ce lien ne contient pas de jeton de vérification.">
        <Link to="/login" className="text-sm text-indigo-600 hover:underline">
          Retour à la connexion
        </Link>
      </Card>
    )
  }

  if (result?.purpose === 'signup') {
    return (
      <Card title="Email vérifié">
        <div className="space-y-4">
          <Alert tone="success">{result.message}</Alert>
          <Link to="/login" className="block text-center text-sm font-medium text-indigo-600 hover:underline">
            Se connecter
          </Link>
        </div>
      </Card>
    )
  }

  if (result?.purpose === 'login') {
    return (
      <Card title="Connexion approuvée">
        <Alert tone="success">
          {result.message} Vous pouvez fermer cet onglet : la page de connexion d'origine s'ouvre toute seule.
        </Alert>
      </Card>
    )
  }

  return (
    <Card title="Confirmer" subtitle="Cliquez pour confirmer votre adresse email ou approuver la connexion en cours.">
      <div className="space-y-4">
        {error && <Alert>{error}</Alert>}
        <Button className="w-full" loading={loading} onClick={confirm}>
          Confirmer
        </Button>
      </div>
    </Card>
  )
}
