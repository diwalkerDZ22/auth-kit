/** Réglages des pages : textes et marque. Facultatif : sans provider, textes français par défaut. */
import { useMemo } from 'react'
import type { ReactNode } from 'react'

import { UIContext } from './context'
import type { Brand } from './context'
import { FR, mergeMessages } from './messages'
import type { MessagesOverride } from './messages'

export function AuthUIProvider({
  messages,
  brand,
  children,
}: {
  messages?: MessagesOverride
  brand?: Brand
  children: ReactNode
}) {
  const value = useMemo(() => ({ messages: mergeMessages(FR, messages), brand: brand ?? {} }), [messages, brand])
  return <UIContext.Provider value={value}>{children}</UIContext.Provider>
}
