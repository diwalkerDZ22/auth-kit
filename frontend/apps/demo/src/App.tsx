import { createBrowserRouter, RouterProvider } from 'react-router'

import { RequireAuth } from '@auth-kit/react/react'
import { createAuthRoutes, FullPageSpinner } from '@auth-kit/react/ui'

import { HelloPage } from './HelloPage'
import { Layout } from './Layout'
import { HomePage, NotFoundPage } from './pages'

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: '/', element: <HomePage /> },
      ...createAuthRoutes(),
      // Routes métier du projet, protégées par les gardes du kit
      { path: '/hello', element: <RequireAuth loading={<FullPageSpinner />}><HelloPage /></RequireAuth> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])

export function App() {
  return <RouterProvider router={router} />
}
