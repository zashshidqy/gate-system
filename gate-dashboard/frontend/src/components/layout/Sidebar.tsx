import { NavLink } from 'react-router-dom'
import { cn } from '../../utils/helpers'
import {
  LayoutDashboard,
  Ticket,
  CreditCard,
  History,
  Settings,
  LogOut,
  X,
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { useState, useEffect } from 'react'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard, accent: 'bg-nb-yellow' },
  { name: 'Tiket', href: '/tickets', icon: Ticket, accent: 'bg-nb-pink' },
  { name: 'Kartu RFID', href: '/rfid', icon: CreditCard, accent: 'bg-nb-purple' },
  { name: 'Riwayat', href: '/passages', icon: History, accent: 'bg-nb-cyan' },
  { name: 'Pengaturan', href: '/settings', icon: Settings, accent: 'bg-nb-orange' },
]

export function Sidebar() {
  const { user, logout } = useAuth()
  const [isOpen, setIsOpen] = useState(false)

  // Close sidebar on route change
  useEffect(() => {
    const handleRouteChange = () => setIsOpen(false)
    window.addEventListener('popstate', handleRouteChange)
    return () => window.removeEventListener('popstate', handleRouteChange)
  }, [])

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-30 bg-ink/70 lg:hidden"
          onClick={() => setIsOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar — solid ink block with a hard edge */}
      <aside
        className={cn(
          'fixed left-0 top-0 z-40 h-screen w-64 border-r-2 border-ink bg-ink transition-transform duration-200 lg:translate-x-0',
          isOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex h-full flex-col">
          {/* Logo block */}
          <div className="flex h-20 items-center gap-3 border-b-2 border-background/20 px-5">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md border-2 border-background bg-nb-yellow text-ink shadow-[3px_3px_0_0_hsl(var(--background))]">
              <svg className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth={3} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <div className="leading-none">
              <h1 className="text-xl font-extrabold uppercase tracking-tight text-background">
                Gate
              </h1>
              <p className="mt-1 text-[10px] font-bold uppercase tracking-[0.18em] text-background/60">
                Dashboard
              </p>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="ml-auto rounded-md border-2 border-background/40 p-1.5 text-background transition-colors hover:bg-background/10 lg:hidden"
              aria-label="Tutup menu"
            >
              <X className="h-4 w-4" strokeWidth={3} />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 space-y-3 overflow-y-auto p-4" aria-label="Navigasi utama">
            {navigation.map((item) => (
              <NavLink
                key={item.name}
                to={item.href}
                className={({ isActive }) =>
                  cn(
                    'nb-press group flex items-center gap-3 rounded-md border-2 px-3 py-3 text-sm font-extrabold uppercase tracking-wide',
                    isActive
                      ? // Active: solid accent slab that sits proud of the ink bar
                        'border-ink bg-nb-yellow text-ink shadow-[4px_4px_0_0_hsl(var(--background))]'
                      : 'border-background/25 bg-transparent text-background hover:border-background hover:bg-background/10'
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <span
                      className={cn(
                        'flex h-8 w-8 shrink-0 items-center justify-center rounded border-2 transition-colors',
                        isActive
                          ? 'border-ink bg-ink text-nb-yellow'
                          : 'border-background/40 text-background group-hover:border-background group-hover:bg-nb-yellow group-hover:text-ink'
                      )}
                    >
                      <item.icon className="h-4 w-4" strokeWidth={2.5} aria-hidden="true" />
                    </span>
                    <span>{item.name}</span>
                  </>
                )}
              </NavLink>
            ))}
          </nav>

          {/* User block */}
          <div className="space-y-3 border-t-2 border-background/20 p-4">
            <div className="flex items-center gap-3 rounded-md border-2 border-background/25 p-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded border-2 border-ink bg-nb-cyan text-ink shadow-[2px_2px_0_0_hsl(var(--background))]">
                <span className="text-sm font-extrabold">
                  {(user?.full_name || user?.username || 'U').charAt(0).toUpperCase()}
                </span>
              </div>
              <div className="min-w-0 flex-1 leading-tight">
                <p className="truncate text-sm font-extrabold text-background">
                  {user?.full_name || user?.username}
                </p>
                <p className="mt-0.5 truncate text-[10px] font-bold uppercase tracking-[0.12em] text-nb-green">
                  {user?.role}
                </p>
              </div>
            </div>

            <button
              onClick={() => {
                logout()
                setIsOpen(false)
              }}
              className="nb-press flex w-full items-center gap-3 rounded-md border-2 border-background bg-nb-red px-3 py-3 text-sm font-extrabold uppercase tracking-wide text-ink shadow-[4px_4px_0_0_hsl(var(--background))]"
            >
              <LogOut className="h-5 w-5 shrink-0" strokeWidth={3} />
              Keluar
            </button>
          </div>
        </div>
      </aside>
    </>
  )
}
