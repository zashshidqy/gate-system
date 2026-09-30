import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '../api/client'
import { cn, formatDateTime } from '../utils/helpers'
import { Card, CardContent } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../components/ui/table'
import { Select, SelectItem } from '../components/ui/select'
import { badge, getMethodBadge, getMethodLabel, tile } from '../styles/tokens'
import {
  Search,
  Download,
  X,
  Filter,
  CalendarDays,
  LogIn,
  LogOut,
  ShieldCheck,
  ShieldX,
  Inbox,
} from 'lucide-react'
import { format, subDays, startOfDay, endOfDay } from 'date-fns'
import { PaginatedResponse, Passage } from '../types'
import toast from 'react-hot-toast'
import { useDebounce } from '../hooks/useDebounce'
import { Pagination } from '../components/ui/pagination'
export function Passages() {
  const [page, setPage] = useState(1)
  const [searchInput, setSearchInput] = useState('')
  const debouncedSearch = useDebounce(searchInput, 300)
  const [directionFilter, setDirectionFilter] = useState<'ENTRY' | 'EXIT' | ''>('')
  const [methodFilter, setMethodFilter] = useState<'RFID' | 'ANPR' | 'MANUAL' | 'QR' | ''>('')
  const [allowedFilter, setAllowedFilter] = useState<boolean | ''>('')
  const [dateFrom, setDateFrom] = useState<string>('')
  const [dateTo, setDateTo] = useState<string>('')
  const { data, isLoading } = useQuery({
    queryKey: ['passages', page, debouncedSearch, directionFilter, methodFilter, allowedFilter, dateFrom, dateTo],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '50',
      })
      if (debouncedSearch) params.append('search', debouncedSearch)
      if (directionFilter) params.append('direction', directionFilter)
      if (methodFilter) params.append('method', methodFilter)
      if (allowedFilter !== '') params.append('allowed', allowedFilter.toString())
      if (dateFrom) params.append('date_from', dateFrom)
      if (dateTo) params.append('date_to', dateTo)
      const response = await api.get<PaginatedResponse<Passage>>(`/passages?${params}`)
      return response.data
    },
  })
  const exportMutation = useMutation({
    mutationFn: (params: URLSearchParams) => api.get(`/passages/export/csv?${params}`, { responseType: 'blob' }),
    onSuccess: (blob) => {
      const url = window.URL.createObjectURL(blob.data)
      const link = document.createElement('a')
      link.href = url
      link.download = `passages_${format(new Date(), 'yyyyMMdd_HHmmss')}.csv`
      link.click()
      window.URL.revokeObjectURL(url)
      toast.success('Data berhasil diunduh')
    },
    onError: () => toast.error('Gagal mengunduh data'),
  })
  const handleExport = () => {
    const params = new URLSearchParams()
    if (debouncedSearch) params.append('search', debouncedSearch)
    if (directionFilter) params.append('direction', directionFilter)
    if (methodFilter) params.append('method', methodFilter)
    if (allowedFilter !== '') params.append('allowed', allowedFilter.toString())
    if (dateFrom) params.append('date_from', dateFrom)
    if (dateTo) params.append('date_to', dateTo)
    exportMutation.mutate(params)
  }
  const quickDates = [
    { label: 'Today', from: format(startOfDay(new Date()), 'yyyy-MM-dd'), to: format(endOfDay(new Date()), 'yyyy-MM-dd') },
    { label: 'Last 7 Days', from: format(startOfDay(subDays(new Date(), 6)), 'yyyy-MM-dd'), to: format(endOfDay(new Date()), 'yyyy-MM-dd') },
    { label: 'Last 30 Days', from: format(startOfDay(subDays(new Date(), 29)), 'yyyy-MM-dd'), to: format(endOfDay(new Date()), 'yyyy-MM-dd') },
  ]
  const hasFilters =
    !!searchInput ||
    !!directionFilter ||
    !!methodFilter ||
    allowedFilter !== '' ||
    !!dateFrom ||
    !!dateTo
  const resetFilters = () => {
    setSearchInput('')
    setDirectionFilter('')
    setMethodFilter('')
    setAllowedFilter('')
    setDateFrom('')
    setDateTo('')
    setPage(1)
  }
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-4xl font-extrabold uppercase tracking-tight sm:text-5xl">
            Passage History
          </h1>
          <p className="mt-2 text-sm font-semibold text-muted-foreground">
            View and export gate passage records
          </p>
        </div>
        <Button onClick={handleExport} disabled={exportMutation.isPending} className="gap-2">
          <Download className="h-4 w-4" />
          Export CSV
        </Button>
      </div>
      {/* Quick Date Filters */}
      <Card className="border-2 border-ink bg-muted">
        <CardContent className="p-4 pt-4 sm:p-4 sm:pt-4">
          <div className="flex flex-wrap items-center gap-3">
            <span className="nb-label inline-flex items-center gap-2 text-muted-foreground">
              <CalendarDays className="h-4 w-4 text-ink" />
              Quick Range
            </span>
            {quickDates.map((d) => (
              <Button
                key={d.label}
                variant="outline"
                size="sm"
                onClick={() => { setDateFrom(d.from); setDateTo(d.to) }}
                className={cn(
                  'bg-nb-cyan text-ink',
                  dateFrom === d.from && dateTo === d.to && 'bg-nb-yellow'
                )}
              >
                {d.label}
              </Button>
            ))}
            <Button
              variant="outline"
              size="sm"
              onClick={() => { setDateFrom(''); setDateTo('') }}
              className="gap-1 bg-nb-red text-ink"
            >
              <X className="h-3 w-3" />
              Clear
            </Button>
          </div>
        </CardContent>
      </Card>
      {/* Filters */}
      <Card>
        <CardContent className="p-4 pt-4 sm:p-4 sm:pt-4">
          <div className="mb-4 flex items-center gap-3">
            <span className="nb-label inline-flex items-center gap-2 text-muted-foreground">
              <Filter className="h-4 w-4 text-ink" />
              Filter
            </span>
            {hasFilters && (
              <span className="nb-label rounded-md border-2 border-ink bg-nb-yellow px-2 py-0.5 text-ink">
                Aktif
              </span>
            )}
          </div>
          <div className="flex flex-col gap-4">
            <div className="relative min-w-[220px] flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-ink" />
              <Input
                placeholder="Cari UID, plat, catatan..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                className="h-11 pl-11"
              />
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Select
                value={directionFilter}
                onValueChange={(v) => setDirectionFilter(v as 'ENTRY' | 'EXIT' | '')}
                className="w-[150px]"
              >
                <SelectItem value="">Semua Gerbang</SelectItem>
                <SelectItem value="ENTRY">ENTRY</SelectItem>
                <SelectItem value="EXIT">EXIT</SelectItem>
              </Select>
              <Select
                value={methodFilter}
                onValueChange={(v) => setMethodFilter(v as 'RFID' | 'ANPR' | 'MANUAL' | 'QR' | '')}
                className="w-[150px]"
              >
                <SelectItem value="">Semua Metode</SelectItem>
                <SelectItem value="RFID">Kartu RFID</SelectItem>
                <SelectItem value="ANPR">ANPR / Plat</SelectItem>
                <SelectItem value="MANUAL">MANUAL</SelectItem>
                <SelectItem value="QR">Scan QR</SelectItem>
              </Select>
              <Select
                value={allowedFilter === '' ? 'all' : allowedFilter.toString()}
                onValueChange={(v) => setAllowedFilter(v === 'all' ? '' : v === 'true')}
                className="w-[150px]"
              >
                <SelectItem value="all">Semua Status</SelectItem>
                <SelectItem value="true">Diizinkan</SelectItem>
                <SelectItem value="false">Ditolak</SelectItem>
              </Select>
              <div className="flex items-center gap-2">
                <Label htmlFor="passage-from" className="whitespace-nowrap text-muted-foreground">
                  Dari
                </Label>
                <Input
                  id="passage-from"
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="h-11 w-[165px]"
                />
              </div>
              <div className="flex items-center gap-2">
                <Label htmlFor="passage-to" className="whitespace-nowrap text-muted-foreground">
                  Sampai
                </Label>
                <Input
                  id="passage-to"
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="h-11 w-[165px]"
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
      {/* Passages Table */}
      <Card className="overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-ink bg-nb-yellow px-5 py-3">
          <span className="nb-label">Log Lalu Lintas</span>
          <span className="nb-label tabular-nums rounded-md border-2 border-ink bg-card px-2 py-0.5 text-ink">
            {data?.total ?? 0} Baris
          </span>
        </div>
        {isLoading ? (
          <div className="space-y-3 p-6">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-12 animate-pulse border-2 border-ink bg-muted" />
            ))}
          </div>
        ) : data && data.items.length > 0 ? (
          <>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-40">Waktu</TableHead>
                    <TableHead className="w-28">Gerbang</TableHead>
                    <TableHead className="w-28">Metode</TableHead>
                    <TableHead className="w-36">UID</TableHead>
                    <TableHead className="w-32">Plat</TableHead>
                    <TableHead className="w-28 text-center">Status</TableHead>
                    <TableHead>Catatan</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((p) => (
                    <TableRow key={p.id}>
                      <TableCell className="whitespace-nowrap font-mono text-sm font-bold">
                        {formatDateTime(p.ts)}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={cn(p.direction === 'ENTRY' ? badge.entry : badge.exit)}
                        >
                          {p.direction === 'ENTRY' ? (
                            <LogIn className="h-3 w-3" />
                          ) : (
                            <LogOut className="h-3 w-3" />
                          )}
                          {p.direction}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className={getMethodBadge(p.method)}>
                          {getMethodLabel(p.method)}
                        </Badge>
                      </TableCell>
                      <TableCell className="max-w-[200px] truncate font-mono text-sm">
                        {p.uid || '-'}
                      </TableCell>
                      <TableCell className="max-w-[180px] truncate text-sm">{p.plate || '-'}</TableCell>
                      <TableCell className="text-center">
                        <Badge
                          variant="outline"
                          className={cn(p.allowed ? badge.success : badge.danger)}
                        >
                          {p.allowed ? (
                            <ShieldCheck className="h-3 w-3" />
                          ) : (
                            <ShieldX className="h-3 w-3" />
                          )}
                          {p.allowed ? 'Diizinkan' : 'Ditolak'}
                        </Badge>
                      </TableCell>
                      <TableCell className="max-w-[200px] truncate text-sm text-muted-foreground">
                        {p.note || '-'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            {/* Pagination */}
            <Pagination
              variant="strip"
              page={page}
              totalPages={data.total_pages}
              total={data.total}
              perPage={50}
              onPageChange={setPage}
              isLoading={isLoading}
            />
          </>
        ) : (
          /* Empty state */
          <div className="flex flex-col items-center justify-center gap-4 p-12 text-center">
            <div
              className={cn(
                'flex h-20 w-20 items-center justify-center rounded-md border-2 border-ink text-ink shadow-nb',
                tile.cyan
              )}
            >
              <Inbox className="h-9 w-9" />
            </div>
            <div>
              <p className="text-xl font-extrabold uppercase tracking-tight">Tidak ada lalu lintas</p>
              <p className="mt-1 text-sm font-semibold text-muted-foreground">
                Belum ada yang cocok dengan filter ini. Perlebar rentang tanggal atau atur ulang filter.
              </p>
            </div>
            <Button variant="outline" size="sm" onClick={resetFilters} className="gap-1 bg-nb-yellow text-ink">
              <X className="h-3 w-3" />
              Atur Ulang Filter
            </Button>
          </div>
        )}
      </Card>
    </div>
  )
}