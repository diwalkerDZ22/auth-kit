// @vitest-environment happy-dom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { CONFIG, renderApp } from '../test-utils'
import { describeDevice } from './devices'
import { FR, mergeMessages } from './messages'
import { AuthUIProvider } from './provider'
import { createAuthRoutes } from './routes'
import { makeSchemas, rulesFromConfig } from './schemas'
import { passwordScore } from './strength'
import { setThemePreference } from './theme'
import { ThemeToggle } from './ThemeToggle'

afterEach(() => {
  cleanup()
  setThemePreference('system')
})

describe('pages', () => {
  it('la page de connexion masque les liens des fonctionnalités désactivées', async () => {
    const { ui } = renderApp({ initialPath: '/login', config: { ...CONFIG, features: [] }, routes: createAuthRoutes() })
    render(ui)
    expect(await screen.findByRole('button', { name: FR.login.submit })).toBeTruthy()
    expect(screen.queryByText(FR.login.createAccount)).toBeNull()
    expect(screen.queryByText(FR.login.forgot)).toBeNull()
  })

  it('les chemins et les textes sont personnalisables', async () => {
    const { ui } = renderApp({
      initialPath: '/connexion',
      paths: { login: '/connexion', register: '/inscription' },
      routes: createAuthRoutes({ login: '/connexion', register: '/inscription' }),
      wrap: (node) => (
        <AuthUIProvider messages={{ login: { title: 'Sign in', createAccount: 'Join us' } }} brand={{ name: 'Acme' }}>
          {node}
        </AuthUIProvider>
      ),
    })
    render(ui)
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeTruthy()
    expect(screen.getByText('Acme')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Join us' }).getAttribute('href')).toBe('/inscription')
    // Les textes non remplacés restent ceux par défaut
    expect(screen.getByRole('button', { name: FR.login.submit })).toBeTruthy()
  })

  it('valide le formulaire avant d’appeler le backend', async () => {
    const { ui } = renderApp({ initialPath: '/login', routes: createAuthRoutes() })
    render(ui)
    fireEvent.click(await screen.findByRole('button', { name: FR.login.submit }))
    expect(await screen.findAllByText(FR.validation.required)).toHaveLength(2)
  })

  it('le lien de connexion propose d’approuver ou de refuser', async () => {
    const { ui } = renderApp({ initialPath: '/verify-email?token=abc&type=login', routes: createAuthRoutes() })
    render(ui)
    expect(await screen.findByRole('button', { name: FR.verify.approve })).toBeTruthy()
    expect(screen.getByRole('button', { name: FR.verify.deny })).toBeTruthy()
  })
})

describe('thème', () => {
  it('applique et mémorise le choix', () => {
    render(<ThemeToggle />)
    fireEvent.click(screen.getByRole('button', { name: FR.theme.dark }))
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(localStorage.getItem('auth-kit-theme')).toBe('dark')
    expect(screen.getByRole('button', { name: FR.theme.dark }).getAttribute('aria-pressed')).toBe('true')

    fireEvent.click(screen.getByRole('button', { name: FR.theme.system }))
    expect(document.documentElement.dataset.theme).toBeUndefined()
    expect(localStorage.getItem('auth-kit-theme')).toBeNull()
  })
})

describe('outils', () => {
  it('fusionne les textes par section', () => {
    const messages = mergeMessages(FR, { login: { title: 'Sign in' } })
    expect(messages.login.title).toBe('Sign in')
    expect(messages.login.submit).toBe(FR.login.submit)
    expect(messages.register).toBe(FR.register)
  })

  it('construit les règles des formulaires depuis la config du backend', () => {
    const rules = rulesFromConfig({ ...CONFIG, password: { min_length: 12, max_bytes: 72, breach_check: true } })
    const schemas = makeSchemas(rules, FR.validation)
    const result = schemas.resetPassword.safeParse({ new_password: 'onze-carac', new_password_confirm: 'onze-carac' })
    expect(result.success).toBe(false)
    expect(result.error?.issues[0].message).toBe(FR.validation.passwordMin(12))
  })

  it('évalue la solidité d’un mot de passe', () => {
    expect(passwordScore('court')).toBe(0)
    expect(passwordScore('motdepasse')).toBe(1)
    expect(passwordScore('cheval batterie agrafe correcte')).toBe(4)
  })

  it('décrit un appareil à partir du user-agent', () => {
    const firefox = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0'
    const iphone = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1'
    expect(describeDevice(firefox)).toEqual({ label: 'Firefox · Windows', mobile: false })
    expect(describeDevice(iphone)).toEqual({ label: 'Safari · iOS', mobile: true })
    expect(describeDevice(null)).toEqual({ label: null, mobile: false })
  })
})

describe('liens reçus par email', () => {
  it('retire le jeton de l’URL après l’avoir lu', async () => {
    const { ui, router } = renderApp({ initialPath: '/reset-password?token=secret&type=reset', routes: createAuthRoutes() })
    render(ui)
    expect(await screen.findByRole('heading', { name: FR.reset.title })).toBeTruthy()
    expect(router.state.location.search).toBe('?type=reset')
  })
})
