import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { cn } from '../utils/helpers'
import { Card, CardContent } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../components/ui/table'
import {
  Plus,
  Search,
  QrCode,
  Trash2,
  Copy,
  Ticket,
  BadgeCheck,
  XCircle,
  Crown,
  TrendingUp,
  AlertCircle,
  Calendar,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { TicketToken, TicketType, PaginatedResponse } from '../types'
import QRCodeModal from '../components/ticket/QRCodeModal'
import TicketForm from '../components/ticket/TicketForm'
import { Skeleton } from '../components/ui/skeleton'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { StatCard } from '../components/ui/stat-card'
import { useDebounce } from '../hooks/useDebounce'
import { accents, badge, getTicketBadge, getTicketLabel, nbFill } from '../styles/tokens'
import { Pagination } from '../components/ui/pagination'
/* -------------------------------------------------------------------------- */
/*  Helpers                                                                    */
/* -------------------------------------------------------------------------- */
function getTicketTypeIcon(type: TicketType) {
  switch (type) {
    case 'SINGLE_ENTRY': return <Ticket className="h-3 w-3" />
    case 'MULTI_DAY': return <Calendar className="h-3 w-3" />
    case 'VIP': return <Crown className="h-3 w-3" />
    case 'STAFF': return <BadgeCheck className="h-3 w-3" />
    default: return <Ticket className="h-3 w-3" />
  }
}
/** Clamp a used/max ratio to 0-100 so the meter never overflows its track. */
function usagePercent(used: number, max: number): number {
  if (max <= 0) return 0
  return Math.min(100, Math.max(0, Math.round((used / max) * 100)))
}
/* -------------------------------------------------------------------------- */
/*  Page                                                                       */
/* -------------------------------------------------------------------------- */
export function Tickets() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [searchInput, setSearchInput] = useState('')
  const debouncedSearch = useDebounce(searchInput, 300)
  const [typeFilter, setTypeFilter] = useState<TicketType | ''>('')
  const [revokedFilter, setRevokedFilter] = useState<boolean | ''>('')
  const [showQRCode, setShowQRCode] = useState<string | null>(null)
  const [showForm, setShowForm] = useState<TicketToken | null | 'create'>(null)
  const [confirmRevoke, setConfirmRevoke] = useState<string | null>(null)
  const { data, isLoading } = useQuery({
    queryKey: ['tickets', page, debouncedSearch, typeFilter, revokedFilter],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '20',
      })
      if (debouncedSearch) params.append('search', debouncedSearch)
      if (typeFilter) params.append('type', typeFilter)
      if (revokedFilter !== '') params.append('revoked', revokedFilter.toString())
      const response = await api.get<PaginatedResponse<TicketToken>>(`/tickets?${params}`)
      return response.data
    },
  })
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/tickets/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tickets'] })
      toast.success('Tiket berhasil dicabut', { icon: '✓' })
    },
    onError: () => toast.error('Gagal mencabut tiket'),
  })
  const createMutation = useMutation({
    mutationFn: (data: any) => api.post('/tickets', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tickets'] })
      toast.success('Tiket berhasil dibuat', { icon: '✓' })
      setShowForm(null)
      setPage(1)
    },
    onError: () => toast.error('Gagal membuat tiket'),
  })
  const handleRevoke = (id: string) => {
    setConfirmRevoke(id)
  }
  const handleViewQR = (code: string) => {
    setShowQRCode(code)
  }
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast.success('Kode disalin ke papan klip', { icon: '📋' })
  }
  const activeCount = data?.items.filter(t => !t.revoked).length || 0
  const revokedCount = data?.items.filter(t => t.revoked).length || 0
  const totalUses = data?.items.reduce((sum, t) => sum + t.used_count, 0) || 0
  return (
    <div className="space-y-6">
      {/* ============================== Header ============================== */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-4xl font-extrabold uppercase tracking-tight sm:text-5xl">
            Token Tiket
          </h1>
          <p className="mt-2 text-sm font-semibold text-muted-foreground">
            Kelola token tiket masuk/keluar dengan kode QR
          </p>
        </div>
        <Button
          onClick={() => setShowForm('create')}
          className="gap-2 bg-nb-pink text-ink shadow-nb hover:shadow-nb-lg"
        >
          <Plus className="h-5 w-5" />
          Buat Tiket
        </Button>
      </div>
      {/* ============================ Stats summary ========================== */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Total Tiket"
          value={data?.total || 0}
          icon={Ticket}
          fill={nbFill[accents.ticket]}
        />
        <StatCard
          label="Aktif"
          value={activeCount}
          icon={BadgeCheck}
          fill={nbFill[accents.success]}
        />
        <StatCard
          label="Dicabut"
          value={revokedCount}
          icon={XCircle}
          fill={nbFill[accents.danger]}
        />
        <StatCard
          label="Total Pemakaian"
          value={totalUses}
          icon={TrendingUp}
          fill={nbFill[accents.info]}
        />
      </div>
      {/* ============================== Filters ============================= */}
      <Card className="nb-card-hover">
        <CardContent className="p-5">
          <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-center">
            <div className="relative min-w-0 flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink" />
              <Input
                placeholder="Cari berdasarkan kode atau penerbit..."
                value={searchInput}
                onChange={(e) => { setSearchInput(e.target.value); setPage(1) }}
                className="h-11 pl-10"
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <select
                aria-label="Filter jenis tiket"
                value={typeFilter}
                onChange={(e) => { setTypeFilter((e.target.value as TicketType) || ''); setPage(1) }}
                className="h-11 rounded-md border-2 border-ink bg-card px-3 text-sm font-bold text-foreground shadow-nb-sm"
              >
                <option value="">Semua Jenis</option>
                <option value="SINGLE_ENTRY">Sekali Masuk</option>
                <option value="MULTI_DAY">Multi Hari</option>
                <option value="VIP">VIP</option>
                <option value="STAFF">Staf</option>
              </select>
              <select
                aria-label="Filter status"
                value={revokedFilter === '' ? 'all' : revokedFilter.toString()}
                onChange={(e) => { setRevokedFilter(e.target.value === 'all' ? '' : e.target.value === 'true'); setPage(1) }}
                className="h-11 rounded-md border-2 border-ink bg-card px-3 text-sm font-bold text-foreground shadow-nb-sm"
              >
                <option value="all">Semua Status</option>
                <option value="false">Aktif</option>
                <option value="true">Dicabut</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>
      {/* =============================== Table =============================== */}
      <Card className="overflow-hidden">
        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-3 p-6">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : data?.items.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-12 text-center">
              <span className="flex h-20 w-20 items-center justify-center rounded-md border-2 border-ink bg-nb-yellow text-ink shadow-nb-sm">
                <AlertCircle className="h-9 w-9" />
              </span>
              <p className="mt-4 text-lg font-extrabold uppercase tracking-tight">Tiket tidak ditemukan</p>
              <p className="mt-1 text-sm font-semibold text-muted-foreground">
                Ubah kotak pencarian atau filter di atas untuk menemukan tiket.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Kode</TableHead>
                    <TableHead>Jenis</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Pemakaian</TableHead>
                    <TableHead>Berlaku Sampai</TableHead>
                    <TableHead>Diterbitkan</TableHead>
                    <TableHead className="text-right">Aksi</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data?.items.map((ticket, index) => {
                    const used = usagePercent(ticket.used_count, ticket.max_uses)
                    return (
                    <TableRow
                      key={ticket.id}
                      className={index % 2 === 0 ? 'bg-muted' : 'bg-card'}
                    >
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {/* shrink-0: a real code is wider than this column's
                              share, and a squeezed flex item would clip the
                              tail instead of widening the cell. */}
                          <span className="shrink-0 whitespace-nowrap font-mono text-sm font-extrabold">
                            {ticket.code}
                          </span>
                          <button
                            onClick={() => copyToClipboard(ticket.code)}
                            className="nb-press flex h-10 w-10 shrink-0 items-center justify-center rounded-md border-2 border-ink bg-nb-yellow text-ink shadow-nb-sm"
                            title="Salin kode"
                            aria-label="Salin kode"
                          >
                            <Copy className="h-4 w-4" />
                          </button>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge className={cn(getTicketBadge(ticket.type), 'gap-1 text-ink')}>
                          {getTicketTypeIcon(ticket.type)}
                          {getTicketLabel(ticket.type)}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge className={cn(ticket.revoked ? badge.danger : badge.success, 'text-ink')}>
                          {ticket.revoked ? '✗ Dicabut' : '✓ Aktif'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-extrabold tabular-nums">
                            {ticket.used_count}
                            {ticket.max_uses ? (
                              <span className="text-muted-foreground">/{ticket.max_uses}</span>
                            ) : null}
                          </span>
                          {ticket.max_uses > 0 && (
                            <div className="h-3 w-20 overflow-hidden rounded-md border-2 border-ink bg-card">
                              <div
                                className={cn('h-full', used >= 100 ? 'bg-nb-red' : 'bg-nb-blue')}
                                style={{ width: `${used}%` }}
                              />
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-sm font-semibold text-muted-foreground">
                        {ticket.valid_until ? new Date(ticket.valid_until).toLocaleDateString() : '∞'}
                      </TableCell>
                      <TableCell className="text-sm font-semibold text-muted-foreground">
                        {ticket.issued_by}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => handleViewQR(ticket.code)}
                            className="nb-press flex h-10 w-10 items-center justify-center rounded-md border-2 border-ink bg-nb-cyan text-ink shadow-nb-sm"
                            title="Lihat kode QR"
                            aria-label="Lihat kode QR"
                          >
                            <QrCode className="h-4 w-4" />
                          </button>
                          {!ticket.revoked && (
                            <button
                              onClick={() => handleRevoke(ticket.id)}
                              disabled={deleteMutation.isPending}
                              className="nb-press flex h-10 w-10 items-center justify-center rounded-md border-2 border-ink bg-nb-red text-ink shadow-nb-sm disabled:opacity-50"
                              title="Cabut tiket"
                              aria-label="Cabut tiket"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
      {/* ============================= Pagination =========================== */}
      {data && (
        <Pagination
          page={page}
          totalPages={data.total_pages}
          total={data.total}
          perPage={20}
          onPageChange={setPage}
          isLoading={isLoading}
        />
      )}
      {/* ============================ QR Code Modal ========================== */}
      {showQRCode && (
        <QRCodeModal tokenCode={showQRCode} onClose={() => setShowQRCode(null)} />
      )}
      {/* ======================= Revoke Confirmation ======================== */}
      <ConfirmDialog
        open={!!confirmRevoke}
        onClose={() => setConfirmRevoke(null)}
        onConfirm={() => confirmRevoke && deleteMutation.mutate(confirmRevoke)}
        title="Cabut Tiket?"
        description="Tiket akan dicabut permanen. Pengguna tidak lagi bisa memakainya untuk akses gerbang."
        confirmLabel="Cabut Tiket"
        variant="destructive"
        loading={deleteMutation.isPending}
      />
      {/* =========================== Create/Edit Form ======================= */}
      {showForm && (
        <TicketForm
          ticket={showForm === 'create' ? null : (showForm as TicketToken)}
          onSubmit={(data) => createMutation.mutate(data)}
          onClose={() => setShowForm(null)}
          isLoading={createMutation.isPending}
        />
      )}
    </div>
  )
}