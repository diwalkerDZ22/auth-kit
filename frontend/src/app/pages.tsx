import { Link } from 'react-router'

import { useAuth } from '../auth'

export function HomePage() {
  const { status, user } = useAuth()
  return (
    <div className="mx-auto max-w-2xl text-center">
      <h1 className="text-3xl font-semibold tracking-tight">auth-kit</h1>
      <p className="mt-3 text-slate-600">Module d'authentification réutilisable : FastAPI + React.</p>
      <div className="mt-8">
        {status === 'authenticated' && user ? (
          <p className="text-slate-700">
            Connecté en tant que <strong>{user.username}</strong>.{' '}
            <Link to="/profile" className="text-indigo-600 hover:underline">
              Voir mon profil
            </Link>
          </p>
        ) : (
          <div className="flex justify-center gap-3">
            <Link to="/login" className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500">
              Se connecter
            </Link>
            <Link to="/register" className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
              Créer un compte
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}

export function NotFoundPage() {
  return (
    <div className="mx-auto max-w-md text-center">
      <h1 className="text-2xl font-semibold">Page introuvable</h1>
      <Link to="/" className="mt-4 inline-block text-sm text-indigo-600 hover:underline">
        Retour à l'accueil
      </Link>
    </div>
  )
}
