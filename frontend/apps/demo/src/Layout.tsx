import { Link, NavLink, Outlet } from 'react-router'

import { ADMIN_PERMISSION, useAuth } from '@auth-kit/react/react'
import { Avatar, Icon, ThemeToggle } from '@auth-kit/react/ui'

function navClass({ isActive }: { isActive: boolean }) {
  return `demo-nav-link${isActive ? ' is-active' : ''}`
}

export function Layout() {
  const { status, user, hasPermission, hasFeature, paths } = useAuth()

  return (
    <div className="demo-shell">
      <header className="demo-header">
        <nav className="demo-nav" aria-label="Navigation principale">
          <Link to="/" className="demo-logo">
            <span className="ak-brand-mark">
              <Icon name="shield" size={17} />
            </span>
            auth-kit
          </Link>

          <div className="demo-nav-links">
            {status === 'authenticated' && (
              <NavLink to="/hello" className={navClass}>
                API protégée
              </NavLink>
            )}
            {status === 'authenticated' && hasPermission(ADMIN_PERMISSION) && (
              <NavLink to={paths.adminUsers} className={navClass}>
                Administration
              </NavLink>
            )}
          </div>

          <div className="demo-nav-end">
            <ThemeToggle />
            {status === 'authenticated' && user ? (
              <NavLink to={paths.profile} className="demo-account" title="Mon profil">
                <Avatar name={user.full_name || user.username} small />
                <span className="demo-account-name">{user.full_name || user.username}</span>
              </NavLink>
            ) : status === 'anonymous' ? (
              <>
                <NavLink to={paths.login} className={navClass}>
                  Connexion
                </NavLink>
                {hasFeature('register') && (
                  <Link to={paths.register} className="ak-btn ak-btn--primary ak-btn--sm">
                    Créer un compte
                  </Link>
                )}
              </>
            ) : null}
          </div>
        </nav>
      </header>
      <main className="demo-main">
        <Outlet />
      </main>
      <footer className="demo-footer">
        auth-kit · FastAPI + React · thème clair, sombre ou système
      </footer>
    </div>
  )
}
