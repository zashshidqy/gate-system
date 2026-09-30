import { lazy, Suspense, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { cn } from '../utils/helpers'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Skeleton } from '../components/ui/skeleton'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../components/ui/table'
import { StatCard, Meter } from '../components/ui/stat-card'
import { useGates } from '../context/GateContext'
import { useAuth } from '../context/AuthContext'
import {
  nb,
  badge,
  getMethodAccent,
  getMethodBadge,
  getMethodLabel,
  getTicketAccent,
  getTicketLabel,
} from '../styles/tokens'
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle,
  Clock,
  CreditCard,
  Hourglass,
  Layers,
  Lock,
  RefreshCw,
  Route,
  Signal,
  Ticket,
  Truck,
  Unlock,
  WifiOff,
  XCircle,
  Zap,
  LogIn,
  LogOut,
} from 'lucide-react'

/**
 * Charting deps are heavy; split them out so the other routes stay light.
 */
const TrafficChart = lazy(() => import('../components/dashboard/TrafficChart'))

/* -------------------------------------------------------------------------- */
/*  Types                                                                     */
/* -------------------------------------------------------------------------- */

interface DashboardStats {
  period_hours: number
  passages: {
    total: number
    allowed: number
    denied: number
    by_direction: Record<string, number>
    by_method: Record<string, number>
    hourly: { hour: string; count: number }[]
  }
  tickets: {
    active: number
    by_type: Record<string, number>
  }
  rfid: {
    active_cards: number
  }
  recent_passages: {
    id: number
    ts: string
    direction: string
    method: string
    uid: string | null
    plate: string | null
    allowed: boolean
  }[]
}

interface ExpiringTicket {
  id: string
  code: string
  type: string
  valid_until: string
  used_count: number
  max_uses: number
}

/* -------------------------------------------------------------------------- */
/*  Constants                                                                 */
/* -------------------------------------------------------------------------- */

const PERIODS = [
  { label: '24 Jam', short: '24j', hours: 24 },
  { label: '3 Hari', short: '3h', hours: 72 },
  { label: '7 Hari', short: '7h', hours: 168 },
] as const

interface AccentRow {
  icon: typeof CreditCard
  fill: string
  label: string
}

/** Per-method icon, with the label/accent coming from the shared tokens. */
const METHOD_ICON: Record<string, typeof CreditCard> = {
  RFID: CreditCard,
  ANPR: Route,
  QR: Layers,
  MANUAL: Zap,
}

/* -------------------------------------------------------------------------- */
/*  Helpers                                                                   */
/* -------------------------------------------------------------------------- */

function greeting(): string {
  const h = new Date().getHours()
  if (h < 11) return 'Selamat pagi'
  if (h < 15) return 'Selamat siang'
  if (h < 18) return 'Selamat sore'
  return 'Selamat malam'
}

