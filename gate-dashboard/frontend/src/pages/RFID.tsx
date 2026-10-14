import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { cn, formatDateTime } from '../utils/helpers'
import { Card, CardContent } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../components/ui/table'
import { Dialog, DialogHeader, DialogContent, DialogFooter } from '../components/ui/dialog'
import { 
  Plus, 
  Search, 
  Trash2, 
  Wifi,
  Shield,
  UserCheck,
  UserX,
  AlertCircle,
  Save,
  X,
  Edit,
  IdCard,
} from 'lucide-react'
import { AuthorizedCard, PaginatedResponse } from '../types'
import toast from 'react-hot-toast'
import { Skeleton } from '../components/ui/skeleton'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { StatCard } from '../components/ui/stat-card'
import { useDebounce } from '../hooks/useDebounce'
import { accents, nb, nbFill } from '../styles/tokens'
import { Pagination } from '../components/ui/pagination'
interface CardFormData {
  uid: string
  label?: string
  note?: string
}
export function RFID() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [searchInput, setSearchInput] = useState('')
  const debouncedSearch = useDebounce(searchInput, 300)
  const [activeFilter, setActiveFilter] = useState<boolean | ''>('')
  const [showForm, setShowForm] = useState<AuthorizedCard | 'create' | null>(null)
  const [formData, setFormData] = useState<CardFormData>({ uid: '', label: '', note: '' })
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)
  const [tapMode, setTapMode] = useState<null | { unit: string; expiresAt: number }>(null)
  const { data, isLoading } = useQuery({
    queryKey: ['rfid-cards', page, debouncedSearch, activeFilter],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '50',
      })
      if (debouncedSearch) params.append('search', debouncedSearch)
      if (activeFilter !== '') params.append('active', activeFilter.toString())
      const response = await api.get<PaginatedResponse<AuthorizedCard>>(`/rfid?${params}`)
      return response.data
    },
  })
  const createMutation = useMutation({
    mutationFn: (data: CardFormData) => api.post('/rfid', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rfid-cards'] })
      toast.success('Kartu berhasil ditambahkan', { icon: '✓' })
      setShowForm(null)
      setFormData({ uid: '', label: '', note: '' })
      setPage(1)
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to add card'
      toast.error(message)
    },
  })
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<AuthorizedCard> }) => 
      api.patch(`/rfid/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rfid-cards'] })
      toast.success('Kartu berhasil diperbarui', { icon: '✓' })
      setShowForm(null)
      setFormData({ uid: '', label: '', note: '' })
    },
    onError: () => toast.error('Gagal memperbarui kartu'),
  })
  const toggleMutation = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) => 
      api.patch(`/rfid/${id}`, { active }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rfid-cards'] })
      toast.success('Status berhasil diperbarui', { icon: '✓' })
    },
    onError: () => toast.error('Gagal memperbarui status'),
  })
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/rfid/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rfid-cards'] })
      toast.success('Kartu berhasil dihapus', { icon: '✓' })
    },
    onError: () => toast.error('Gagal menghapus kartu'),
  })
  const syncMutation = useMutation({
    mutationFn: (unit: string) => api.post(`/rfid/sync-to-hardware/${unit}`),
    onSuccess: (response: any) => {
      toast.success(response.data?.message || 'Sync initiated', { icon: '📡' })
    },
    onError: () => toast.error('Gagal menyinkronkan'),
  })
  const tapRegisterMutation = useMutation({
    mutationFn: (unit: string) => api.post(`/rfid/register-tap/${unit}`),
    onSuccess: (response: any, unit: string) => {
      toast.success(response.data?.message || 'Add-master mode activated', { icon: '📡' })
      setTapMode({ unit: unit.toUpperCase(), expiresAt: Date.now() + 15000 })
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Gagal mengaktifkan mode tap'
      toast.error(message)
    },
  })

  // Listen for card-tapped events from GateContext
  React.useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail
      if (detail?.uid) {
        setFormData((prev) => ({ ...prev, uid: detail.uid }))
        setShowForm('create')
        setTapMode(null)
        toast.success(`Kartu terdeteksi: ${detail.uid}`, { icon: '✅' })
      }
    }
    window.addEventListener('card-tapped', handler)
    return () => window.removeEventListener('card-tapped', handler)
  }, [])

  // Countdown timer for tap mode
  const [tapCountdown, setTapCountdown] = useState(0)
  React.useEffect(() => {
    if (!tapMode) return
    const interval = setInterval(() => {
      const remaining = Math.max(0, Math.ceil((tapMode.expiresAt - Date.now()) / 1000))
      setTapCountdown(remaining)
      if (remaining <= 0) {
        setTapMode(null)
        setTapCountdown(0)
        toast.error('Waktu tap habis', { icon: '⏰' })
      }
    }, 200)
    return () => clearInterval(interval)
  }, [tapMode])
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.uid.trim()) {
      toast.error('UID wajib diisi')
      return
    }
    if (showForm === 'create') {
      createMutation.mutate(formData)
    } else if (showForm && 'id' in showForm) {
      updateMutation.mutate({ id: showForm.id, data: formData })
    }
  }
  const handleEdit = (card: AuthorizedCard) => {
    setShowForm(card)
    setFormData({ uid: card.uid, label: card.label || undefined, note: card.note || undefined })
  }
  const handleToggle = (card: AuthorizedCard) => {
    toggleMutation.mutate({ id: card.id, active: !card.active })
  }
  const handleDelete = (id: string) => {
    setConfirmDelete(id)
  }
  const activeCount = data?.items.filter(c => c.active).length || 0
  const inactiveCount = data?.items.filter(c => !c.active).length || 0
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-4xl font-extrabold uppercase tracking-tight sm:text-5xl">Kartu RFID</h1>
          <p className="mt-2 text-sm font-semibold text-muted-foreground">Kelola kartu RFID resmi untuk akses gerbang</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => tapRegisterMutation.mutate('ENTRY')}
            disabled={tapRegisterMutation.isPending || !!tapMode}
            className="gap-2"
          >
            <IdCard className="h-5 w-5" />
            Tap ENTRY
          </Button>
          <Button
            variant="outline"
            onClick={() => tapRegisterMutation.mutate('EXIT')}
            disabled={tapRegisterMutation.isPending || !!tapMode}
            className="gap-2"
          >
            <IdCard className="h-5 w-5" />
            Tap EXIT
          </Button>
          <Button
            onClick={() => { setShowForm('create'); setFormData({ uid: '', label: '', note: '' }) }}
            className="gap-2 bg-nb-purple text-ink"
          >
            <Plus className="h-5 w-5" />
            Tambah Kartu
          </Button>
        </div>
      </div>
      {/* Tap Mode Banner */}
      {tapMode && (
        <div className="flex items-center gap-3 rounded-md border-2 border-ink bg-nb-yellow px-5 py-4 shadow-nb-md">
          <div className="flex h-10 w-10 items-center justify-center rounded-md border-2 border-ink bg-card">
            <IdCard className="h-5 w-5 text-ink" />
          </div>
          <div className="flex-1">
            <p className="font-extrabold uppercase tracking-tight">
              Mode Aktif: Tap Kartu di {tapMode.unit}
            </p>
            <p className="text-sm font-semibold text-muted-foreground">
              Tempel kartu RFID pada reader {tapMode.unit} sekarang — {tapCountdown}s tersisa
            </p>
          </div>
          <div className="flex h-12 w-12 items-center justify-center rounded-md border-2 border-ink bg-card font-mono text-lg font-extrabold">
            {tapCountdown}
          </div>
        </div>
      )}
      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          label="Total Kartu"
          value={data?.total || 0}
          icon={Shield}
          fill={nbFill[accents.rfid]}
        />
        <StatCard
          label="Aktif"
          value={activeCount}
          icon={UserCheck}
          fill={nbFill[accents.success]}
        />
        <StatCard
          label="Nonaktif"
          value={inactiveCount}
          icon={UserX}
          fill={nbFill[accents.danger]}
        />
      </div>
      {/* Hardware Sync */}
      <Card className="overflow-hidden">
        <div className="flex items-center gap-2 border-b-2 border-ink bg-nb-cyan px-5 py-3.5">
          <Wifi className="h-5 w-5 shrink-0 text-ink" />
          <h2 className="text-base font-extrabold uppercase tracking-tight text-ink">
            Sinkronisasi Perangkat
          </h2>
        </div>
        <CardContent className="p-5 pt-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                onClick={() => syncMutation.mutate('ENTRY')}
                className="gap-2"
                disabled={syncMutation.isPending}
              >
                <Wifi className="h-4 w-4" />
                Sinkron ENTRY
              </Button>
              <Button
                variant="outline"
                onClick={() => syncMutation.mutate('EXIT')}
                className="gap-2"
                disabled={syncMutation.isPending}
              >
                <Wifi className="h-4 w-4" />
                Sinkron EXIT
              </Button>
            </div>
            <p className="nb-stripes rounded-md border-2 border-ink bg-nb-yellow px-3 py-2 text-sm font-semibold text-ink">
              💡 Tips: Kartu harus ditekan dalam 15 detik setelah sinkronisasi dimulai.
            </p>
          </div>
        </CardContent>
      </Card>
      {/* Filters */}
      <Card className="nb-card-hover">
        <CardContent className="p-5 pt-5">
          <p className="nb-label mb-3 text-muted-foreground">Cari Kartu</p>
          <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-center">
            <div className="relative min-w-0 flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink" />
              <Input
                placeholder="Cari UID, label..."
                value={searchInput}
                onChange={(e) => { setSearchInput(e.target.value); setPage(1) }}
                className="h-11 pl-10 font-bold"
              />
            </div>
            <select
              aria-label="Filter status"
              value={activeFilter === '' ? 'all' : activeFilter.toString()}
              onChange={(e) => { setActiveFilter(e.target.value === 'all' ? '' : e.target.value === 'true'); setPage(1) }}
              className="h-11 rounded-md border-2 border-ink bg-card px-3 text-sm font-bold text-foreground shadow-nb-sm"
            >
              <option value="all">Semua Status</option>
              <option value="true">Aktif</option>
              <option value="false">Nonaktif</option>
            </select>
          </div>
        </CardContent>
      </Card>
      {/* Table */}
      <Card className="overflow-hidden">
        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-3 p-6">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : data?.items.length === 0 ? (
            <div className="p-12 text-center">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-md border-2 border-ink bg-muted shadow-nb-sm">
                <AlertCircle className="h-8 w-8 text-ink" />
              </div>
              <p className="text-lg font-extrabold uppercase tracking-tight">Kartu RFID tidak ditemukan</p>
              <p className="mt-1 text-sm font-semibold text-muted-foreground">
                Tambahkan kartu untuk mengotorisasi akses gerbang.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>UID</TableHead>
                    <TableHead>Label</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Ditambahkan Oleh</TableHead>
                    <TableHead>Ditambahkan Pada</TableHead>
                    <TableHead className="text-right">Aksi</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data?.items.map((card) => (
                    <TableRow key={card.id}>
                      <TableCell className="whitespace-nowrap font-mono text-sm font-bold">{card.uid}</TableCell>
                      <TableCell className="text-sm">
                        {card.label || <span className="text-muted-foreground">—</span>}
                      </TableCell>
                      <TableCell>
                        <Badge className={cn('gap-1', card.active ? nb.green : nb.red)}>
                          {card.active ? <UserCheck className="h-3 w-3" /> : <UserX className="h-3 w-3" />}
                          {card.active ? 'Aktif' : 'Nonaktif'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">{card.added_by}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">{formatDateTime(card.added_at)}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleEdit(card)}
                            className="nb-press flex h-10 w-10 items-center justify-center rounded-md border-2 border-ink bg-nb-purple text-ink shadow-nb-sm"
                            title="Ubah kartu"
                            aria-label="Ubah kartu"
                          >
                            <Edit className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => handleToggle(card)}
                            disabled={toggleMutation.isPending}
                            className={cn(
                              'nb-press flex h-10 w-10 items-center justify-center rounded-md border-2 border-ink text-ink shadow-nb-sm disabled:opacity-50',
                              card.active ? 'bg-nb-orange' : 'bg-nb-green'
                            )}
                            title={card.active ? 'Nonaktifkan' : 'Aktifkan'}
                            aria-label={card.active ? 'Nonaktifkan kartu' : 'Aktifkan kartu'}
                          >
                            {card.active ? <UserX className="h-4 w-4" /> : <UserCheck className="h-4 w-4" />}
                          </button>
                          <button
                            onClick={() => handleDelete(card.id)}
                            disabled={deleteMutation.isPending}
                            className="nb-press flex h-10 w-10 items-center justify-center rounded-md border-2 border-ink bg-nb-red text-ink shadow-nb-sm disabled:opacity-50"
                            title="Hapus kartu"
                            aria-label="Hapus kartu"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
      {/* Pagination */}
      {data && (
        <Pagination
          page={page}
          totalPages={data.total_pages}
          total={data.total}
          perPage={50}
          onPageChange={setPage}
          isLoading={isLoading}
        />
      )}
      {/* Add/Edit Card Dialog */}
      {showForm && (
        <Dialog open onOpenChange={() => setShowForm(null)}>
          <DialogContent>
            <DialogHeader
              icon={<IdCard className="h-5 w-5" strokeWidth={3} />}
              tone="bg-nb-purple"
              title={showForm === 'create' ? 'Tambah Kartu RFID' : 'Ubah Kartu RFID'}
              description={
                showForm === 'create'
                  ? 'Daftarkan kartu RFID baru yang diizinkan'
                  : 'Perbarui informasi kartu RFID'
              }
            />
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="uid" className="nb-label">UID Kartu *</Label>
                <Input
                  id="uid"
                  value={formData.uid}
                  onChange={(e) => setFormData({ ...formData, uid: e.target.value.toUpperCase() })}
                  placeholder="mis. 04E12345AB67"
                  disabled={showForm !== 'create'}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="label" className="nb-label">Label (Opsional)</Label>
                <Input
                  id="label"
                  value={formData.label || ''}
                  onChange={(e) => setFormData({ ...formData, label: e.target.value })}
                  placeholder="mis. Kartu Gerbang Utama"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="note" className="nb-label">Catatan (Opsional)</Label>
                <Input
                  id="note"
                  value={formData.note || ''}
                  onChange={(e) => setFormData({ ...formData, note: e.target.value })}
                  placeholder="Keterangan tambahan tentang kartu ini..."
                />
              </div>
              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowForm(null)}
                  className="gap-2"
                >
                  <X className="h-4 w-4" strokeWidth={3} />
                  Batal
                </Button>
                <Button
                  type="submit"
                  disabled={createMutation.isPending || updateMutation.isPending}
                  className="gap-2 bg-nb-purple text-ink"
                >
                  <Save className="h-4 w-4" strokeWidth={3} />
                  {createMutation.isPending || updateMutation.isPending ? 'Menyimpan...' : 'Simpan'}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      )}
      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
          open={!!confirmDelete}
          onClose={() => setConfirmDelete(null)}
          onConfirm={() => confirmDelete && deleteMutation.mutate(confirmDelete)}
          title="Remove RFID Card?"
          description="This will permanently remove the RFID card from the system. The card will no longer be authorized for gate access."
          confirmLabel="Remove Card"
          variant="destructive"
          loading={deleteMutation.isPending}
        />
    </div>
  )
}