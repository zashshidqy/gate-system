import { cn } from '../../utils/helpers'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

export interface TrafficPoint {
  label: string
  count: number
}

/**
 * Hourly passage volume as a stepped area chart.
 *
 * Neobrutalism avoids smooth/soft curves, blur and gradients, so this uses a
 * hard linear interpolation, a thick ink stroke and one flat solid fill — the
 * area under the line is a single colour, not a fade.
 *
 * Lives in its own module so the (large) charting dependency is code-split and
 * only downloaded when the dashboard actually needs to render it.
 */

/** Same ink the rest of the app uses, via the `--ink` custom property. */
const INK = 'hsl(var(--ink))'

export function TrafficChart({
  data,
  className,
}: {
  data: TrafficPoint[]
  /** Pass `h-full` when the parent card stretches, so the plot absorbs the slack. */
  className?: string
}) {
  return (
    <div className={cn('h-72 w-full', className)}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
          <CartesianGrid strokeDasharray="4 4" stroke="hsl(var(--muted-foreground))" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11, fontWeight: 800, fill: INK }}
            tickLine={false}
            axisLine={{ stroke: INK, strokeWidth: 2 }}
            interval="preserveStartEnd"
            minTickGap={24}
          />
          <YAxis
            tick={{ fontSize: 11, fontWeight: 800, fill: INK }}
            tickLine={false}
            axisLine={false}
            allowDecimals={false}
            width={44}
          />
          <Tooltip
            cursor={{ stroke: INK, strokeWidth: 2, strokeDasharray: '4 4' }}
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null
              return (
                <div className="rounded-md border-2 border-ink bg-card px-3 py-2 shadow-nb">
                  <p className="text-[10px] font-extrabold uppercase tracking-wide text-muted-foreground">
                    {label}
                  </p>
                  <p className="mt-1 text-sm font-extrabold uppercase text-ink">
                    {payload[0].value} pelintas
                  </p>
                </div>
              )
            }}
          />
          <Area
            type="linear"
            dataKey="count"
            stroke={INK}
            strokeWidth={3}
            /* Flat solid fill: no <defs>/<linearGradient>, no fade. */
            fill="#FFD83D"
            activeDot={{ r: 6, strokeWidth: 3, stroke: INK, fill: '#FFD83D' }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

export default TrafficChart
