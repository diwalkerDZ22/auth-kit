/** @auth-kit/react/client : client HTTP du backend auth-kit, sans React. */
export { createAuthClient } from './client'
export type { AuthClient, AuthClientOptions, RawResponse, RequestOptions } from './client'
export { ApiError, errorMessage, isApiError, networkError } from './errors'
export { readLinkTypeFromUrl, readTokenFromUrl, safeNext, stripTokenFromUrl } from './links'
export type * from './types'
