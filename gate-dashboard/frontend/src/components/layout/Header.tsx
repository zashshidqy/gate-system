import { cn } from '../../utils/helpers'
import { Signal, WifiOff } from 'lucide-react'
import { useGates } from '../../context/GateContext'
import { useAuth } from '../../context/AuthContext'

export function Header() {
  const { entryStatus, exitStatus, connectionQuality } = useGates()
  const { user, logout } = useAuth()

  const signalTheme = () => {
    switch (connectionQuality) {
      case 'excellent':
        return { fill: 'bg-nb-green', label: 'Sangat Baik' }
      case 'good':
        return { fill: 'bg-nb-yellow', label: 'Baik' }
      case 'poor':
        return { fill: 'bg-nb-orange', label: 'Buruk' }
      default:
        return { fill: 'bg-nb-red', label: 'Terputus' }
    }
  }

  const theme = signalTheme()

  return (
    <header className="sticky top-0 z-30 flex h-20 items-center gap-3 border-b-2 border-ink bg-background px-4 sm:gap-4 sm:px-6">
      {/* Spacer for mobile menu button (button is in Sidebar component) */}
      <div className="w-10 lg:hidden" />

      <div className="flex-1" />

      {/* Gate status chips */}
      <div className="flex items-center gap-2">
        <StatusChip label="ENTRY" connected={entryStatus.connected} />
        <StatusChip label="EXIT" connected={exitStatus.connected} />
      </div>

      {/* Connection quality */}
      <div
        className={cn(
          'hidden items-center gap-2 rounded-md border-2 border-ink px-3 py-2 shadow-nb-sm sm:flex',
          theme.fill
        )}
        title={`Kualitas koneksi: ${theme.label}`}
      >
        <Signal className="h-4 w-4 text-ink" strokeWidth={3} aria-hidden="true" />
        <span className="text-xs font-extrabold uppercase tracking-wide text-ink">{theme.label}</span>
      </div>

      {/* User */}
      <div className="flex items-center gap-2">
        <div
          className="flex h-10 w-10 shrink-0 cursor-pointer items-center justify-center rounded-md border-2 border-ink bg-nb-purple text-ink shadow-nb-sm transition-transform hover:-translate-y-0.5"
          title={user?.full_name || user?.username}
          role="button"
          aria-label={`Profil: ${user?.full_name || user?.username || 'Pengguna'}`}
        >
          <span className="text-sm font-extrabold">
            {(user?.full_name || user?.username || 'U').charAt(0).toUpperCase()}
          </span>
        </div>
        <button
          onClick={logout}
          className="nb-press hidden rounded-md border-2 border-ink bg-nb-red px-3 py-2 text-xs font-extrabold uppercase tracking-wide text-ink shadow-nb-sm sm:inline-block"
          aria-label="Keluar"
        >
          Keluar
        </button>
      </div>

      {connectionQuality === 'offline' && (
        <WifiOff className="h-5 w-5 text-destructive sm:hidden" strokeWidth={3} aria-hidden="true" />
      )}
    </header>
  )
}

function StatusChip({ label, connected }: { label: string; connected: boolean }) {
  return (
    <div
      className={cn(
        'flex items-center gap-2 rounded-md border-2 border-ink px-2.5 py-2 shadow-nb-sm',
        connected ? 'bg-nb-green' : 'bg-nb-red'
      )}
      title={connected ? `${label}: terhubung` : `${label}: terputus`}
    >
      <span className="text-[10px] font-extrabold uppercase tracking-wide text-ink">{label}</span>
      <span
        className={cn(
          'h-2.5 w-2.5 rounded-sm border-2 border-ink',
          connected ? 'bg-ink' : 'bg-background'
        )}
      />
    </div>
  )
}
