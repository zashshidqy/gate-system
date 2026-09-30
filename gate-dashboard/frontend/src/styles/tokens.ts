/**
 * Neobrutalist design tokens.
 *
 * Rules of the style, encoded here so pages stay consistent:
 *   1. Every surface is a flat, saturated fill — never a gradient.
 *   2. Every surface is outlined with `border-2 border-ink`.
 *   3. Every raised surface drops a hard offset shadow (`shadow-nb`).
 *   4. Text on any accent fill is always ink-coloured for max contrast.
 */

export type Accent =
  | 'yellow'
  | 'blue'
  | 'green'
  | 'red'
  | 'orange'
  | 'purple'
  | 'cyan'
  | 'pink'

/** Flat fill + matching outline for each accent. */
export const nb = {
  yellow: 'bg-nb-yellow border-ink',
  blue: 'bg-nb-blue border-ink',
  green: 'bg-nb-green border-ink',
  red: 'bg-nb-red border-ink',
  orange: 'bg-nb-orange border-ink',
  purple: 'bg-nb-purple border-ink',
  cyan: 'bg-nb-cyan border-ink',
  pink: 'bg-nb-pink border-ink',
} as const satisfies Record<Accent, string>

/** Bare fill, for use inside an already-outlined box. */
export const nbFill = {
  yellow: 'bg-nb-yellow',
  blue: 'bg-nb-blue',
  green: 'bg-nb-green',
  red: 'bg-nb-red',
  orange: 'bg-nb-orange',
  purple: 'bg-nb-purple',
  cyan: 'bg-nb-cyan',
  pink: 'bg-nb-pink',
} as const satisfies Record<Accent, string>

/** Semantic aliases used across pages, so meaning stays consistent. */
export const accents = {
  primary: 'yellow',
  success: 'green',
  danger: 'red',
  warning: 'orange',
  info: 'cyan',
  entry: 'blue',
  exit: 'green',
  rfid: 'purple',
  ticket: 'pink',
  anpr: 'cyan',
  qr: 'blue',
  manual: 'orange',
} as const satisfies Record<string, Accent>

/* -------------------------------------------------------------------------- */
/*  Badge presets                                                              */
/* -------------------------------------------------------------------------- */

export const badge = {
  entry: 'bg-nb-blue text-ink border-ink',
  exit: 'bg-nb-green text-ink border-ink',
  success: 'bg-nb-green text-ink border-ink',
  danger: 'bg-nb-red text-ink border-ink',
  warning: 'bg-nb-orange text-ink border-ink',
  info: 'bg-nb-cyan text-ink border-ink',
  neutral: 'bg-muted text-ink border-ink',
  primary: 'bg-nb-yellow text-ink border-ink',
} as const

/* -------------------------------------------------------------------------- */
/*  Icon tiles — square, hard-bordered, flat fill                            */
/* -------------------------------------------------------------------------- */

export const tile = {
  yellow: 'bg-nb-yellow border-ink',
  blue: 'bg-nb-blue border-ink',
  green: 'bg-nb-green border-ink',
  red: 'bg-nb-red border-ink',
  orange: 'bg-nb-orange border-ink',
  purple: 'bg-nb-purple border-ink',
  cyan: 'bg-nb-cyan border-ink',
  pink: 'bg-nb-pink border-ink',
} as const satisfies Record<Accent, string>

/* -------------------------------------------------------------------------- */
/*  Helpers                                                                    */
/* -------------------------------------------------------------------------- */

/**
 * Display labels.
 *
 * These live here, not on each page: the ticket type used to be rendered as
 * `type.replace('_', ' ')` in the table (so "SINGLE ENTRY" appeared in the
 * table while the same filter dropdown said "Sekali Masuk"). One map, one
 * spelling, everywhere.
 */
const METHOD_LABEL: Record<string, string> = {
  RFID: 'Kartu RFID',
  ANPR: 'ANPR / Plat',
  QR: 'Scan QR',
  MANUAL: 'Manual',
}

const TICKET_LABEL: Record<string, string> = {
  SINGLE_ENTRY: 'Sekali Masuk',
  MULTI_DAY: 'Multi Hari',
  VIP: 'VIP',
  STAFF: 'Staf',
}

/** Map an access method to its accent colour. */
export function getMethodAccent(method: string): Accent {
  const m = method.toUpperCase()
  if (m.includes('RFID')) return accents.rfid
  if (m.includes('ANPR')) return accents.anpr
  if (m.includes('QR')) return accents.qr
  if (m.includes('MANUAL')) return accents.manual
  return 'blue'
}

/** Indonesian display label for an access method. */
export function getMethodLabel(method: string): string {
  return METHOD_LABEL[method.toUpperCase()] ?? method
}

/** Ready-made badge class for an access method. */
export function getMethodBadge(method: string): string {
  return nb[getMethodAccent(method)]
}

/** Map a ticket type to its accent colour. */
export function getTicketAccent(type: string): Accent {
  switch (type) {
    case 'SINGLE_ENTRY':
      return 'cyan'
    case 'MULTI_DAY':
      return 'purple'
    case 'VIP':
      return 'yellow'
    case 'STAFF':
      return 'green'
    default:
      return 'blue'
  }
}

/** Indonesian display label for a ticket type. */
export function getTicketLabel(type: string): string {
  return TICKET_LABEL[type] ?? type.replace(/_/g, ' ')
}

/** Ready-made badge class for a ticket type. */
export function getTicketBadge(type: string): string {
  return nb[getTicketAccent(type)]
}
