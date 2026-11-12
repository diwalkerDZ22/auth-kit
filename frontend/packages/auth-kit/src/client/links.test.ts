// @vitest-environment happy-dom
import { describe, expect, it } from 'vitest'

import { readLinkTypeFromUrl, readTokenFromUrl, safeNext, stripTokenFromUrl } from './links'

describe('safeNext', () => {
  it.each([
    ['?next=/profile', '/profile'],
    ['?next=%2Fadmin%2Fusers%3Fpage%3D2', '/admin/users?page=2'],
    ['', '/'],
    ['?next=https://evil.example', '/'],
    ['?next=//evil.example', '/'],
    ['?next=profile', '/'],
    ['?next=/\\evil.example', '/'],
  ])('%s -> %s', (search, expected) => {
    expect(safeNext(search)).toBe(expected)
  })

  it('accepte une page de repli', () => {
    expect(safeNext('', '/accueil')).toBe('/accueil')
  })
})

describe('liens reçus par email', () => {
  it('lit le token et le type, puis retire le token de l’URL', () => {
    window.history.replaceState(null, '', '/verify-email?token=abc_123&type=login')
    expect(readTokenFromUrl()).toBe('abc_123')
    expect(readLinkTypeFromUrl()).toBe('login')

    stripTokenFromUrl()
    expect(window.location.search).toBe('?type=login')
    expect(readTokenFromUrl()).toBeNull()
  })

  it('ignore un type inconnu', () => {
    window.history.replaceState(null, '', '/verify-email?token=x&type=reset')
    expect(readLinkTypeFromUrl()).toBeNull()
  })
})
