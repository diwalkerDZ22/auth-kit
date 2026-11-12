import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { createAuthClient } from '@auth-kit/react/client'
import { AuthProvider } from '@auth-kit/react/react'
import { AuthUIProvider } from '@auth-kit/react/ui'
import '@auth-kit/react/ui/styles.css'

import { App } from './App'
import './demo.css'

// Une instance par application. baseUrl : le proxy Vite (/api -> backend), ou l'URL de l'API.
const authClient = createAuthClient({ baseUrl: import.meta.env.VITE_API_BASE ?? '/api' })

const queryClient = new QueryClient({
  defaultOptions: {
    // Les erreurs 4xx ne se règlent pas en réessayant
    queries: {
      retry: (count, error) => count < 2 && !('status' in error && Number(error.status) >= 400),
      refetchOnWindowFocus: false,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider client={authClient}>
        <AuthUIProvider brand={{ name: 'auth-kit' }}>
          <App />
        </AuthUIProvider>
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>,
)
