// @vitest-environment happy-dom
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { ALICE, renderApp } from '../test-utils'
import { useAuth } from './context'
import { GuestOnly, RequireAuth, RequirePermission } from './guards'

afterEach(cleanup)

function Whoami() {
  const { user, hasFeature } = useAuth()
  return (
    <p>
      {user?.username ?? 'anonyme'} {hasFeature('register') ? 'inscription-ouverte' : 'inscription-fermee'}
    </p>
  )
}

describe('gardes de routes', () => {
  it('redirige un visiteur vers la page de connexion configurée, avec ?next=', async () => {
    const { ui, router } = renderApp({
      initialPath: '/secret?x=1',
      paths: { login: '/connexion' },
      routes: [
        { path: '/secret', element: <RequireAuth>secret</RequireAuth> },
        { path: '/connexion', element: <p>page de connexion</p> },
      ],
    })
    render(ui)
    expect(await screen.findByText('page de connexion')).toBeTruthy()
    expect(router.state.location.search).toBe(`?next=${encodeURIComponent('/secret?x=1')}`)
  })

  it('restaure la session depuis le cookie et affiche la page', async () => {
    const { ui } = renderApp({
      initialPath: '/secret',
      user: ALICE,
      routes: [{ path: '/secret', element: <RequireAuth><Whoami /></RequireAuth> }],
    })
    render(ui)
    expect(await screen.findByText(/alice inscription-ouverte/)).toBeTruthy()
  })

  it('affiche le repli sans la permission', async () => {
    const { ui } = renderApp({
      initialPath: '/admin',
      user: ALICE,
      routes: [
        {
          path: '/admin',
          element: <RequirePermission permission="users:manage" fallback={<p>refusé</p>}>admin</RequirePermission>,
        },
      ],
    })
    render(ui)
    expect(await screen.findByText('refusé')).toBeTruthy()
  })

  it('renvoie un utilisateur connecté vers l’accueil configuré', async () => {
    const { ui } = renderApp({
      initialPath: '/login',
      user: ALICE,
      paths: { home: '/tableau-de-bord' },
      routes: [
        { path: '/login', element: <GuestOnly>formulaire</GuestOnly> },
        { path: '/tableau-de-bord', element: <p>tableau de bord</p> },
      ],
    })
    render(ui)
    expect(await screen.findByText('tableau de bord')).toBeTruthy()
  })

  it('suit les fonctionnalités annoncées par le backend', async () => {
    const { ui } = renderApp({
      initialPath: '/',
      config: { ...(await import('../test-utils')).CONFIG, features: [] },
      routes: [{ path: '/', element: <Whoami /> }],
    })
    render(ui)
    expect(await screen.findByText(/inscription-fermee/)).toBeTruthy()
  })
})