/** "2026-09-30 14:00" -> "14:00" (or "30/09 14:00" for multi-day ranges). */
function formatHourLabel(raw: string, spanHours: number): string {
  if (!raw) return '—'
  const [day = '', hour = ''] = raw.split(' ')
  // Backend always returns "%Y-%m-%d %H:00"; fall back to the raw label if not.
  if (!hour) return day
  if (spanHours <= 24) return hour
  return day.length === 10 ? `${day.slice(8, 10)}/${day.slice(5, 7)} ${hour}` : hour
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Baru saja'
  if (mins < 60) return `${mins} mnt lalu`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours} jam lalu`
  return `${Math.floor(hours / 24)} hari lalu`
}

function clockTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })
}

function daysLeft(iso: string): number {
  return Math.ceil((new Date(iso).getTime() - Date.now()) / 86_400_000)
}

function sumOf(record: Record<string, number>): number {
  return Object.values(record).reduce((a, b) => a + b, 0)
}

/** Clamp percentage so a zero-total group never produces NaN widths. */
function pct(value: number, total: number): number {
  if (total <= 0) return 0
  return Math.min(100, Math.max(0, (value / total) * 100))
}

/* -------------------------------------------------------------------------- */
/*  Page                                                                      */
/* -------------------------------------------------------------------------- */

export function Dashboard() {
  const { entryStatus, exitStatus, sendCommand, isConnected, connectionQuality } = useGates()
  const { user } = useAuth()
  const [hours, setHours] = useState<number>(24)
  const [loadingCommand, setLoadingCommand] = useState<string | null>(null)
  const [syncedAt, setSyncedAt] = useState<Date | null>(null)

  const { data: stats, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['dashboard-stats', hours],
    queryFn: async () => {
      const response = await api.get<DashboardStats>(`/dashboard/overview?hours=${hours}`)
      return response.data
    },
    refetchInterval: 30_000,
  })

  const { data: expiringTickets } = useQuery({
    queryKey: ['dashboard-expiring'],
    queryFn: async () => {
      const response = await api.get<ExpiringTicket[]>('/dashboard/tickets/expiring?days=7')
      return response.data
    },
    refetchInterval: 120_000,
  })

  const handleCommand = async (unit: 'ENTRY' | 'EXIT', command: string) => {
    setLoadingCommand(`${unit}-${command}`)
    try {
      await sendCommand(unit, command)
    } finally {
      setLoadingCommand(null)
    }
  }

  const handleRefresh = async () => {
    await refetch()
    setSyncedAt(new Date())
  }

  const derived = useMemo(() => {
    const total = stats?.passages.total ?? 0
    const allowed = stats?.passages.allowed ?? 0
    const denied = stats?.passages.denied ?? 0
    const periodHours = stats?.period_hours ?? hours
    const avgPerHour = periodHours > 0 ? total / periodHours : 0
    const denialRate = total > 0 ? Math.round((denied / total) * 100) : 0
    const successRate = total > 0 ? Math.round((allowed / total) * 100) : 0

    const peak = (stats?.passages.hourly ?? []).reduce(
      (best, cur) => (cur.count > best.count ? cur : best),
      { hour: '', count: 0 },
    )

    const methodRows: (AccentRow & { method: string; count: number })[] = Object.entries(
      stats?.passages.by_method ?? {},
    )
      .map(([method, count]) => ({
        method,
        count,
        icon: METHOD_ICON[method] ?? Layers,
        fill: nb[getMethodAccent(method)],
        label: getMethodLabel(method),
      }))
      .sort((a, b) => b.count - a.count)

    const ticketRows = Object.entries(stats?.tickets.by_type ?? {})
      .map(([type, count]) => ({
        type,
        count,
        label: getTicketLabel(type),
        fill: nb[getTicketAccent(type)],
      }))
      .sort((a, b) => b.count - a.count)

    const directionRows = Object.entries(stats?.passages.by_direction ?? {})
      .map(([direction, count]) => ({ direction, count }))
      .sort((a, b) => b.count - a.count)

    const chartData = (stats?.passages.hourly ?? []).map((h) => ({
      label: formatHourLabel(h.hour, periodHours),
      count: h.count,
    }))

    return {
      total,
      allowed,
      denied,
      avgPerHour,
      denialRate,
      successRate,
      peakLabel: peak.count > 0 ? formatHourLabel(peak.hour, periodHours) : '—',
      peakCount: peak.count,
      methodRows,
      ticketRows,
      directionRows,
      directionTotal: sumOf(stats?.passages.by_direction ?? {}),
      chartData,
      ticketTotal: sumOf(stats?.tickets.by_type ?? {}),
    }
  }, [stats, hours])

  const lastUpdated = syncedAt ?? null
  const activePeriodLabel = PERIODS.find((p) => p.hours === hours)?.label.toLowerCase()

  return (
    <div className="space-y-6">
      {/* ============================ Page header ============================ */}
      <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-4xl font-extrabold uppercase leading-none tracking-tight sm:text-5xl">
            Dashboard
          </h1>
          <p className="mt-3 flex flex-wrap items-center gap-2 text-sm font-semibold text-muted-foreground">
            <span>
              {greeting()}
              {user?.full_name ? `, ${user.full_name.split(' ')[0]}` : ''}
            </span>
            {lastUpdated && (
              <span className="rounded border-2 border-ink bg-muted px-2 py-0.5 text-xs uppercase text-foreground">
                Update {clockTime(lastUpdated.toISOString())}
              </span>
            )}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Live status */}
          <div
            className={cn(
              'flex items-center gap-2 rounded-md border-2 border-ink px-3.5 py-2.5 shadow-nb-sm',
              isConnected ? nb.green : nb.red,
            )}
          >
            <span className="h-3 w-3 rounded-sm border-2 border-ink bg-ink" />
            <span className="text-sm font-extrabold uppercase tracking-wide text-ink">
              {isConnected ? 'Live' : 'Terputus'}
            </span>
            {isConnected && (
              <span className="hidden text-xs font-bold uppercase text-ink/70 sm:inline">
                {connectionQuality === 'excellent'
                  ? 'Sinyal bagus'
                  : connectionQuality === 'good'
                    ? 'Sinyal baik'
                    : 'Sinyal lemah'}
              </span>
            )}
          </div>

          {/* Period selector */}
          <div
            role="tablist"
            aria-label="Periode laporan"
            className="inline-flex flex-wrap gap-2"
          >
            {PERIODS.map((p) => (
              <button
                key={p.hours}
                role="tab"
                aria-selected={hours === p.hours}
                onClick={() => setHours(p.hours)}
                className={cn(
                  'nb-press rounded-md border-2 border-ink px-3.5 py-2 text-sm font-extrabold uppercase tracking-wide',
                  hours === p.hours
                    ? 'bg-nb-yellow text-ink shadow-nb'
                    : 'bg-card text-foreground hover:bg-muted',
                )}
              >
                <span className="hidden sm:inline">{p.label}</span>
                <span className="sm:hidden">{p.short}</span>
              </button>
            ))}
          </div>

          <Button variant="outline" onClick={handleRefresh} disabled={isFetching} className="gap-2">
            <RefreshCw className={cn('h-4 w-4', isFetching && 'animate-spin')} strokeWidth={3} />
            <span className="hidden sm:inline">Muat</span>
          </Button>
        </div>
      </div>

      {/* ========================== Offline banner ========================== */}
      {!isConnected && (
        <div
          role="alert"
          className="nb-stripes flex items-start gap-4 rounded-lg border-2 border-ink bg-nb-orange p-4 shadow-nb"
        >
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md border-2 border-ink bg-card">
            <WifiOff className="h-5 w-5" strokeWidth={3} aria-hidden="true" />
          </div>
          <div>
            <h3 className="nb-label">Koneksi kontrol terputus</h3>
            <p className="mt-1 text-sm font-semibold">
              Perintah buka/tutup gerbang tidak dapat dikirim. Sistem mencoba menyambung ulang
              otomatis.
            </p>
          </div>
        </div>
      )}

      {/* ============================== KPI row ============================== */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-6">
        <StatCard
          label="Total Pelintas"
          value={stats?.passages.total}
          loading={isLoading}
          hint={`${derived.avgPerHour.toFixed(1)}/jam`}
          icon={Activity}
          fill={nb.yellow}
        />
        <StatCard
          label="Diizinkan"
          value={stats?.passages.allowed}
          loading={isLoading}
          hint={`${derived.successRate}% dari total`}
          icon={CheckCircle}
          fill={nb.green}
          meter={derived.successRate}
          meterFill="bg-nb-green"
        />
        <StatCard
          label="Ditolak"
          value={stats?.passages.denied}
          loading={isLoading}
          hint={`${derived.denialRate}% dari total`}
          icon={XCircle}
          fill={nb.red}
          meter={derived.denialRate}
          meterFill="bg-nb-red"
        />
        <StatCard
          label="Jam Tersibuk"
          value={derived.peakLabel}
          loading={isLoading}
          isText
          hint={`${derived.peakCount} pelintas`}
          icon={Clock}
          fill={nb.cyan}
        />
        <StatCard
          label="Tiket Aktif"
          value={stats?.tickets.active}
          loading={isLoading}
          hint={`${derived.ticketTotal} terbit`}
          icon={Ticket}
          fill={nb.pink}
        />
        <StatCard
          label="Kartu RFID"
          value={stats?.rfid.active_cards}
          loading={isLoading}
          hint="Terotorisasi"
          icon={CreditCard}
          fill={nb.purple}
        />
      </div>

      {/* ==================== Traffic chart + method breakdown ==================== */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Card className="flex flex-col overflow-hidden xl:col-span-2">
          <CardHeader className="flex-row items-start justify-between gap-4 border-b-2 border-ink bg-nb-yellow pb-4">
            <div>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-6 w-6" strokeWidth={3} aria-hidden="true" />
                Arus Pelintas
              </CardTitle>
              <CardDescription className="mt-1 text-ink/70">
                Periode {activePeriodLabel} · puncak{' '}
                <span className="font-extrabold text-ink">{derived.peakLabel}</span> (
                {derived.peakCount} pelintas)
              </CardDescription>
            </div>
            <span className="hidden rounded-md border-2 border-ink bg-card px-2.5 py-1 text-xs font-extrabold uppercase text-ink sm:inline-block">
              Per jam
            </span>
          </CardHeader>
          <CardContent className="flex min-h-0 flex-1 flex-col pt-6">
            {isLoading ? (
              <Skeleton className="h-72 w-full" />
            ) : derived.chartData.length === 0 ? (
              <EmptyState
                icon={AlertTriangle}
                title="Belum ada data arus"
                message={`Tidak ada pelintas tercatat dalam ${activePeriodLabel}.`}
              />
            ) : (
              <Suspense fallback={<Skeleton className="h-72 w-full" />}>
                <div className="flex min-h-0 flex-1 flex-col">
                  <TrafficChart data={derived.chartData} className="h-full min-h-72" />
                </div>
              </Suspense>
            )}
          </CardContent>
        </Card>

        {/* Access methods */}
        <Card className="overflow-hidden">
          <CardHeader className="border-b-2 border-ink bg-nb-orange pb-4">
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-6 w-6" strokeWidth={3} aria-hidden="true" />
              Metode Akses
            </CardTitle>
            <CardDescription className="mt-1 text-ink/70">Persentase verifikasi</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-6">
            {isLoading ? (
              <div className="space-y-4">
                {[...Array(4)].map((_, i) => (
                  <Skeleton key={i} className="h-14 w-full" />
                ))}
              </div>
            ) : derived.methodRows.length === 0 ? (
              <EmptyState icon={Zap} title="Belum ada data" message="Tidak ada metode akses tercatat." compact />
            ) : (
              derived.methodRows.map((row) => {
                const Icon = row.icon
                const share = pct(row.count, derived.total)
                return (
                  <div key={row.method} className="rounded-md border-2 border-ink bg-card p-3">
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2.5">
                        <span
                          className={cn(
                            'flex h-9 w-9 shrink-0 items-center justify-center rounded border-2 border-ink text-ink',
                            row.fill,
                          )}
                        >
                          <Icon className="h-4 w-4" strokeWidth={3} aria-hidden="true" />
                        </span>
                        <p className="text-sm font-extrabold uppercase leading-none">
                          {row.label}
                        </p>
                      </div>
                      <div className="text-right leading-none">
                        <p className="text-lg font-extrabold tabular-nums">{row.count}</p>
                        <p className="mt-1 text-xs font-bold uppercase text-muted-foreground">
                          {share.toFixed(0)}%
                        </p>
                      </div>
                    </div>
                    <Meter value={share} fillClass={row.fill.split(' ')[0]} />
                  </div>
                )
              })
            )}
          </CardContent>
        </Card>
      </div>

      {/* ================ Gate control + direction + ticket types ================ */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <GateStatusCard
          title="Gerbang ENTRY"
          subtitle="Akses masuk area"
          status={entryStatus}
          onOpen={() => handleCommand('ENTRY', 'O')}
          onClose={() => handleCommand('ENTRY', 'C')}
          loading={loadingCommand?.startsWith('ENTRY') ?? false}
        />
        <GateStatusCard
          title="Gerbang EXIT"
          subtitle="Akses keluar area"
          status={exitStatus}
          onOpen={() => handleCommand('EXIT', 'O')}
          onClose={() => handleCommand('EXIT', 'C')}
          loading={loadingCommand?.startsWith('EXIT') ?? false}
        />

        {/* auto-rows-fr makes the two stacked cards split this column's full
            height instead of leaving dead space under the shorter one. */}
        <div className="grid auto-rows-fr grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-1">
          {/* Direction */}
          <Card className="flex flex-col overflow-hidden">
            <CardHeader className="border-b-2 border-ink bg-nb-blue pb-4">
              <CardTitle className="flex items-center gap-2">
                <Truck className="h-6 w-6" strokeWidth={3} aria-hidden="true" />
                Arah Pelintas
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-1 flex-col gap-4 pt-6">
              {isLoading ? (
                <Skeleton className="h-24 w-full" />
              ) : derived.directionRows.length === 0 ? (
                <EmptyState icon={Truck} title="Belum ada data" message="Belum ada lalu lintas." compact />
              ) : (
                derived.directionRows.map((row) => {
                  const isEntry = row.direction === 'ENTRY'
                  const share = pct(row.count, derived.directionTotal)
                  return (
                    /* `flex-1` + `items-center`: only two directions exist, so
                       the rows grow to fill the card instead of leaving a
                       ragged gap underneath. */
                    <div
                      key={row.direction}
                      className="flex flex-1 items-center rounded-md border-2 border-ink bg-card p-3"
                    >
                      <div className="flex w-full items-center gap-3">
                        <span
                          className={cn(
                            'flex h-9 w-9 shrink-0 items-center justify-center rounded border-2 border-ink text-ink',
                            isEntry ? nb.blue : nb.green,
                          )}
                        >
                          {isEntry ? (
                            <LogIn className="h-4 w-4" strokeWidth={3} aria-hidden="true" />
                          ) : (
                            <LogOut className="h-4 w-4" strokeWidth={3} aria-hidden="true" />
                          )}
                        </span>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-sm font-extrabold uppercase">{row.direction}</span>
                            <span className="text-sm font-extrabold tabular-nums">
                              {row.count}{' '}
                              <span className="text-xs text-muted-foreground">
                                ({share.toFixed(0)}%)
                              </span>
                            </span>
                          </div>
                          <Meter
                            value={share}
                            fillClass={isEntry ? 'bg-nb-blue' : 'bg-nb-green'}
                          />
                        </div>
                      </div>
                    </div>
                  )
                })
              )}
            </CardContent>
          </Card>

          {/* Ticket types */}
          <Card className="flex flex-col overflow-hidden">
            <CardHeader className="border-b-2 border-ink bg-nb-pink pb-4">
              <CardTitle className="flex items-center gap-2">
                <Ticket className="h-6 w-6" strokeWidth={3} aria-hidden="true" />
                Tiket / Jenis
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 space-y-3 pt-6">
              {isLoading ? (
                <Skeleton className="h-24 w-full" />
              ) : derived.ticketRows.length === 0 ? (
                <EmptyState icon={Ticket} title="Belum ada tiket" message="Belum ada tiket terbit." compact />
              ) : (
                derived.ticketRows.map((row) => {
                  const share = pct(row.count, derived.ticketTotal)
                  return (
                    <div key={row.type} className="rounded-md border-2 border-ink bg-card p-3">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-extrabold uppercase">{row.label}</span>
                        <span className="text-sm font-extrabold tabular-nums">
                          {row.count}{' '}
                          <span className="text-xs text-muted-foreground">
                            ({share.toFixed(0)}%)
                          </span>
                        </span>
                      </div>
                      <Meter value={share} fillClass={row.fill.split(' ')[0]} />
                    </div>
                  )
                })
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* ============== Expiring tickets + recent passages table ============== */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        {/* Expiring soon */}
        <Card className="flex flex-col overflow-hidden">
          <CardHeader className="border-b-2 border-ink bg-nb-yellow pb-4">
            <CardTitle className="flex items-center gap-2">
              <Hourglass className="h-6 w-6" strokeWidth={3} aria-hidden="true" />
              Segera Kedaluwarsa
            </CardTitle>
            <CardDescription className="mt-1 text-ink/70">Dalam 7 hari ke depan</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col pt-6">
            {!expiringTickets || expiringTickets.length === 0 ? (
              <EmptyState
                icon={CheckCircle}
                title="Semua aman"
                message="Tidak ada tiket yang akan kedaluwarsa dalam 7 hari."
                compact
                fill={nb.green}
              />
            ) : (
              /* flex-1 on each row makes the list grow to fill the card, so a
                 short list does not leave a slab of dead space at the bottom. */
              <ul className="flex flex-1 flex-col gap-2.5">
                {expiringTickets.slice(0, 6).map((t) => {
                  const left = daysLeft(t.valid_until)
                  return (
                    <li
                      key={t.id}
                      className="flex flex-1 items-center gap-3 rounded-md border-2 border-ink bg-card p-2.5"
                    >
                      <span
                        className={cn(
                          'flex h-9 w-9 shrink-0 items-center justify-center rounded border-2 border-ink text-ink',
                          left <= 1 ? nb.red : nb.yellow,
                        )}
                      >
                        <Hourglass className="h-4 w-4" strokeWidth={3} aria-hidden="true" />
                      </span>
                      <div className="min-w-0 flex-1 leading-tight">
                        <p className="truncate font-mono text-sm font-extrabold">{t.code}</p>
                        <p className="mt-1 text-[11px] font-semibold text-muted-foreground">
                          {getTicketLabel(t.type)} · {t.used_count}/{t.max_uses}
                        </p>
                      </div>
                      <Badge
                        className={cn('shrink-0', left <= 1 ? nb.red : nb.orange)}
                      >
                        {left <= 0 ? 'Hari ini' : `${left} hari`}
                      </Badge>
                    </li>
                  )
                })}
                {expiringTickets.length > 6 && (
                  <li className="shrink-0 pt-1 text-center text-xs font-extrabold uppercase text-muted-foreground">
                    +{expiringTickets.length - 6} tiket lainnya
                  </li>
                )}
              </ul>
            )}
          </CardContent>
        </Card>

        {/* Recent passages */}
        <Card className="flex flex-col overflow-hidden xl:col-span-2">
          <CardHeader className="flex-row items-center justify-between gap-4 border-b-2 border-ink bg-nb-cyan pb-4">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-6 w-6" strokeWidth={3} aria-hidden="true" />
                Aktivitas Terakhir
              </CardTitle>
              <CardDescription className="mt-1 text-ink/70">
                {stats?.recent_passages.length ?? 0} kejadian terbaru
              </CardDescription>
            </div>
            <Badge className={cn('shrink-0 gap-1', nb.green)}>
              <Signal className="h-3 w-3" strokeWidth={3} aria-hidden="true" />
              Real-time
            </Badge>
          </CardHeader>
          <CardContent className="p-0">
            {isLoading ? (
              <div className="space-y-3 p-6">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            ) : !stats || stats.recent_passages.length === 0 ? (
              <EmptyState
                icon={Activity}
                title="Belum ada aktivitas"
                message="Belum ada pelintas tercatat. Aktivitas muncul di sini otomatis."
              />
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Waktu</TableHead>
                      <TableHead>Gerbang</TableHead>
                      <TableHead>Metode</TableHead>
                      <TableHead>Identitas</TableHead>
                      <TableHead className="text-right">Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {stats.recent_passages.map((p) => (
                      <TableRow key={p.id}>
                        <TableCell className="whitespace-nowrap">
                          <div className="leading-tight">
                            <p className="font-mono text-sm font-extrabold">{clockTime(p.ts)}</p>
                            <p className="mt-1 text-[11px] font-semibold text-muted-foreground">
                              {timeAgo(p.ts)}
                            </p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge className={p.direction === 'ENTRY' ? badge.entry : badge.exit}>
                            {p.direction === 'ENTRY' ? (
                              <LogIn className="mr-1 h-3 w-3" strokeWidth={3} aria-hidden="true" />
                            ) : (
                              <LogOut className="mr-1 h-3 w-3" strokeWidth={3} aria-hidden="true" />
                            )}
                            {p.direction}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge className={getMethodBadge(p.method)}>{getMethodLabel(p.method)}</Badge>
                        </TableCell>
                        <TableCell className="max-w-[220px]">
                          <span className="block truncate font-mono text-sm font-bold">
                            {p.uid || p.plate || '—'}
                          </span>
                        </TableCell>
                        <TableCell className="text-right">
                          <Badge className={p.allowed ? badge.success : badge.danger}>
                            {p.allowed ? '✓ Diizinkan' : '✗ Ditolak'}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/*  Sub-components                                                            */
/* -------------------------------------------------------------------------- */

function GateStatusCard({
  title,
  subtitle,
  status,
  onOpen,
  onClose,
  loading,
}: {
  title: string
  subtitle: string
  status: { connected: boolean; status: any; last_update: string | null }
  onOpen: () => Promise<void>
  onClose: () => Promise<void>
  loading: boolean
}) {
  const state = status.status?.state || 'UNKNOWN'
  const vehicle = status.status?.vehicle
  const pos = status.status?.pos ?? 0
  const lcd1 = status.status?.lcd1 || ''
  const lcd2 = status.status?.lcd2 || ''
  const count = status.status?.count
  const lastUid = status.status?.last_uid
  const lastAuth = status.status?.last_auth
  const rfidVer = status.status?.rfid_ver
  const isOpen = state === 'OPEN'
  const isMoving = state === 'OPENING' || state === 'CLOSING'
  const tone = gateTone(state)

  return (
    <Card className="flex flex-col overflow-hidden">
      <CardHeader className={cn('border-b-2 border-ink pb-4', tone.fill)}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle>{title}</CardTitle>
            <CardDescription className="mt-1 text-ink/70">{subtitle}</CardDescription>
          </div>
          <span
            className={cn(
              'flex shrink-0 items-center gap-2 rounded border-2 border-ink px-2 py-1',
              status.connected ? nb.green : nb.red,
            )}
          >
            <span className="h-2.5 w-2.5 rounded-sm border-2 border-ink bg-ink" />
            <span className="text-[10px] font-extrabold uppercase tracking-wide text-ink">
              {status.connected ? 'On' : 'Off'}
            </span>
          </span>
        </div>
      </CardHeader>

      <CardContent className="flex flex-1 flex-col gap-4 pt-5">
        {/* State + position */}
        <div className="rounded-md border-2 border-ink bg-card p-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <span
                className={cn(
                  'flex h-12 w-12 shrink-0 items-center justify-center rounded border-2 border-ink text-ink',
                  tone.iconFill,
                )}
              >
                {isOpen ? (
                  <Unlock className="h-6 w-6" strokeWidth={3} aria-hidden="true" />
                ) : (
                  <Lock className="h-6 w-6" strokeWidth={3} aria-hidden="true" />
                )}
              </span>
              <div className="leading-none">
                <p className="nb-label text-muted-foreground">Status</p>
                <p className="mt-1.5 text-xl font-extrabold uppercase">{state}</p>
              </div>
            </div>
            {isMoving && <Badge className={nb.blue}>Bergerak</Badge>}
          </div>

          <div className="mt-4">
            <div className="flex items-center justify-between text-xs font-extrabold uppercase">
              <span className="text-muted-foreground">Posisi</span>
              <span className="tabular-nums">{pos}&deg;</span>
            </div>
            <Meter
              value={pct(pos, 90)}
              fillClass={isOpen ? 'bg-nb-green' : 'bg-nb-yellow'}
              className="mt-2"
            />
            <div className="mt-1.5 flex justify-between text-[10px] font-bold uppercase text-muted-foreground">
              <span>Tutup 0&deg;</span>
              <span>Buka 90&deg;</span>
            </div>
          </div>
        </div>

        {/* Vehicle */}
        <div
          className={cn(
            'flex items-center gap-2.5 rounded-md border-2 border-ink px-3 py-2.5',
            vehicle ? nb.orange : 'bg-muted',
          )}
        >
          <span className="h-3 w-3 shrink-0 rounded-sm border-2 border-ink bg-ink" />
          <span className="text-sm font-extrabold uppercase">
            {vehicle ? 'Kendaraan terdeteksi' : 'Tidak ada kendaraan'}
          </span>
        </div>

        {/* LCD */}
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-md border-2 border-ink bg-ink p-2.5">
            <p className="nb-label text-background/60">LCD 1</p>
            <p className="mt-1.5 truncate font-mono text-xs font-bold text-background" title={lcd1}>
              {lcd1 || '—'}
            </p>
          </div>
          <div className="rounded-md border-2 border-ink bg-ink p-2.5">
            <p className="nb-label text-background/60">LCD 2</p>
            <p className="mt-1.5 truncate font-mono text-xs font-bold text-background" title={lcd2}>
              {lcd2 || '—'}
            </p>
          </div>
        </div>

        {/* Device info */}
        <div className="grid grid-cols-3 gap-2 border-t-2 border-ink pt-4 text-center">
          <div className="rounded border-2 border-ink bg-muted py-2">
            <p className="nb-label text-muted-foreground">Total</p>
            <p className="mt-1 text-sm font-extrabold tabular-nums">{count ?? '—'}</p>
          </div>
          <div className="rounded border-2 border-ink bg-muted py-2">
            <p className="nb-label text-muted-foreground">UID</p>
            <p className="mt-1 truncate font-mono text-xs font-extrabold">{lastUid || '—'}</p>
          </div>
          <div className="rounded border-2 border-ink bg-muted py-2">
            <p className="nb-label text-muted-foreground">RFID</p>
            <p className="mt-1 truncate font-mono text-xs font-extrabold">{rfidVer || '—'}</p>
          </div>
        </div>

        {lastAuth && (
          <p className="text-center text-xs font-semibold text-muted-foreground">
            Otorisasi terakhir:{' '}
            <span className="font-mono font-extrabold text-foreground">{lastAuth}</span>
          </p>
        )}

        {/* Controls — mt-auto pins the pair to the card's bottom edge so both
            gate cards' buttons line up even when their status blocks differ. */}
        <div className="mt-auto flex gap-3 pt-1">
          <Button
            onClick={onOpen}
            disabled={!status.connected || isOpen || loading}
            className="flex-1 gap-2 bg-nb-green text-ink"
          >
            <Unlock className="h-4 w-4" strokeWidth={3} aria-hidden="true" />
            {loading ? 'Kirim' : 'Buka'}
          </Button>
          <Button
            variant="outline"
            onClick={onClose}
            disabled={!status.connected || !isOpen || loading}
            className="flex-1 gap-2"
          >
            <Lock className="h-4 w-4" strokeWidth={3} aria-hidden="true" />
            {loading ? 'Kirim' : 'Tutup'}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

function gateTone(state: string): { fill: string; iconFill: string } {
  switch (state) {
    case 'OPEN':
      return { fill: nb.green, iconFill: nb.green }
    case 'CLOSED':
      return { fill: nb.yellow, iconFill: nb.yellow }
    default:
      return { fill: nb.orange, iconFill: nb.orange }
  }
}

function EmptyState({
  icon: Icon,
  title,
  message,
  compact,
  fill,
}: {
  icon: typeof Activity
  title: string
  message: string
  compact?: boolean
  fill?: string
}) {
  return (
    <div className={cn('flex flex-col items-center justify-center text-center', compact ? 'py-6' : 'py-12')}>
      <span
        className={cn(
          'mb-4 flex items-center justify-center rounded-lg border-2 border-ink text-ink shadow-nb-sm',
          compact ? 'h-14 w-14' : 'h-16 w-16',
          fill ?? 'bg-muted',
        )}
      >
        <Icon className={compact ? 'h-7 w-7' : 'h-8 w-8'} strokeWidth={3} aria-hidden="true" />
      </span>
      <p className="text-sm font-extrabold uppercase">{title}</p>
      <p className="mt-2 max-w-xs text-xs font-semibold text-muted-foreground">{message}</p>
    </div>
  )
}
