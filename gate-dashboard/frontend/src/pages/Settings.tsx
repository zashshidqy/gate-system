import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { printerApi } from '../api/client'
import { formatDateTime } from '../utils/helpers'
import { Card, CardHeader, CardContent, CardTitle, CardDescription } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../components/ui/table'
import { Dialog, DialogHeader, DialogContent, DialogFooter } from '../components/ui/dialog'
import { Select, SelectItem } from '../components/ui/select'
import { Plus, Search, Edit, Trash2, Shield, User, UserX, UserPlus, Printer, AlertCircle, Loader2, Usb } from 'lucide-react'
import { User as UserType, UserRole, PrinterTestResponse, GateTicketTestRequest, ExitScanRequest, ExitScanResponse } from '../types'
import toast from 'react-hot-toast'
import { useAuth } from '../context/AuthContext'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { Pagination } from '../components/ui/pagination'
import { Tabs, TabsList, TabsTrigger } from '../components/ui/tabs'
import { cn } from '../utils/helpers'
import { nbFill, accents } from '../styles/tokens'

export function Settings() {
  const { user: currentUser } = useAuth()
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState<UserRole | ''>('')
  const [activeFilter, setActiveFilter] = useState<boolean | ''>('')
  const [showForm, setShowForm] = useState<UserType | null>(null)
  const [activeTab, setActiveTab] = useState<'users' | 'profile' | 'printer'>('users')
  const [confirmDeactivate, setConfirmDeactivate] = useState<string | null>(null)
  const [printerTestLoading, setPrinterTestLoading] = useState(false)
  const [gateTicketForm, setGateTicketForm] = useState<GateTicketTestRequest>({
    direction: 'ENTRY',
    ticket_type: 'SINGLE_ENTRY',
    ticket_code: 'TKT-20261012-ABCD1234',
    plate: 'B 1234 ABC',
    rfid_uid: 'A1 B2 C3 D4',
    method: 'QR_SCAN',
    gate_name: 'Gerbang Utama',
    operator: currentUser?.username || 'Operator 1',
    company_name: 'PT Smart Gate Solutions',
    company_website: 'https://smartgate.co.id',
    show_qr: true,
    entry_time: new Date(Date.now() - 2.5 * 60 * 60 * 1000).toISOString(),
    exit_time: new Date().toISOString(),
    duration_hours: 2.5,
    duration_text: '2 jam 30 menit',
    parking_fee: 12500,
    payment_method: 'QRIS',
  })

  const { data, isLoading } = useQuery({
    queryKey: ['users', page, search, roleFilter, activeFilter],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '20',
      })
      if (search) params.append('search', search)
      if (roleFilter) params.append('role', roleFilter)
      if (activeFilter !== '') params.append('active', activeFilter.toString())

      const response = await api.get(`/users?${params}`)
      return response.data
    },
  })

  const { data: printerStatus, isLoading: printerLoading, refetch: refetchPrinter } = useQuery({
    queryKey: ['printer-status'],
    queryFn: async () => {
      const response = await printerApi.getStatus()
      return response.data
    },
    refetchInterval: 30_000,
    retry: 1,
  })

  const createMutation = useMutation({
    mutationFn: (data: { username: string; email?: string; password: string; full_name?: string; role: string }) =>
      api.post('/users', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      toast.success('Pengguna dibuat')
      setShowForm(null)
    },
    onError: () => toast.error('Gagal membuat pengguna'),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<UserType> }) => api.patch(`/users/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      toast.success('Pengguna diperbarui')
      setShowForm(null)
    },
    onError: () => toast.error('Gagal memperbarui pengguna'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/users/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      toast.success('Pengguna dinonaktifkan')
    },
    onError: () => toast.error('Gagal menonaktifkan pengguna'),
  })

  const passwordMutation = useMutation({
    mutationFn: (data: { current_password: string; new_password: string }) =>
      api.post('/auth/change-password', data),
    onSuccess: () => toast.success('Kata sandi diubah'),
    onError: () => toast.error('Gagal mengubah kata sandi'),
  })

  const testPrintMutation = useMutation({
    mutationFn: async () => {
      const response = await printerApi.testPrint()
      return response.data
    },
    onSuccess: (data: PrinterTestResponse) => {
      if (data.success) {
        toast.success(data.message)
      } else {
        toast.error(data.message)
      }
      refetchPrinter()
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Gagal mencetak test'
      toast.error(message)
    },
    onSettled: () => setPrinterTestLoading(false),
  })

  const gateTicketTestMutation = useMutation({
    mutationFn: async (req: GateTicketTestRequest) => {
      const response = await printerApi.testGateTicket(req)
      return response.data
    },
    onSuccess: (data: PrinterTestResponse) => {
      if (data.success) {
        toast.success(data.message)
      } else {
        toast.error(data.message)
      }
      refetchPrinter()
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Gagal mencetak tiket gerbang'
      toast.error(message)
    },
    onSettled: () => setPrinterTestLoading(false),
  })

  const [exitScanResult, setExitScanResult] = useState<ExitScanResponse | null>(null)
  const [exitScanLoading, setExitScanLoading] = useState(false)

  const exitScanMutation = useMutation({
    mutationFn: async (req: ExitScanRequest) => {
      const response = await printerApi.testExitScan(req)
      return response.data
    },
    onSuccess: (data: ExitScanResponse) => {
      setExitScanResult(data)
      toast.success('Barcode berhasil di-scan!')
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Gagal scan barcode'
      toast.error(message)
    },
    onSettled: () => setExitScanLoading(false),
  })

  const handleSubmit = (data: any) => {
    if (showForm) {
      updateMutation.mutate({ id: showForm.id, data })
    } else {
      createMutation.mutate(data)
    }
  }

  const handleDelete = (id: string) => {
    setConfirmDeactivate(id)
  }

  const handleEdit = (user: UserType) => {
    setShowForm(user)
  }

  const openCreateForm = () => {
    setShowForm({ id: '', username: '', email: '', full_name: '', role: 'STAFF', active: true, created_at: '', last_login: null } as any)
  }

  const getRoleVariant = (role: UserRole): 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning' => {
    switch (role) {
      case 'ADMIN': return 'destructive'
      case 'GUARD': return 'warning'
      case 'STAFF': return 'default'
      default: return 'outline'
    }
  }

  const renderUserManagement = () => {
    const isEmpty = !isLoading && data && data.items && data.items.length === 0

    return (
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-extrabold uppercase tracking-tight text-foreground">
              Manajemen Pengguna
            </h1>
            <p className="mt-2 text-sm font-semibold text-muted-foreground">
              Kelola pengguna sistem dan perannya
            </p>
          </div>
          <Button onClick={openCreateForm} size="lg" className="w-full sm:w-auto">
            <Plus className="h-5 w-5" strokeWidth={3} />
            Tambah Pengguna
          </Button>
        </div>

        {/* Filters */}
        <Card>
          <CardHeader className="pb-3">
            <p className="nb-label text-foreground">Filter</p>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="relative min-w-0 flex-1 sm:max-w-sm">
                <Search
                  className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-foreground"
                  strokeWidth={3}
                  aria-hidden="true"
                />
                <Input
                  placeholder="Cari pengguna..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
              <div className="flex flex-wrap gap-3">
                <Select
                  value={roleFilter}
                  onValueChange={(v) => setRoleFilter(v as UserRole | '')}
                  className="w-[160px]"
                  aria-label="Filter peran"
                >
                  <SelectItem value="">Semua Peran</SelectItem>
                  <SelectItem value="ADMIN">Admin</SelectItem>
                  <SelectItem value="GUARD">Guard</SelectItem>
                  <SelectItem value="STAFF">Staff</SelectItem>
                </Select>
                <Select
                  value={activeFilter === '' ? 'all' : activeFilter.toString()}
                  onValueChange={(v) => setActiveFilter(v === 'all' ? '' : v === 'true')}
                  className="w-[140px]"
                  aria-label="Filter status"
                >
                  <SelectItem value="all">Semua Status</SelectItem>
                  <SelectItem value="true">Aktif</SelectItem>
                  <SelectItem value="false">Nonaktif</SelectItem>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Users Table */}
        <Card className="overflow-hidden">
          <CardHeader className="flex-row items-center justify-between gap-3 pb-4">
            <p className="nb-label text-foreground">Direktori Pengguna</p>
            {data && (
              <span className="nb-label rounded-md border-2 border-ink bg-muted px-2.5 py-1 text-foreground">
                Total {data.total}
              </span>
            )}
          </CardHeader>
          <CardContent className="p-0">
            {isLoading ? (
              <div className="space-y-3 p-6">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="h-12 animate-pulse rounded-md border-2 border-ink bg-muted" />
                ))}
              </div>
            ) : isEmpty ? (
              <div className="flex flex-col items-center justify-center gap-4 px-6 py-16 text-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-md border-2 border-ink bg-nb-purple text-ink shadow-nb">
                  <UserX className="h-8 w-8" strokeWidth={3} aria-hidden="true" />
                </div>
                <p className="text-xl font-extrabold uppercase tracking-tight text-foreground">
                  Pengguna tidak ditemukan
                </p>
                <p className="max-w-sm text-sm font-semibold text-muted-foreground">
                  Tidak ada yang cocok dengan pencarian dan filter saat ini. Coba kata lain atau atur ulang filter.
                </p>
              </div>
            ) : (
              <div>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-36">Nama Pengguna</TableHead>
                        <TableHead className="w-40">Email</TableHead>
                        <TableHead>Nama Lengkap</TableHead>
                        <TableHead className="w-28">Peran</TableHead>
                        <TableHead className="w-24">Status</TableHead>
                        <TableHead className="w-36">Dibuat</TableHead>
                        <TableHead className="w-36">Login Terakhir</TableHead>
                        <TableHead className="w-28 text-right">Aksi</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data?.items.map((u: UserType) => (
                        <TableRow key={u.id}>
                          <TableCell className="text-sm font-extrabold text-foreground">{u.username}</TableCell>
                          <TableCell className="max-w-[200px] truncate text-sm font-semibold">
                            {u.email || <span className="text-muted-foreground">—</span>}
                          </TableCell>
                          <TableCell className="max-w-[200px] truncate text-sm font-semibold">
                            {u.full_name || <span className="text-muted-foreground">—</span>}
                          </TableCell>
                          <TableCell>
                            <Badge variant={getRoleVariant(u.role)}>{u.role}</Badge>
                          </TableCell>
                          <TableCell>
                            <Badge variant={u.active ? 'success' : 'destructive'}>
                              {u.active ? 'Aktif' : 'Nonaktif'}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-sm font-semibold">{formatDateTime(u.created_at)}</TableCell>
                          <TableCell className="text-sm font-semibold text-muted-foreground">
                            {u.last_login ? formatDateTime(u.last_login) : 'Belum pernah'}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-2">
                              {u.id !== currentUser?.id && (
                                <>
                                  <Button
                                    variant="outline"
                                    size="icon"
                                    className="shadow-nb-sm"
                                    onClick={() => handleEdit(u)}
                                    title="Ubah pengguna"
                                    aria-label="Ubah pengguna"
                                  >
                                    <Edit className="h-4 w-4" strokeWidth={2.5} />
                                  </Button>
                                  {!u.active && (
                                    <Button
                                      variant="outline"
                                      size="icon"
                                      className="bg-success text-success-foreground shadow-nb-sm"
                                      onClick={() => updateMutation.mutate({ id: u.id, data: { active: true } })}
                                      title="Aktifkan pengguna"
                                      aria-label="Aktifkan pengguna"
                                    >
                                      <Shield className="h-4 w-4" strokeWidth={2.5} />
                                    </Button>
                                  )}
                                  {u.active && u.id !== currentUser?.id && (
                                    <Button
                                      variant="outline"
                                      size="icon"
                                      className="bg-destructive text-destructive-foreground shadow-nb-sm"
                                      onClick={() => handleDelete(u.id)}
                                      title="Nonaktifkan pengguna"
                                      aria-label="Nonaktifkan pengguna"
                                    >
                                      <Trash2 className="h-4 w-4" strokeWidth={2.5} />
                                    </Button>
                                  )}
                                </>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>

                {/* Pagination */}
                {data && (
                  <Pagination
                    variant="strip"
                    page={page}
                    totalPages={data.total_pages}
                    total={data.total}
                    perPage={20}
                    onPageChange={setPage}
                    isLoading={isLoading}
                  />
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* User Form Modal */}
        <Dialog open={!!showForm} onOpenChange={(open) => !open && setShowForm(null)} size="md">
          <DialogContent>
            <DialogHeader
              icon={<UserPlus className="h-5 w-5" strokeWidth={3} />}
              tone="bg-nb-yellow"
              title={showForm?.id ? 'Ubah Pengguna' : 'Tambah Pengguna'}
              description={
                showForm?.id ? 'Ubah detail pengguna' : 'Buat pengguna sistem baru'
              }
            />
            <UserForm
              user={showForm}
              onSubmit={handleSubmit}
              onClose={() => setShowForm(null)}
              isLoading={createMutation.isPending || updateMutation.isPending}
            />
          </DialogContent>
        </Dialog>
      </div>
    )
  }

  const renderProfile = () => (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-extrabold uppercase tracking-tight text-foreground">
          Profil Saya
        </h1>
        <p className="mt-2 text-sm font-semibold text-muted-foreground">
          Detail akun dan kredensial Anda
        </p>
      </div>
      <ProfileSettings
        currentUser={currentUser}
        onPasswordChange={passwordMutation.mutate}
        isChangingPassword={passwordMutation.isPending}
      />
    </div>
  )

  const renderPrinter = () => (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-extrabold uppercase tracking-tight text-foreground">
            Printer Thermal (POS80)
          </h1>
          <p className="mt-2 text-sm font-semibold text-muted-foreground">
            Kelola dan test printer tiket/resi iware IW 8220
          </p>
        </div>

        {/* Status Card */}
        <Card>
          <CardHeader className="border-b-2 border-ink bg-nb-cyan">
            <div className="flex items-start justify-between gap-3">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Printer className="h-6 w-6" strokeWidth={3} aria-hidden="true" />
                  Status Printer
                </CardTitle>
                <CardDescription className="mt-1 text-ink/70">
                  Koneksi USB & CUPS
                </CardDescription>
              </div>
              {printerStatus && (
                <Badge className={cn('shrink-0 gap-1', printerStatus.connected ? nbFill[accents.success] : nbFill[accents.danger])}>
                  <span className="h-2.5 w-2.5 rounded-sm border-2 border-ink bg-ink" />
                  {printerStatus.connected ? 'Terhubung' : 'Terputus'}
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col pt-6">
            {printerLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" strokeWidth={2.5} />
              </div>
            ) : printerStatus ? (
              <div className="space-y-4">
                {/* Connection details grid */}
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div className="rounded-md border-2 border-ink bg-card p-4">
                    <p className="nb-label text-muted-foreground">Nama Printer</p>
                    <p className="mt-1 font-mono text-lg font-extrabold">{printerStatus.name}</p>
                  </div>
                  <div className="rounded-md border-2 border-ink bg-card p-4">
                    <p className="nb-label text-muted-foreground">Driver</p>
                    <p className="mt-1 font-mono text-lg font-extrabold">{printerStatus.driver}</p>
                  </div>
                  <div className="rounded-md border-2 border-ink bg-card p-4">
                    <p className="nb-label text-muted-foreground">USB Device</p>
                    <div className="mt-1 flex items-center gap-2">
                      <Usb className={cn('h-5 w-5', printerStatus.usb_detected ? 'text-success' : 'text-destructive')} strokeWidth={2.5} />
                      <span className="font-extrabold">
                        {printerStatus.usb_detected ? 'Terdeteksi (0416:5011)' : 'Tidak terdeteksi'}
                      </span>
                    </div>
                  </div>
                  <div className="rounded-md border-2 border-ink bg-card p-4">
                    <p className="nb-label text-muted-foreground">CUPS Status</p>
                    <p className="mt-1 font-mono text-sm font-semibold truncate">{printerStatus.cups_status || '—'}</p>
                  </div>
                </div>

                {/* URI */}
                <div className="rounded-md border-2 border-ink bg-muted p-4">
                  <p className="nb-label text-muted-foreground">URI CUPS</p>
                  <p className="mt-1 font-mono text-xs font-semibold truncate break-all">{printerStatus.uri}</p>
                </div>

                {/* Basic Test Print Button */}
                <div className="pt-4 border-t-2 border-ink">
                  <Button
                    onClick={() => {
                      setPrinterTestLoading(true)
                      testPrintMutation.mutate()
                    }}
                    disabled={!printerStatus?.connected || printerTestLoading || testPrintMutation.isPending}
                    className="w-full sm:w-auto gap-2 bg-nb-green text-ink"
                    size="lg"
                  >
                    {printerTestLoading || testPrintMutation.isPending ? (
                      <>
                        <Loader2 className="h-5 w-5 animate-spin" strokeWidth={3} />
                        Mencetak...
                      </>
                    ) : (
                      <>
                        <Printer className="h-5 w-5" strokeWidth={3} />
                        Test Print (ESC/POS)
                      </>
                    )}
                  </Button>
                  <p className="mt-3 text-xs font-semibold text-muted-foreground text-center">
                    Mencetak resi test: header, tanggal, driver info, dan potong kertas parsial
                  </p>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-destructive">
                <AlertCircle className="h-12 w-12 mx-auto mb-3" strokeWidth={2.5} />
                <p className="font-extrabold">Gagal memuat status printer</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Gate Ticket Test Print Card */}
        <Card className="border-nb-blue">
          <CardHeader className="border-b-2 border-ink bg-nb-blue">
            <CardTitle className="flex items-center gap-2">
              <Printer className="h-6 w-6" strokeWidth={3} aria-hidden="true" />
              Test Print Tiket Gerbang (Real Case)
            </CardTitle>
            <CardDescription className="mt-1 text-ink/70">
              Simulasi cetak tiket masuk/keluar gerbang dengan data lengkap
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6 space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div className="space-y-2">
                <Label>Arah</Label>
                <Select
                  value={gateTicketForm.direction}
                  onValueChange={(v) => setGateTicketForm((prev) => ({ ...prev, direction: v as 'ENTRY' | 'EXIT' }))}
                >
                  <SelectItem value="ENTRY">MASUK (Entry)</SelectItem>
                  <SelectItem value="EXIT">KELUAR (Exit)</SelectItem>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Tipe Tiket</Label>
                <Select
                  value={gateTicketForm.ticket_type}
                  onValueChange={(v) => setGateTicketForm((prev) => ({ ...prev, ticket_type: v as any }))}
                >
                  <SelectItem value="SINGLE_ENTRY">Sekali Masuk</SelectItem>
                  <SelectItem value="MULTI_DAY">Multi Hari</SelectItem>
                  <SelectItem value="VIP">VIP</SelectItem>
                  <SelectItem value="STAFF">Staf</SelectItem>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Metode</Label>
                <Select
                  value={gateTicketForm.method}
                  onValueChange={(v) => setGateTicketForm((prev) => ({ ...prev, method: v as any }))}
                >
                  <SelectItem value="QR_SCAN">Scan QR Code</SelectItem>
                  <SelectItem value="RFID_LINK">Kartu RFID</SelectItem>
                  <SelectItem value="MANUAL">Manual</SelectItem>
                  <SelectItem value="ANPR">ANPR / Plat</SelectItem>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Nama Gerbang</Label>
                <Input
                  value={gateTicketForm.gate_name}
                  onChange={(e) => setGateTicketForm((prev) => ({ ...prev, gate_name: e.target.value }))}
                />
              </div>
              <div className="space-y-2 sm:col-span-2">
                <Label>Kode Tiket</Label>
                <Input
                  value={gateTicketForm.ticket_code}
                  onChange={(e) => setGateTicketForm((prev) => ({ ...prev, ticket_code: e.target.value }))}
                />
              </div>
              <div className="space-y-2 sm:col-span-2">
                <Label>Plat Nomor (opsional)</Label>
                <Input
                  value={gateTicketForm.plate || ''}
                  onChange={(e) => setGateTicketForm((prev) => ({ ...prev, plate: e.target.value || undefined }))}
                  placeholder="B 1234 ABC"
                />
              </div>
              <div className="space-y-2 sm:col-span-2">
                <Label>RFID UID (opsional)</Label>
                <Input
                  value={gateTicketForm.rfid_uid || ''}
                  onChange={(e) => setGateTicketForm((prev) => ({ ...prev, rfid_uid: e.target.value || undefined }))}
                  placeholder="A1 B2 C3 D4"
                />
              </div>
              <div className="space-y-2">
                <Label>Petugas</Label>
                <Input
                  value={gateTicketForm.operator}
                  onChange={(e) => setGateTicketForm((prev) => ({ ...prev, operator: e.target.value }))}
                />
              </div>
              <div className="space-y-2 sm:col-span-2">
                <Label>Nama Perusahaan</Label>
                <Input
                  value={gateTicketForm.company_name}
                  onChange={(e) => setGateTicketForm((prev) => ({ ...prev, company_name: e.target.value }))}
                  placeholder="PT Smart Gate Solutions"
                />
              </div>
              <div className="space-y-2 sm:col-span-2">
                <Label>Website Perusahaan</Label>
                <Input
                  value={gateTicketForm.company_website}
                  onChange={(e) => setGateTicketForm((prev) => ({ ...prev, company_website: e.target.value }))}
                  placeholder="https://example.com"
                />
              </div>
              <div className="space-y-2 sm:col-span-2 lg:col-span-4">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="show_qr"
                    checked={gateTicketForm.show_qr}
                    onChange={(e) => setGateTicketForm((prev) => ({ ...prev, show_qr: e.target.checked }))}
                    className="h-4 w-4 rounded border-2 border-ink"
                  />
                  <Label htmlFor="show_qr" className="cursor-pointer">
                    {gateTicketForm.direction === 'ENTRY'
                      ? 'Tampilkan QR Code di tiket (untuk scan saat keluar)'
                      : 'Tampilkan QR Code di tiket (link ke website perusahaan)'}
                  </Label>
                </div>
              </div>

              {/* Exit-specific fields */}
              {gateTicketForm.direction === 'EXIT' && (
                <>
                  <div className="rounded-md border-2 border-ink bg-muted p-4 space-y-4">
                    <p className="nb-label text-foreground">Data Parkir (Khusus Exit)</p>
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                      <div className="space-y-2">
                        <Label>Waktu Masuk</Label>
                        <Input
                          type="time"
                          value={gateTicketForm.entry_time ? gateTicketForm.entry_time.slice(11, 16) : ''}
                          onChange={(e) => {
                            const date = gateTicketForm.entry_time?.slice(0, 10) || new Date().toISOString().slice(0, 10)
                            setGateTicketForm((prev) => ({ ...prev, entry_time: `${date}T${e.target.value}:00` }))
                          }}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Waktu Keluar</Label>
                        <Input
                          type="time"
                          value={gateTicketForm.exit_time ? gateTicketForm.exit_time.slice(11, 16) : ''}
                          onChange={(e) => {
                            const date = gateTicketForm.exit_time?.slice(0, 10) || new Date().toISOString().slice(0, 10)
                            setGateTicketForm((prev) => ({ ...prev, exit_time: `${date}T${e.target.value}:00` }))
                          }}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Durasi (jam)</Label>
                        <Input
                          type="number"
                          step="0.25"
                          min="0"
                          value={gateTicketForm.duration_hours || ''}
                          onChange={(e) => {
                            const hours = parseFloat(e.target.value) || 0
                            const h = Math.floor(hours)
                            const m = Math.round((hours - h) * 60)
                            setGateTicketForm((prev) => ({
                              ...prev,
                              duration_hours: hours,
                              duration_text: `${h} jam ${m} menit`,
                            }))
                          }}
                          placeholder="2.25"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Biaya Parkir (Rp)</Label>
                        <Input
                          type="number"
                          step="500"
                          min="0"
                          value={gateTicketForm.parking_fee || ''}
                          onChange={(e) => setGateTicketForm((prev) => ({ ...prev, parking_fee: parseInt(e.target.value) || 0 }))}
                          placeholder="15000"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Metode Pembayaran</Label>
                        <Select
                          value={gateTicketForm.payment_method || 'CASH'}
                          onValueChange={(v) => setGateTicketForm((prev) => ({ ...prev, payment_method: v as any }))}
                        >
                          <SelectItem value="CASH">Tunai</SelectItem>
                          <SelectItem value="QRIS">QRIS</SelectItem>
                          <SelectItem value="CARD">Kartu Debit/Kredit</SelectItem>
                          <SelectItem value="E_WALLET">E-Wallet</SelectItem>
                        </Select>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>

            <div className="pt-4 border-t-2 border-ink">
              <Button
                onClick={() => {
                  setPrinterTestLoading(true)
                  gateTicketTestMutation.mutate(gateTicketForm)
                }}
                disabled={!printerStatus?.connected || printerTestLoading || gateTicketTestMutation.isPending}
                className="w-full sm:w-auto gap-2 bg-nb-blue text-ink"
                size="lg"
              >
                {printerTestLoading || gateTicketTestMutation.isPending ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" strokeWidth={3} />
                    Mencetak Tiket...
                  </>
                ) : (
                  <>
                    <Printer className="h-5 w-5" strokeWidth={3} />
                    Cetak Tiket Gerbang
                  </>
                )}
              </Button>
              <p className="mt-3 text-xs font-semibold text-muted-foreground text-center">
                Mencetak tiket gerbang realistis: header, arah, kode tiket, plat/RFID, gerbang, petugas, potong parsial
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Exit Scan Test Card */}
        <Card className="border-nb-green">
          <CardHeader className="border-b-2 border-ink bg-nb-green">
            <CardTitle className="flex items-center gap-2">
              <Printer className="h-6 w-6" strokeWidth={3} aria-hidden="true" />
              Test Scan Barcode (Exit Gate)
            </CardTitle>
            <CardDescription className="mt-1 text-ink/70">
              Simulasi scan barcode tiket masuk di gerbang keluar
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6 space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <div className="space-y-2">
                <Label>Kode Tiket (Barcode)</Label>
                <Input
                  id="exit_scan_ticket_code"
                  placeholder="Scan atau ketik kode tiket..."
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      const target = e.target as HTMLInputElement
                      if (target.value.trim()) {
                        setExitScanLoading(true)
                        exitScanMutation.mutate({
                          ticket_code: target.value.trim(),
                          plate: gateTicketForm.plate,
                          rfid_uid: gateTicketForm.rfid_uid || undefined,
                          ticket_type: gateTicketForm.ticket_type,
                          entry_time: gateTicketForm.entry_time,
                          gate_name: gateTicketForm.gate_name,
                        })
                      }
                    }
                  }}
                />
              </div>
              <div className="space-y-2">
                <Label>Plat Nomor</Label>
                <Input
                  id="exit_scan_plate"
                  placeholder="B 1234 ABC"
                  defaultValue={gateTicketForm.plate || ''}
                  onBlur={(e) => {
                    const val = e.target.value.trim()
                    if (val) {
                      setExitScanLoading(true)
                      const codeInput = document.getElementById('exit_scan_ticket_code') as HTMLInputElement
                      exitScanMutation.mutate({
                        ticket_code: codeInput?.value?.trim() || gateTicketForm.ticket_code,
                        plate: val,
                        rfid_uid: gateTicketForm.rfid_uid || undefined,
                        ticket_type: gateTicketForm.ticket_type,
                        entry_time: gateTicketForm.entry_time,
                        gate_name: gateTicketForm.gate_name,
                      })
                    }
                  }}
                />
              </div>
              <div className="space-y-2">
                <Label>Waktu Masuk</Label>
                <Input
                  id="exit_scan_entry_time"
                  type="datetime-local"
                  defaultValue={gateTicketForm.entry_time ? gateTicketForm.entry_time.slice(0, 16) : ''}
                  onBlur={(e) => {
                    const val = e.target.value
                    if (val) {
                      setExitScanLoading(true)
                      const codeInput = document.getElementById('exit_scan_ticket_code') as HTMLInputElement
                      exitScanMutation.mutate({
                        ticket_code: codeInput?.value?.trim() || gateTicketForm.ticket_code,
                        plate: gateTicketForm.plate,
                        rfid_uid: gateTicketForm.rfid_uid || undefined,
                        ticket_type: gateTicketForm.ticket_type,
                        entry_time: new Date(val).toISOString(),
                        gate_name: gateTicketForm.gate_name,
                      })
                    }
                  }}
                />
              </div>
            </div>

            <div className="pt-4 border-t-2 border-ink">
              <Button
                onClick={() => {
                  const codeInput = document.getElementById('exit_scan_ticket_code') as HTMLInputElement
                  const plateInput = document.getElementById('exit_scan_plate') as HTMLInputElement
                  const entryTimeInput = document.getElementById('exit_scan_entry_time') as HTMLInputElement
                  if (codeInput?.value?.trim()) {
                    setExitScanLoading(true)
                    exitScanMutation.mutate({
                      ticket_code: codeInput.value.trim(),
                      plate: plateInput?.value?.trim() || undefined,
                      rfid_uid: gateTicketForm.rfid_uid || undefined,
                      ticket_type: gateTicketForm.ticket_type,
                      entry_time: entryTimeInput?.value ? new Date(entryTimeInput.value).toISOString() : undefined,
                      gate_name: gateTicketForm.gate_name,
                    })
                  }
                }}
                disabled={exitScanLoading || exitScanMutation.isPending}
                className="w-full sm:w-auto gap-2 bg-nb-green text-ink"
                size="lg"
              >
                {exitScanLoading || exitScanMutation.isPending ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" strokeWidth={3} />
                    Scanning...
                  </>
                ) : (
                  <>
                    <Printer className="h-5 w-5" strokeWidth={3} />
                    Scan Barcode Tiket
                  </>
                )}
              </Button>
              <p className="mt-3 text-xs font-semibold text-muted-foreground text-center">
                Simulasi pemindaian barcode tiket masuk di gerbang keluar
              </p>
            </div>

            {/* Scan Result Display */}
            {exitScanResult && (
              <div className="mt-4 rounded-md border-2 border-ink bg-card p-4 space-y-4">
                <p className="nb-label text-foreground">Hasil Scan</p>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  <div className="rounded-md border-2 border-ink bg-muted p-3">
                    <p className="text-xs font-semibold text-muted-foreground">Kode Tiket</p>
                    <p className="mt-1 font-mono text-sm font-extrabold text-foreground">{exitScanResult.ticket_code}</p>
                  </div>
                  <div className="rounded-md border-2 border-ink bg-muted p-3">
                    <p className="text-xs font-semibold text-muted-foreground">Tipe Tiket</p>
                    <p className="mt-1 font-mono text-sm font-extrabold text-foreground">{exitScanResult.ticket_type}</p>
                  </div>
                  <div className="rounded-md border-2 border-ink bg-muted p-3">
                    <p className="text-xs font-semibold text-muted-foreground">Plat Nomor</p>
                    <p className="mt-1 font-mono text-sm font-extrabold text-foreground">{exitScanResult.plate || '-'}</p>
                  </div>
                  <div className="rounded-md border-2 border-ink bg-muted p-3">
                    <p className="text-xs font-semibold text-muted-foreground">Waktu Masuk</p>
                    <p className="mt-1 font-mono text-sm font-extrabold text-foreground">
                      {exitScanResult.entry_time ? exitScanResult.entry_time.slice(11, 19) : '-'}
                    </p>
                  </div>
                  <div className="rounded-md border-2 border-ink bg-muted p-3">
                    <p className="text-xs font-semibold text-muted-foreground">Waktu Keluar</p>
                    <p className="mt-1 font-mono text-sm font-extrabold text-foreground">{exitScanResult.exit_time.slice(11, 19)}</p>
                  </div>
                  <div className="rounded-md border-2 border-ink bg-muted p-3">
                    <p className="text-xs font-semibold text-muted-foreground">Durasi</p>
                    <p className="mt-1 font-mono text-sm font-extrabold text-foreground">{exitScanResult.duration_text}</p>
                  </div>
                  <div className="rounded-md border-2 border-ink bg-muted p-3 sm:col-span-2">
                    <p className="text-xs font-semibold text-muted-foreground">Biaya Parkir</p>
                    <p className="mt-1 font-mono text-lg font-extrabold text-foreground">Rp {exitScanResult.parking_fee.toLocaleString('id-ID')}</p>
                  </div>
                  <div className="rounded-md border-2 border-ink bg-muted p-3">
                    <p className="text-xs font-semibold text-muted-foreground">Metode Pembayaran</p>
                    <p className="mt-1 font-mono text-sm font-extrabold text-foreground">{exitScanResult.payment_method}</p>
                  </div>
                  <div className="rounded-md border-2 border-ink bg-muted p-3">
                    <p className="text-xs font-semibold text-muted-foreground">Gerbang</p>
                    <p className="mt-1 font-mono text-sm font-extrabold text-foreground">{exitScanResult.gate_name}</p>
                  </div>
                </div>
                <div className="rounded-md border-2 border-ink bg-nb-yellow p-3">
                  <p className="text-center font-extrabold text-foreground">{exitScanResult.message}</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Troubleshooting Card */}
        <Card className="border-nb-orange">
          <CardHeader className="border-b-2 border-ink bg-nb-orange">
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-6 w-6" strokeWidth={3} aria-hidden="true" />
              Troubleshooting
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6 space-y-3 text-sm font-semibold text-muted-foreground">
            <div className="rounded-md border-2 border-ink bg-card p-4 space-y-2">
              <p className="font-extrabold text-foreground">Jika printer tidak terdeteksi:</p>
              <ol className="list-decimal list-inside space-y-1 ml-2">
                <li>Pastikan printer menyala & kabel USB colok rapat</li>
                <li>Jalankan <code className="font-mono bg-muted px-1.5 py-0.5 rounded">lsusb | grep 0416:5011</code> di terminal</li>
                <li>Jika <code className="font-mono bg-muted px-1.5 py-0.5 rounded">usblp</code> module aktif: <code className="font-mono bg-muted px-1.5 py-0.5 rounded">echo "blacklist usblp" | sudo tee /etc/modprobe.d/blacklist-usblp.conf && sudo update-initramfs -u</code> lalu reboot</li>
                <li>Pastikan user ada di group <code className="font-mono bg-muted px-1.5 py-0.5 rounded">lp</code>: <code className="font-mono bg-muted px-1.5 py-0.5 rounded">sudo usermod -a -G lp $USER</code> lalu logout/login</li>
                <li>Restart CUPS: <code className="font-mono bg-muted px-1.5 py-0.5 rounded">sudo systemctl restart cups</code></li>
              </ol>
            </div>
          </CardContent>
        </Card>
      </div>
    )

  return (
    <div className="space-y-6">
      {/* Tab Navigation — uses the shared Tabs so the trigger styling can
          never drift from the rest of the app again. */}
      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'users' | 'profile' | 'printer')}>
        <TabsList>
          <TabsTrigger value="users">
            <Shield className="h-4 w-4" strokeWidth={3} aria-hidden="true" />
            Manajemen Pengguna
          </TabsTrigger>
          <TabsTrigger value="profile">
            <User className="h-4 w-4" strokeWidth={3} aria-hidden="true" />
            Profil Saya
          </TabsTrigger>
          <TabsTrigger value="printer">
            <Printer className="h-4 w-4" strokeWidth={3} aria-hidden="true" />
            Printer
          </TabsTrigger>
        </TabsList>
      </Tabs>

      {activeTab === 'users' && renderUserManagement()}
      {activeTab === 'profile' && renderProfile()}
      {activeTab === 'printer' && renderPrinter()}

      {/* Deactivate Confirmation Dialog */}
      <ConfirmDialog
        open={!!confirmDeactivate}
        onClose={() => setConfirmDeactivate(null)}
        onConfirm={() => confirmDeactivate && deleteMutation.mutate(confirmDeactivate)}
        title="Nonaktifkan Pengguna?"
        description="Akun pengguna akan dinonaktifkan dan tidak bisa lagi masuk ke sistem. Akun bisa diaktifkan kembali nanti bila diperlukan."
        confirmLabel="Nonaktifkan Pengguna"
        variant="destructive"
        loading={deleteMutation.isPending}
      />
    </div>
  )
}

function UserForm({ user, onSubmit, onClose, isLoading }: any) {
  const [formData, setFormData] = useState({
    username: user?.username || '',
    email: user?.email || '',
    full_name: user?.full_name || '',
    role: user?.role || 'STAFF',
    password: '',
    active: user?.active ?? true,
  })

  return (
    <form onSubmit={(e) => { e.preventDefault(); onSubmit(formData) }} className="space-y-4">
      <div className="space-y-4 rounded-md border-2 border-ink bg-muted p-4">
        <p className="nb-label text-foreground">Identitas</p>
        <div className="space-y-2">
          <Label htmlFor="username">Nama Pengguna</Label>
          <Input
            id="username"
            value={formData.username}
            onChange={(e) => setFormData((prev: any) => ({ ...prev, username: e.target.value }))}
            required
            disabled={!!user?.id}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            value={formData.email}
            onChange={(e) => setFormData((prev: any) => ({ ...prev, email: e.target.value }))}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="full_name">Nama Lengkap</Label>
          <Input
            id="full_name"
            value={formData.full_name}
            onChange={(e) => setFormData((prev: any) => ({ ...prev, full_name: e.target.value }))}
          />
        </div>
      </div>

      <div className="space-y-4 rounded-md border-2 border-ink bg-muted p-4">
        <p className="nb-label text-foreground">Akses</p>
        <div className="space-y-2">
          <Label htmlFor="role">Peran</Label>
          <Select
            value={formData.role}
            onValueChange={(v) => setFormData((prev: any) => ({ ...prev, role: v }))}
          >
            <SelectItem value="ADMIN">Admin</SelectItem>
            <SelectItem value="GUARD">Satpam</SelectItem>
            <SelectItem value="STAFF">Staf</SelectItem>
          </Select>
        </div>
        {user?.id ? (
          <div className="space-y-2">
            <Label htmlFor="password">Kata Sandi Baru (kosongkan untuk memakai yang lama)</Label>
            <Input
              id="password"
              type="password"
              value={formData.password}
              onChange={(e) => setFormData((prev: any) => ({ ...prev, password: e.target.value }))}
              placeholder="••••••••"
            />
          </div>
        ) : (
          <div className="space-y-2">
            <Label htmlFor="password">Kata Sandi</Label>
            <Input
              id="password"
              type="password"
              value={formData.password}
              onChange={(e) => setFormData((prev: any) => ({ ...prev, password: e.target.value }))}
              required
            />
          </div>
        )}
      </div>

      <DialogFooter>
        <Button type="button" variant="outline" onClick={onClose}>Batal</Button>
        <Button type="submit" disabled={isLoading}>
          {isLoading ? 'Menyimpan...' : user?.id ? 'Perbarui' : 'Buat'}
        </Button>
      </DialogFooter>
    </form>
  )
}

function ProfileSettings({ currentUser, onPasswordChange, isChangingPassword }: any) {
  const [passwords, setPasswords] = useState({ current: '', new: '', confirm: '' })

  const handlePasswordSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (passwords.new !== passwords.confirm) {
      toast.error('Kata sandi tidak cocok')
      return
    }
    if (passwords.new.length < 8) {
      toast.error('Kata sandi minimal 8 karakter')
      return
    }
    onPasswordChange({ current_password: passwords.current, new_password: passwords.new })
    setPasswords({ current: '', new: '', confirm: '' })
  }

  const detailFields = [
    { label: 'Username', value: currentUser?.username },
    { label: 'Email', value: currentUser?.email || 'Belum diisi' },
    { label: 'Nama Lengkap', value: currentUser?.full_name || 'Belum diisi' },
    { label: 'Anggota Sejak', value: formatDateTime(currentUser?.created_at || '') },
    {
      label: 'Login Terakhir',
      value: currentUser?.last_login ? formatDateTime(currentUser.last_login) : 'Belum pernah',
    },
  ]

  return (
    <div className="max-w-2xl space-y-6">
      <Card>
        <CardHeader>
          <p className="nb-label text-foreground">Informasi Profil</p>
          <p className="mt-1 text-sm font-semibold text-muted-foreground">Detail akun Anda</p>
        </CardHeader>
        <CardContent>
          <div className="space-y-4 rounded-md border-2 border-ink bg-muted p-4">
            <div className="grid gap-4 md:grid-cols-2">
              {detailFields.map((field) => (
                <div key={field.label} className="space-y-1.5">
                  <Label>{field.label}</Label>
                  <p className="text-sm font-bold text-foreground">{field.value}</p>
                </div>
              ))}
              <div className="space-y-1.5">
                <Label>Peran</Label>
                <div>
                  <Badge variant={getRoleVariant(currentUser?.role || 'STAFF')}>
                    {currentUser?.role}
                  </Badge>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <p className="nb-label text-foreground">Ubah Kata Sandi</p>
          <p className="mt-1 text-sm font-semibold text-muted-foreground">
            Perbarui kata sandi akun Anda
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handlePasswordSubmit} className="space-y-4">
            <div className="space-y-4 rounded-md border-2 border-ink bg-muted p-4">
              <div className="space-y-2">
                <Label htmlFor="current_password">Kata Sandi Saat Ini</Label>
                <Input
                  id="current_password"
                  type="password"
                  value={passwords.current}
                  onChange={(e) => setPasswords((prev) => ({ ...prev, current: e.target.value }))}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="new_password">Kata Sandi Baru</Label>
                <Input
                  id="new_password"
                  type="password"
                  value={passwords.new}
                  onChange={(e) => setPasswords((prev) => ({ ...prev, new: e.target.value }))}
                  required
                  minLength={8}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirm_password">Konfirmasi Kata Sandi Baru</Label>
                <Input
                  id="confirm_password"
                  type="password"
                  value={passwords.confirm}
                  onChange={(e) => setPasswords((prev) => ({ ...prev, confirm: e.target.value }))}
                  required
                />
              </div>
            </div>
            <Button type="submit" disabled={isChangingPassword} className="w-full sm:w-auto">
              {isChangingPassword ? 'Changing...' : 'Change Password'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

function getRoleVariant(role: UserRole): 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning' {
  switch (role) {
    case 'ADMIN': return 'destructive'
    case 'GUARD': return 'warning'
    case 'STAFF': return 'default'
    default: return 'outline'
  }
}