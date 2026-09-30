import * as React from 'react'
import type { LucideIcon } from 'lucide-react'
import { cn } from '../../utils/helpers'
import { Card, CardContent } from './card'
import { Skeleton } from './skeleton'

/**
 * The one KPI/stat tile used by every page.
 *
 * It used to be copy-pasted three times (Dashboard, Tickets, RFID) and the
 * copies drifted: the icon sat on different sides, the tile was 36px in one
 * place and 44px in another, and the label/value order was inverted between
 * pages. More importantly, because the label was allowed to grow, a two-line
 * label pushed its value down and the numbers in a row stopped sharing a
 * baseline. Here the label is clamped to two lines inside a row that is
 * already as tall as the icon tile, so the value below always starts on the
 * same line no matter how the label wraps.
 */

function clampPct(value: number): number {
  if (!Number.isFinite(value)) return 0
  return Math.min(100, Math.max(0, value))
}

export interface StatCardProps {
  label: string
  value: React.ReactNode
  /** Small uppercase line under the value. */
  hint?: string
  icon: LucideIcon
  /** Flat fill for the icon tile, e.g. `nbFill.green`. */
  fill: string
  loading?: boolean
  /** 0-100 bar rendered under the value. */
  meter?: number
  meterFill?: string
  /** Render the value as text (e.g. "14:00") at a smaller size. */
  isText?: boolean
  className?: string
}

export function StatCard({
  label,
  value,
  hint,
  icon: Icon,
  fill,
  loading,
  meter,
  meterFill,
  isText,
  className,
}: StatCardProps) {
  return (
    <Card className={cn('nb-card-hover h-full overflow-hidden', className)}>
      <CardContent className="flex h-full flex-col p-5">
        {/* min-h matches the tile, so a wrapped label never shoves the value down */}
        <div className="flex min-h-[2.75rem] items-start justify-between gap-3">
          <p className="nb-label line-clamp-2 flex-1 text-muted-foreground">{label}</p>
          <span
            className={cn(
              'flex h-11 w-11 shrink-0 items-center justify-center rounded-md border-2 border-ink text-ink shadow-nb-sm',
              fill,
            )}
          >
            <Icon className="h-5 w-5" strokeWidth={3} aria-hidden="true" />
          </span>
        </div>

        {/* min-h keeps every value in a row on a shared top edge */}
        <div className="mt-3 flex min-h-[2.5rem] items-start">
          {loading ? (
            <Skeleton className="h-8 w-24" />
          ) : (
            <p
              className={cn(
                'font-extrabold leading-none tabular-nums',
                isText ? 'text-2xl' : 'text-3xl',
              )}
            >
              {value ?? 0}
            </p>
          )}
        </div>

        {meter !== undefined && <Meter value={meter} fillClass={meterFill} className="mt-3" />}

        {hint ? (
          <p className="mt-2 text-xs font-bold uppercase text-muted-foreground">{hint}</p>
        ) : null}
      </CardContent>
    </Card>
  )
}

/** Chunky bordered progress bar — no gradients, no translucency. */
export function Meter({
  value,
  fillClass,
  className,
}: {
  value: number
  fillClass?: string
  className?: string
}) {
  return (
    <div className={cn('h-3 rounded-md border-2 border-ink bg-muted', className)}>
      <div
        className={cn('h-full rounded-[2px] transition-all duration-500', fillClass ?? 'bg-nb-yellow')}
        style={{ width: `${clampPct(value)}%` }}
      />
    </div>
  )
}
