/** Erreur renvoyée par le backend au format {"code", "message", "fields"?} (docs/Sprint3-Format-erreurs.md). */
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly fields: Record<string, string>

  constructor(status: number, code: string, message: string, fields: Record<string, string> = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.fields = fields
  }
}

export const NETWORK_ERROR = new ApiError(0, 'network_error', 'Serveur injoignable, vérifiez votre connexion.')

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError
}

/** Message affichable pour n'importe quelle erreur. */
export function errorMessage(error: unknown): string {
  if (isApiError(error)) return error.message
  return 'Une erreur inattendue est survenue.'
}
