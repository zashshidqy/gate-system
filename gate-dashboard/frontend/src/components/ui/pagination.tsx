import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react'
import { cn } from '../../utils/helpers'
import { Button } from './button'
import { Input } from './input'

/**
 * One pagination bar for every list page.
 *
 * There were three hand-rolled copies (Tickets, RFID, Passages) that had
 * drifted: one sat in a `Card`, one was a raw bordered `div`, one was a flush
 * strip inside the table card. They also mixed control heights — the "First"
 * button was `size="sm"` (h-9) sitting right next to the `size="icon"`
 * chevrons (h-11) in the same row, so the bar was visibly uneven. Here every
 * control is forced to h-11.
 */

export interface PaginationProps {
  page: number
  totalPages: number
  /** Total records across all pages. */
  total: number
  perPage: number
  onPageChange: (page: number) => void
  isLoading?: boolean
  /**
   * `card`  — a standalone raised card, for pages where the list has its own card.
   * `strip` — flush against the bottom edge of the list card, sharing its border.
   */
  variant?: 'card' | 'strip'
  className?: string
}

export function Pagination({
  page,
  totalPages,
  total,
  perPage,
  onPageChange,
  isLoading,
  variant = 'card',
  className,
}: PaginationProps) {
  if (totalPages <= 1) return null

  const from = (page - 1) * perPage + 1
  const to = Math.min(page * perPage, total)
  const busy = isLoading || totalPages === 0

  const surface =
    variant === 'strip'
      ? 'border-t-2 border-ink bg-muted px-5 py-4'
      : 'nb-card-hover border-2 border-ink bg-card p-4'

  return (
    <div className={cn('flex flex-col items-center justify-between gap-4 sm:flex-row', surface, className)}>
      <p className="nb-label text-muted-foreground">
        Menampilkan <span className="font-extrabold tabular-nums text-ink">{from}</span>–
        <span className="font-extrabold tabular-nums text-ink">{to}</span> dari{' '}
        <span className="font-extrabold tabular-nums text-ink">{total}</span>
      </p>

      {/* Every control below is h-11 so the row is flush. */}
      <div className="flex flex-wrap items-center justify-center gap-2">
        <Button
          variant="outline"
          onClick={() => onPageChange(1)}
          disabled={page === 1 || busy}
          className="h-11 gap-1.5 px-4"
          aria-label="Halaman pertama"
        >
          <ChevronsLeft className="h-4 w-4" strokeWidth={3} />
          Awal
        </Button>

        <Button
          variant="outline"
          size="icon"
          onClick={() => onPageChange(Math.max(1, page - 1))}
          disabled={page === 1 || busy}
          aria-label="Halaman sebelumnya"
        >
          <ChevronLeft className="h-4 w-4" strokeWidth={3} />
        </Button>

        <div className="flex items-center gap-2">
          <label htmlFor="pagination-page" className="nb-label text-muted-foreground">
            Hal
          </label>
          <Input
            id="pagination-page"
            type="number"
            inputMode="numeric"
            min={1}
            max={totalPages}
            value={page}
            onChange={(e) => {
              const next = parseInt(e.target.value, 10)
              if (Number.isFinite(next) && next >= 1 && next <= totalPages) onPageChange(next)
            }}
            className="h-11 w-16 text-center font-extrabold"
            aria-label="Ke halaman"
          />
          <span className="nb-label text-muted-foreground">dari {totalPages}</span>
        </div>

        <Button
          variant="outline"
          size="icon"
          onClick={() => onPageChange(Math.min(totalPages, page + 1))}
          disabled={page === totalPages || busy}
          aria-label="Halaman berikutnya"
        >
          <ChevronRight className="h-4 w-4" strokeWidth={3} />
        </Button>

        <Button
          variant="outline"
          onClick={() => onPageChange(totalPages)}
          disabled={page === totalPages || busy}
          className="h-11 gap-1.5 px-4"
          aria-label="Halaman terakhir"
        >
          Akhir
          <ChevronsRight className="h-4 w-4" strokeWidth={3} />
        </Button>
      </div>
    </div>
  )
}
