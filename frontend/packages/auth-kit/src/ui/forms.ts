import type { FieldValues, Path, UseFormSetError } from 'react-hook-form'

import { errorMessage, isApiError } from '../client/errors'

/**
 * Affiche une erreur du backend dans un formulaire :
 * - erreurs `fields` sous les champs correspondants ;
 * - le reste dans l'erreur globale `root`.
 */
export function applyApiError<T extends FieldValues>(error: unknown, setError: UseFormSetError<T>, fieldNames: string[]) {
  if (isApiError(error) && Object.keys(error.fields).length) {
    let shown = false
    for (const [field, message] of Object.entries(error.fields)) {
      if (fieldNames.includes(field)) {
        setError(field as Path<T>, { type: 'server', message })
        shown = true
      }
    }
    if (shown) return
  }
  setError('root', { type: 'server', message: errorMessage(error) })
}
