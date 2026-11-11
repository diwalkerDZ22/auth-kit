import { Link, NavLink, Outlet } from 'react-router'

import { useAuth } from '../auth'

function navClass({ isActive }: { isActive: boolean }) {
  return `rounded-md px-3 py-1.5 text-sm font-medium transition ${
    isActive ? 'bg-slate-100 text-slate-900' : 'text-slate-600 hover:text-slate-900'
  }`
}

export function Layout() {
  const { status, user, hasPermission } = useAuth()

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <nav className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
          <Link to="/" className="text-base font-semibold tracking-tight">
            auth-kit
          </Link>
          <div className="flex items-center gap-1">
            {status === 'authenticated' && user ? (
              <>
                {hasPermission('users:manage') && (
                  <NavLink to="/admin/users" className={navClass}>
                    Administration
                  </NavLink>
                )}
                <NavLink to="/profile" className={navClass}>
                  {user.username}
                </NavLink>
              </>
            ) : status === 'anonymous' ? (
              <>
                <NavLink to="/login" className={navClass}>
                  Connexion
                </NavLink>
                <NavLink to="/register" className={navClass}>
                  Inscription
                </NavLink>
              </>
            ) : null}
          </div>
        </nav>
      </header>
      <main className="px-4 py-10">
        <Outlet />
      </main>
    </div>
  )
}
