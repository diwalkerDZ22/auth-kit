// @vitest-environment happy-dom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { createAuthClient } from './client'
import type { AuthClient } from './client'

const TOKEN = { access_token: 'access-1', token_type: 'bearer', expires_in: 1800 }

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

let fetchMock: ReturnType<typeof vi.fn>
let clients: AuthClient[] = []

function makeClient(options: Parameters<typeof createAuthClient>[0] = {}) {
  const client = createAuthClient({ fetch: fetchMock as unknown as typeof fetch, channelName: null, ...options })
  clients.push(client)
  return client
}

beforeEach(() => {
  fetchMock = vi.fn()
})

afterEach(() => {
  clients.forEach((client) => client.destroy())
  clients = []
  Reflect.deleteProperty(navigator, 'locks')
})

describe('refreshSession', () => {
  it('ne lance qu’un seul refresh pour des appels simultanés', async () => {
    const client = makeClient()
    let release: (r: Response) => void = () => {}
    fetchMock.mockReturnValueOnce(new Promise<Response>((resolve) => (release = resolve)))

    const first = client.refreshSession()
    const second = client.refreshSession()
    release(json(200, TOKEN))

    expect(await Promise.all([first, second])).toEqual([true, true])
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(client.session.hasSession()).toBe(true)
    expect(client.session.getAccessToken()).toBe('access-1')
  })

  it('envoie le header CSRF et le cookie', async () => {
    const client = makeClient()
    fetchMock.mockResolvedValueOnce(json(200, TOKEN))
    await client.refreshSession()

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/auth/refresh')
    expect(init.method).toBe('POST')
    expect(init.credentials).toBe('include')
    expect(init.headers['X-CSRF-Protection']).toBe('1')
  })

  it('passe par le verrou partagé entre onglets quand le navigateur le propose', async () => {
    const request = vi.fn((_name: string, task: () => Promise<unknown>) => task())
    Object.defineProperty(navigator, 'locks', { value: { request }, configurable: true })
    const client = makeClient({ lockName: 'mon-verrou' })
    fetchMock.mockResolvedValueOnce(json(200, TOKEN))

    expect(await client.refreshSession()).toBe(true)
    expect(request).toHaveBeenCalledWith('mon-verrou', expect.any(Function))
  })

  it('ferme la session si le refresh est refusé', async () => {
    const client = makeClient()
    fetchMock.mockResolvedValueOnce(json(401, { code: 'invalid_refresh_token', message: 'Session expirée.' }))

    expect(await client.refreshSession()).toBe(false)
    expect(client.session.hasSession()).toBe(false)
  })

  it('prévient les abonnés quand la session s’ouvre', async () => {
    const client = makeClient()
    const listener = vi.fn()
    client.session.subscribe(listener)
    fetchMock.mockResolvedValueOnce(json(200, TOKEN))
    await client.refreshSession()
    expect(listener).toHaveBeenCalledTimes(1)
  })
})

describe('configuration', () => {
  it('utilise baseUrl et les préfixes du backend', async () => {
    const client = makeClient({ baseUrl: 'https://api.exemple.fr/', authPrefix: '/compte', adminPrefix: '/gestion' })
    fetchMock.mockResolvedValue(json(200, {}))
    await client.auth.config()
    await client.admin.listRoles()
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      'https://api.exemple.fr/compte/config',
      'https://api.exemple.fr/gestion/roles',
    ])
  })

  it('deux clients sont indépendants', async () => {
    const a = makeClient()
    const b = makeClient()
    fetchMock.mockResolvedValueOnce(json(200, TOKEN))
    await a.refreshSession()
    expect(a.session.hasSession()).toBe(true)
    expect(b.session.hasSession()).toBe(false)
  })
})

describe('connexion', () => {
  it('distingue le lien envoyé (202) de la session directe (200)', async () => {
    const client = makeClient()
    fetchMock.mockResolvedValueOnce(json(202, { code: 'login_email_sent', attempt_id: 'abc', message: 'Lien envoyé.' }))
    expect(await client.auth.login('alice', 'pw')).toEqual({ kind: 'email', attemptId: 'abc', message: 'Lien envoyé.' })
    expect(client.session.hasSession()).toBe(false)

    fetchMock.mockResolvedValueOnce(json(200, TOKEN))
    expect(await client.auth.login('alice', 'pw')).toEqual({ kind: 'session' })
    expect(client.session.hasSession()).toBe(true)
    expect(fetchMock.mock.calls[0][1].body.toString()).toBe('username=alice&password=pw')
  })
})

describe('requêtes authentifiées', () => {
  it('rejoue la requête une fois après un refresh quand l’access token a expiré', async () => {
    const client = makeClient()
    fetchMock.mockResolvedValueOnce(json(200, TOKEN))
    await client.refreshSession()

    const user = { id: 1, username: 'alice' }
    fetchMock
      .mockResolvedValueOnce(json(401, { code: 'invalid_token', message: 'Session invalide.' }))
      .mockResolvedValueOnce(json(200, { ...TOKEN, access_token: 'access-2' }))
      .mockResolvedValueOnce(json(200, user))

    expect(await client.auth.me()).toEqual(user)
    const urls = fetchMock.mock.calls.map(([url]) => url)
    expect(urls).toEqual(['/api/auth/refresh', '/api/auth/me', '/api/auth/refresh', '/api/auth/me'])
    expect(fetchMock.mock.calls[3][1].headers.Authorization).toBe('Bearer access-2')
  })

  it('ne rejoue pas indéfiniment si le refresh échoue', async () => {
    const client = makeClient()
    fetchMock
      .mockResolvedValueOnce(json(401, { code: 'invalid_token', message: 'Session invalide.' }))
      .mockResolvedValueOnce(json(401, { code: 'invalid_refresh_token', message: 'Session expirée.' }))

    await expect(client.auth.me()).rejects.toMatchObject({ code: 'invalid_token', status: 401 })
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('sert aussi pour les routes métier du projet', async () => {
    const client = makeClient()
    fetchMock.mockResolvedValueOnce(json(200, TOKEN)).mockResolvedValueOnce(json(200, { message: 'Bonjour' }))
    await client.refreshSession()
    expect(await client.request('/hello', { query: { lang: 'fr', vide: '' } })).toEqual({ message: 'Bonjour' })
    expect(fetchMock.mock.calls[1][0]).toBe('/api/hello?lang=fr')
    expect(fetchMock.mock.calls[1][1].headers.Authorization).toBe('Bearer access-1')
  })

  it('transforme une panne réseau en erreur network_error', async () => {
    const client = makeClient()
    fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch'))
    await expect(client.auth.forgotPassword('a@example.com')).rejects.toMatchObject({ code: 'network_error' })
  })

  it('garde les erreurs de champ du backend', async () => {
    const client = makeClient()
    fetchMock.mockResolvedValueOnce(
      json(422, { code: 'validation_error', message: 'Données invalides.', fields: { email: 'Adresse email invalide.' } }),
    )
    await expect(client.auth.forgotPassword('x')).rejects.toMatchObject({ fields: { email: 'Adresse email invalide.' } })
  })
})
