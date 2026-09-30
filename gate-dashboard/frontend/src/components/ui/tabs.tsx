import * as React from 'react'
import { cn } from '../../utils/helpers'

/**
 * Minimal uncontrolled Tabs built on context.
 *
 * State lives in `Tabs` and is read by every `TabsTrigger`, so a trigger can
 * reliably tell whether it is the selected one. Each panel is only mounted
 * while it is active, so inactive panels cost nothing.
 */
const TabsContext = React.createContext<{
  value: string
  setValue: (value: string) => void
} | null>(null)

function useTabs() {
  const ctx = React.useContext(TabsContext)
  if (!ctx) throw new Error('Tabs sub-components must be rendered inside <Tabs>')
  return ctx
}

interface TabsProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'defaultValue' | 'onChange'> {
  /** Uncontrolled initial value. Ignored when `value` is supplied. */
  defaultValue?: string
  /** Controlled value. Pair with `onValueChange`. */
  value?: string
  onValueChange?: (value: string) => void
}

const Tabs = React.forwardRef<HTMLDivElement, TabsProps>(
  ({ className, defaultValue, value: controlled, onValueChange, children, ...props }, ref) => {
    const [uncontrolled, setUncontrolled] = React.useState(defaultValue ?? '')
    const value = controlled ?? uncontrolled

    const setValue = React.useCallback(
      (next: string) => {
        // A controlled Tabs only reports the change; the owner applies it.
        if (controlled === undefined) setUncontrolled(next)
        onValueChange?.(next)
      },
      [controlled, onValueChange]
    )

    const ctx = React.useMemo(() => ({ value, setValue }), [value, setValue])

    return (
      <TabsContext.Provider value={ctx}>
        <div ref={ref} className={cn('space-y-4', className)} {...props}>
          {children}
        </div>
      </TabsContext.Provider>
    )
  }
)
Tabs.displayName = 'Tabs'

type TabsListProps = React.HTMLAttributes<HTMLDivElement>

const TabsList = React.forwardRef<HTMLDivElement, TabsListProps>(
  ({ className, children, ...props }, ref) => (
    <div
      ref={ref}
      role="tablist"
      className={cn('inline-flex flex-wrap items-center gap-2', className)}
      {...props}
    >
      {children}
    </div>
  )
)
TabsList.displayName = 'TabsList'

interface TabsTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value: string
}

const TabsTrigger = React.forwardRef<HTMLButtonElement, TabsTriggerProps>(
  ({ className, value, children, ...props }, ref) => {
    const { value: active, setValue } = useTabs()
    const isActive = value === active

    return (
      <button
        ref={ref}
        type="button"
        role="tab"
        aria-selected={isActive}
        onClick={() => setValue(value)}
        className={cn(
          'nb-press inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md border-2 border-ink px-4 py-2 text-sm font-extrabold uppercase tracking-wide',
          'focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50',
          isActive
            ? 'bg-primary text-primary-foreground shadow-nb'
            : 'bg-card text-foreground shadow-nb-sm hover:bg-muted',
          className
        )}
        {...props}
      >
        {children}
      </button>
    )
  }
)
TabsTrigger.displayName = 'TabsTrigger'

interface TabsContentProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string
}

const TabsContent = React.forwardRef<HTMLDivElement, TabsContentProps>(
  ({ className, value, children, ...props }, ref) => {
    const { value: active } = useTabs()
    if (value !== active) return null

    return (
      <div ref={ref} role="tabpanel" className={cn('focus-visible:outline-none', className)} {...props}>
        {children}
      </div>
    )
  }
)
TabsContent.displayName = 'TabsContent'

export { Tabs, TabsList, TabsTrigger, TabsContent }
