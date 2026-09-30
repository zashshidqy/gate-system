import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { formatDateTime } from '../utils/helpers'
import { Card, CardHeader, CardContent } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../components/ui/table'
import { Dialog, DialogHeader, DialogContent, DialogFooter } from '../components/ui/dialog'
import { Select, SelectItem } from '../components/ui/select'
import { Plus, Search, Edit, Trash2, Shield, User, UserX, UserPlus } from 'lucide-react'
import { User as UserType, UserRole } from '../types'
import toast from 'react-hot-toast'
import { useAuth } from '../context/AuthContext'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { Pagination } from '../components/ui/pagination'
import { Tabs, TabsList, TabsTrigger } from '../components/ui/tabs'

export function Settings() {
  const { user: currentUser } = useAuth()
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState<UserRole | ''>('')
  const [activeFilter, setActiveFilter] = useState<boolean | ''>('')
  const [showForm, setShowForm] = useState<UserType | null>(null)
  const [activeTab, setActiveTab] = useState<'users' | 'profile'>('users')
  const [confirmDeactivate, setConfirmDeactivate] = useState<string | null>(null)

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

  return (
    <div className="space-y-6">
      {/* Tab Navigation — uses the shared Tabs so the trigger styling can
          never drift from the rest of the app again. */}
      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'users' | 'profile')}>
        <TabsList>
          <TabsTrigger value="users">
            <Shield className="h-4 w-4" strokeWidth={3} aria-hidden="true" />
            Manajemen Pengguna
          </TabsTrigger>
          <TabsTrigger value="profile">
            <User className="h-4 w-4" strokeWidth={3} aria-hidden="true" />
            Profil Saya
          </TabsTrigger>
        </TabsList>
      </Tabs>

      {activeTab === 'users' && renderUserManagement()}
      {activeTab === 'profile' && renderProfile()}

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
