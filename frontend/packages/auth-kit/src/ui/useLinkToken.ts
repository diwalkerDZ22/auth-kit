import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router'

/**
 * Jeton (?token=) et type (?type=) du lien reçu par email, lus via le routeur (marche avec tout
 * type de routeur). Le jeton est ensuite retiré de l'URL (historique, en-tête Referer).
 */
export interface LinkToken {
  token: string | null
  type: 'signup' | 'login' | null
}

export function useLinkToken(): LinkToken {
  const [searchParams, setSearchParams] = useSearchParams()
  const [link] = useState((): LinkToken => {
    const type = searchParams.get('type')
    return { token: searchParams.get('token'), type: type === 'signup' || type === 'login' ? type : null }
  })

  useEffect(() => {
    if (!link.token) return
    setSearchParams(
      (current) => {
        const next = new URLSearchParams(current)
        next.delete('token')
        return next
      },
      { replace: true },
    )
  }, [link.token, setSearchParams])

  return link
}
