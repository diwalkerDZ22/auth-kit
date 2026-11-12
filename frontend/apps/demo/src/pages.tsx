import { Link } from 'react-router'

import { useAuth } from '@auth-kit/react/react'
import { Icon } from '@auth-kit/react/ui'
import type { IconName } from '@auth-kit/react/ui'

const FEATURES: { icon: IconName; title: string; text: string }[] = [
  { icon: 'mailCheck', title: 'Connexion en deux étapes', text: "Mot de passe, puis lien par email avec l'heure, l'IP et le navigateur de la demande." },
  { icon: 'laptop', title: 'Sessions par appareil', text: 'Chaque appareil a sa session, révocable à distance. Refresh token tournant, stocké hashé.' },
  { icon: 'shieldCheck', title: 'Durci par défaut', text: 'Rate-limit par IP et par compte, mots de passe fuités refusés, aucune fuite d’existence des comptes.' },
  { icon: 'users', title: 'Rôles et permissions', text: 'Gardes côté serveur et côté interface, administration des comptes prête à l’emploi.' },
  { icon: 'sparkles', title: 'Modulaire', text: 'Bibliothèque Python et package React : client, hooks sans interface, ou pages complètes.' },
  { icon: 'moon', title: 'Thème clair et sombre', text: 'Variables CSS personnalisables, suit le système ou le choix de l’utilisateur.' },
]

export function HomePage() {
  const { status, user, paths, hasFeature } = useAuth()

  return (
    <div className="demo-home">
      <section className="demo-hero">
        <span className="demo-eyebrow">
          <Icon name="shield" size={14} /> Module d’authentification réutilisable
        </span>
        <h1 className="demo-hero-title">
          L’authentification, <span className="demo-gradient-text">prête à brancher</span>.
        </h1>
        <p className="demo-hero-text">
          Un backend FastAPI et un package React qui couvrent inscription, connexion par email, sessions, mot de passe
          oublié et administration. Installez, configurez, c’est en place.
        </p>
        <div className="demo-hero-actions">
          {status === 'authenticated' && user ? (
            <>
              <Link to={paths.profile} className="ak-btn ak-btn--primary">
                <Icon name="user" size={17} /> Mon compte
              </Link>
              <Link to="/hello" className="ak-btn ak-btn--secondary">
                Appeler l’API protégée
              </Link>
            </>
          ) : (
            <>
              <Link to={paths.login} className="ak-btn ak-btn--primary">
                Se connecter
              </Link>
              {hasFeature('register') && (
                <Link to={paths.register} className="ak-btn ak-btn--secondary">
                  Créer un compte
                </Link>
              )}
            </>
          )}
        </div>
        {status === 'authenticated' && user && (
          <p className="demo-welcome">
            Connecté en tant que <strong>{user.username}</strong> · rôle {user.role}
          </p>
        )}
      </section>

      <section className="demo-features" aria-label="Fonctionnalités">
        {FEATURES.map((feature) => (
          <article key={feature.title} className="demo-feature">
            <span className="demo-feature-icon">
              <Icon name={feature.icon} size={20} />
            </span>
            <h2>{feature.title}</h2>
            <p>{feature.text}</p>
          </article>
        ))}
      </section>
    </div>
  )
}

export function NotFoundPage() {
  return (
    <div className="ak-scope ak-auth">
      <div className="ak-card ak-center">
        <p className="demo-404">404</p>
        <h1 className="ak-title">Page introuvable</h1>
        <p className="ak-subtitle">Le lien est peut-être incomplet ou la page a été déplacée.</p>
        <div className="ak-body">
          <Link to="/" className="ak-btn ak-btn--secondary">
            <Icon name="arrowLeft" size={17} /> Retour à l’accueil
          </Link>
        </div>
      </div>
    </div>
  )
}
