import { Icon } from './icons'
import type { IconName } from './icons'
import { useMessages } from './context'
import { useTheme } from './theme'
import type { ThemePreference } from './theme'

const OPTIONS: { value: ThemePreference; icon: IconName }[] = [
  { value: 'light', icon: 'sun' },
  { value: 'system', icon: 'monitor' },
  { value: 'dark', icon: 'moon' },
]

/** Sélecteur clair / système / sombre. */
export function ThemeToggle() {
  const { preference: current, setPreference } = useTheme()
  const m = useMessages().theme
  return (
    <div className="ak-theme-toggle" role="group" aria-label={m.label}>
      {OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          aria-pressed={current === option.value}
          title={m[option.value]}
          onClick={() => setPreference(option.value)}
        >
          <Icon name={option.icon} size={15} />
          <span className="ak-sr-only">{m[option.value]}</span>
        </button>
      ))}
    </div>
  )
}
