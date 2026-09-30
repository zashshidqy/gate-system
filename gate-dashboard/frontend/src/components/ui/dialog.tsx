import * as React from 'react'
import { cn } from '../../utils/helpers'

interface DialogProps extends React.HTMLAttributes<HTMLDivElement> {
  open: boolean
  onOpenChange: (open: boolean) => void
  size?: 'sm' | 'md' | 'lg'
  children: React.ReactNode
}

const SIZES = {
  sm: 'sm:max-w-sm',
  md: 'sm:max-w-md',
  lg: 'sm:max-w-lg',
} as const

/**
 * Owns the only overlay + card in a modal.
 *
 * `DialogContent` is deliberately a plain layout div: it used to render a
 * second `fixed inset-0` overlay and a second `nb-card`, so every call site
 * that nested the two inside `Dialog` ended up double-wrapped and knocked out
 * of centre. Wrap content in `DialogContent`, but let `Dialog` do the overlay.
 */
const Dialog = React.forwardRef<HTMLDivElement, DialogProps>(
  ({ className, children, open, onOpenChange, size = 'lg', ...props }, ref) => {
    React.useEffect(() => {
      if (!open) return
      const onKey = (e: KeyboardEvent) => {
        if (e.key === 'Escape') onOpenChange(false)
      }
      document.addEventListener('keydown', onKey)
      return () => document.removeEventListener('keydown', onKey)
    }, [open, onOpenChange])

    if (!open) return null
    return (
      <div className="fixed inset-0 z-50 overflow-y-auto p-4">
        <div
          ref={ref}
          className={cn('flex min-h-full items-center justify-center', className)}
          {...props}
        >
          <div className="fixed inset-0 bg-ink/70" onClick={() => onOpenChange(false)} />
          <div
            role="dialog"
            aria-modal="true"
            className={cn(
              'nb-card relative z-50 w-full bg-card p-6 shadow-nb-lg',
              SIZES[size]
            )}
          >
            {children}
          </div>
        </div>
      </div>
    )
  }
)
Dialog.displayName = 'Dialog'

const DialogContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => (
    <div ref={ref} className={cn(className)} {...props}>
      {children}
    </div>
  )
)
DialogContent.displayName = 'DialogContent'

// `title` is omitted from the base attributes: the native `title?: string`
// attribute clashes with the heading we want to accept as a node.
interface DialogHeaderProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  icon?: React.ReactNode
  tone?: string
  title: React.ReactNode
  description?: React.ReactNode
  right?: React.ReactNode
}

/**
 * Canonical modal header: a fixed-size icon tile optically centred against a
 * flex-1 title block, so every popup lines its icon and copy up the same way.
 * Full-bleed and sticky, so the heading survives scrolling in tall forms.
 */
const DialogHeader = React.forwardRef<HTMLDivElement, DialogHeaderProps>(
  ({ className, icon, tone = 'bg-nb-yellow', title, description, right, children, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'sticky top-0 z-10 -mx-6 -mt-6 mb-5 flex items-center gap-3 border-b-2 border-ink bg-card px-6 py-4',
        className
      )}
      {...props}
    >
      {icon ? (
        <span
          className={cn(
            'flex h-11 w-11 shrink-0 items-center justify-center rounded-md border-2 border-ink text-ink shadow-nb-sm',
            tone
          )}
        >
          {icon}
        </span>
      ) : null}
      <div className="min-w-0 flex-1">
        <DialogTitle>{title}</DialogTitle>
        {description ? <DialogDescription className="mt-1">{description}</DialogDescription> : null}
        {children}
      </div>
      {right ? <div className="shrink-0">{right}</div> : null}
    </div>
  )
)
DialogHeader.displayName = 'DialogHeader'

const DialogTitle = React.forwardRef<HTMLHeadingElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h2
      ref={ref}
      className={cn('truncate text-2xl font-extrabold uppercase leading-tight tracking-tight', className)}
      {...props}
    />
  )
)
DialogTitle.displayName = 'DialogTitle'

const DialogDescription = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <p ref={ref} className={cn('text-sm font-semibold leading-snug text-muted-foreground', className)} {...props} />
  )
)
DialogDescription.displayName = 'DialogDescription'

/**
 * Canonical modal footer: a rule above the actions, and `flex-1` on direct
 * button children so a cancel/confirm pair is always the same width instead
 * of sizing itself to its label. Overridable via `className` (e.g. a
 * `grid grid-cols-2` block for four actions, where `flex-1` is inert).
 */
const DialogFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'mt-5 flex flex-col-reverse gap-3 border-t-2 border-ink pt-4 sm:flex-row sm:justify-end sm:[&>button]:flex-1',
        className
      )}
      {...props}
    />
  )
)
DialogFooter.displayName = 'DialogFooter'

export { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter }
