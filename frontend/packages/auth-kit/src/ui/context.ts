import { createContext, useContext } from 'react'
import type { ReactNode } from 'react'

import { FR } from './messages'
import type { Messages } from './messages'

export interface Brand {
  /** Nom affiché en haut des cartes d'authentification. */
  name?: string
  /** Logo (remplace le pictogramme par défaut). */
  logo?: ReactNode
}

export interface UIContextValue {
  messages: Messages
  brand: Brand
}

export const UIContext = createContext<UIContextValue>({ messages: FR, brand: {} })

export function useMessages(): Messages {
  return useContext(UIContext).messages
}

export function useBrand(): Brand {
  return useContext(UIContext).brand
}
