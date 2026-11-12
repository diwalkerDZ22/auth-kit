import { AuthCard } from '../components'
import { useMessages } from '../context'

export function AccessDenied() {
  const m = useMessages().admin
  return <AuthCard title={m.deniedTitle} subtitle={m.deniedText} icon="lock" tone="danger" />
}
