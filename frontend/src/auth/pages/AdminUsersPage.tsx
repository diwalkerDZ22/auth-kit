import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { adminApi } from '../api'
import { useAuth } from '../context'
import { Alert, Button, Spinner } from '../components/ui'
import { errorMessage } from '../errors'
import type { AdminUser } from '../types'

const PAGE_SIZE = 20

function useDebounced<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return debounced
}

export function AdminUsersPage() {
  const { user: me } = useAuth()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)
  const debouncedSearch = useDebounced(search.trim())

  const users = useQuery({
    queryKey: ['admin', 'users', debouncedSearch, page],
    queryFn: () => adminApi.listUsers({ search: debouncedSearch, limit: PAGE_SIZE, offset: page * PAGE_SIZE }),
    placeholderData: keepPreviousData,
  })
  const roles = useQuery({ queryKey: ['admin', 'roles'], queryFn: adminApi.listRoles, staleTime: 10 * 60_000 })

  const total = users.data?.total ?? 0
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Utilisateurs</h1>
          <p className="mt-1 text-sm text-slate-600">{total} compte{total > 1 ? 's' : ''}</p>
        </div>
        <input
          type="search"
          value={search}
          onChange={(event) => {
            setSearch(event.target.value)
            setPage(0)
          }}
          placeholder="Rechercher (username ou email)"
          aria-label="Rechercher un utilisateur"
          className="w-full max-w-xs rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
        />
      </div>

      {users.isError && <Alert>{errorMessage(users.error)}</Alert>}

      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Utilisateur</th>
              <th className="px-4 py-3">Email</th>
              <th className="px-4 py-3">Rôle</th>
              <th className="px-4 py-3">Statut</th>
              <th className="px-4 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {users.isPending && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-slate-500">
                  <Spinner className="mx-auto h-5 w-5" />
                </td>
              </tr>
            )}
            {users.data?.items.map((user) => (
              <UserRow key={user.id} user={user} roles={roles.data?.map((r) => r.name) ?? [user.role]} isMe={user.id === me?.id} />
            ))}
            {users.data && users.data.items.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-slate-500">
                  Aucun utilisateur trouvé.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-sm text-slate-600">
        <span>
          Page {page + 1} / {pageCount}
        </span>
        <div className="flex gap-2">
          <Button variant="secondary" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
            Précédent
          </Button>
          <Button variant="secondary" disabled={page + 1 >= pageCount} onClick={() => setPage((p) => p + 1)}>
            Suivant
          </Button>
        </div>
      </div>
    </div>
  )
}

function UserRow({ user, roles, isMe }: { user: AdminUser; roles: string[]; isMe: boolean }) {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: (changes: { role?: string; disabled?: boolean }) => adminApi.updateUser(user.id, changes),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'users'] }),
  })

  return (
    <tr className={user.disabled ? 'bg-slate-50 text-slate-500' : undefined}>
      <td className="px-4 py-3">
        <div className="font-medium text-slate-900">{user.username}</div>
        {user.full_name && <div className="text-xs text-slate-500">{user.full_name}</div>}
        {mutation.isError && <div className="mt-1 text-xs text-red-600">{errorMessage(mutation.error)}</div>}
      </td>
      <td className="px-4 py-3">{user.email}</td>
      <td className="px-4 py-3">
        <select
          value={user.role}
          disabled={isMe || mutation.isPending}
          onChange={(event) => mutation.mutate({ role: event.target.value })}
          aria-label={`Rôle de ${user.username}`}
          className="rounded-md border border-slate-300 bg-white px-2 py-1 text-sm disabled:bg-slate-100"
        >
          {roles.map((role) => (
            <option key={role} value={role}>
              {role}
            </option>
          ))}
        </select>
      </td>
      <td className="px-4 py-3">
        <span className="flex flex-wrap gap-1">
          <Badge tone={user.disabled ? 'red' : 'green'}>{user.disabled ? 'Désactivé' : 'Actif'}</Badge>
          {!user.is_verified && <Badge tone="amber">Email non vérifié</Badge>}
        </span>
      </td>
      <td className="px-4 py-3 text-right">
        {isMe ? (
          <span className="text-xs text-slate-400">Vous</span>
        ) : (
          <Button
            variant={user.disabled ? 'secondary' : 'danger'}
            loading={mutation.isPending}
            onClick={() => mutation.mutate({ disabled: !user.disabled })}
          >
            {user.disabled ? 'Réactiver' : 'Désactiver'}
          </Button>
        )}
      </td>
    </tr>
  )
}

function Badge({ tone, children }: { tone: 'green' | 'red' | 'amber'; children: string }) {
  const styles = {
    green: 'bg-emerald-50 text-emerald-700',
    red: 'bg-red-50 text-red-700',
    amber: 'bg-amber-50 text-amber-700',
  }
  return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${styles[tone]}`}>{children}</span>
}
