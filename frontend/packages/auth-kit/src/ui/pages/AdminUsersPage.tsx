import { useState } from 'react'

import { errorMessage } from '../../client/errors'
import type { AdminUser } from '../../client/types'
import { useAuth } from '../../react/context'
import { useAdminRoles, useAdminUsers, useDebounced, useUpdateUser } from '../../react/hooks'
import { Alert, Avatar, Badge, Button, Spinner } from '../components'
import { Icon } from '../icons'
import { useMessages } from '../context'

const PAGE_SIZE = 20

export function AdminUsersPage() {
  const { user: me } = useAuth()
  const m = useMessages().admin
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)
  const debouncedSearch = useDebounced(search.trim())
  const { users, total, pageCount } = useAdminUsers({ search: debouncedSearch, page, pageSize: PAGE_SIZE })
  const roles = useAdminRoles()

  return (
    <div className="ak-scope ak-page ak-page--wide">
      <div className="ak-page-header">
        <div>
          <h1 className="ak-page-title">{m.title}</h1>
          <p className="ak-item-meta">{m.count(total)}</p>
        </div>
        <div className="ak-input-wrap ak-search">
          <span className="ak-input-icon">
            <Icon name="search" size={17} />
          </span>
          <input
            type="search"
            className="ak-input ak-input--icon"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value)
              setPage(0)
            }}
            placeholder={m.search}
            aria-label={m.search}
          />
        </div>
      </div>

      {users.isError && (
        <div style={{ marginBottom: 16 }}>
          <Alert>{errorMessage(users.error)}</Alert>
        </div>
      )}

      <div className="ak-table-wrap">
        <table className="ak-table">
          <thead>
            <tr>
              <th>{m.columns.user}</th>
              <th>{m.columns.email}</th>
              <th>{m.columns.role}</th>
              <th>{m.columns.status}</th>
              <th className="ak-right">{m.columns.action}</th>
            </tr>
          </thead>
          <tbody>
            {users.isPending && (
              <tr>
                <td colSpan={5} className="ak-empty">
                  <Spinner large />
                </td>
              </tr>
            )}
            {users.data?.items.map((user) => (
              <UserRow key={user.id} user={user} roles={roles.data?.map((r) => r.name) ?? [user.role]} isMe={user.id === me?.id} />
            ))}
            {users.data && users.data.items.length === 0 && (
              <tr>
                <td colSpan={5} className="ak-empty">
                  {m.empty}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="ak-pagination">
        <span>{m.page(page + 1, pageCount)}</span>
        <div className="ak-row">
          <Button variant="secondary" size="sm" icon="chevronLeft" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
            {m.previous}
          </Button>
          <Button variant="secondary" size="sm" disabled={page + 1 >= pageCount} onClick={() => setPage((p) => p + 1)}>
            {m.next}
            <Icon name="chevronRight" size={15} />
          </Button>
        </div>
      </div>
    </div>
  )
}

function UserRow({ user, roles, isMe }: { user: AdminUser; roles: string[]; isMe: boolean }) {
  const m = useMessages().admin
  const mutation = useUpdateUser(user.id)

  return (
    <tr data-disabled={user.disabled || undefined}>
      <td>
        <div className="ak-row">
          <Avatar name={user.full_name || user.username} small />
          <div style={{ minWidth: 0 }}>
            <div className="ak-item-title">{user.username}</div>
            {user.full_name && <div className="ak-item-meta">{user.full_name}</div>}
            {mutation.isError && <div className="ak-error">{errorMessage(mutation.error)}</div>}
          </div>
        </div>
      </td>
      <td>{user.email}</td>
      <td>
        <select
          className="ak-select"
          value={user.role}
          disabled={isMe || mutation.isPending}
          onChange={(event) => mutation.mutate({ role: event.target.value })}
          aria-label={m.roleOf(user.username)}
        >
          {roles.map((role) => (
            <option key={role} value={role}>
              {role}
            </option>
          ))}
        </select>
      </td>
      <td>
        <span className="ak-row" style={{ gap: 6, flexWrap: 'wrap' }}>
          <Badge tone={user.disabled ? 'red' : 'green'}>{user.disabled ? m.disabled : m.active}</Badge>
          {!user.is_verified && <Badge tone="amber">{m.unverified}</Badge>}
        </span>
      </td>
      <td className="ak-right">
        {isMe ? (
          <Badge tone="indigo" plain>
            {m.you}
          </Badge>
        ) : (
          <Button
            size="sm"
            variant={user.disabled ? 'secondary' : 'danger-soft'}
            loading={mutation.isPending}
            onClick={() => mutation.mutate({ disabled: !user.disabled })}
          >
            {user.disabled ? m.enable : m.disable}
          </Button>
        )}
      </td>
    </tr>
  )
}
