import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createBrowserRouter, RouterProvider } from 'react-router'

import { AuthProvider, authRoutes } from '../auth'
import { Layout } from './Layout'
import { HomePage, NotFoundPage } from './pages'

const queryClient = new QueryClient({
  defaultOptions: {
    // Les erreurs 4xx ne se règlent pas en réessayant
    queries: { retry: (count, error) => count < 2 && !('status' in error && Number(error.status) >= 400), refetchOnWindowFocus: false },
  },
})

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: '/', element: <HomePage /> },
      ...authRoutes,
      // Les routes métier du projet viennent ici, protégées par <RequireAuth> / <RequirePermission>
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryClientProvider>
  )
}
