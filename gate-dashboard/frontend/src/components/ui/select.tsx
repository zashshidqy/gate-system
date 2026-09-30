import * as React from 'react'
import { cn } from '../../utils/helpers'

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  onValueChange?: (value: string) => void
}

const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, children, onValueChange, value, ...props }, ref) => (
    <select
      ref={ref}
      className={cn(
        'flex h-11 w-full items-center justify-between rounded-md border-2 border-ink bg-card px-3 py-2 text-sm font-bold text-foreground',
        'focus-visible:outline-none focus-visible:ring-0 disabled:cursor-not-allowed disabled:opacity-50',
        '[&>option]:bg-card [&>option]:text-foreground [&>option]:font-semibold',
        className
      )}
      onChange={(e) => onValueChange?.(e.target.value)}
      value={value}
      {...props}
    >
      {children}
    </select>
  )
)
Select.displayName = 'Select'

const SelectItem = React.forwardRef<HTMLOptionElement, React.OptionHTMLAttributes<HTMLOptionElement>>(
  ({ className, children, ...props }, ref) => (
    <option ref={ref} className={cn('relative select-none font-semibold', className)} {...props}>
      {children}
    </option>
  )
)
SelectItem.displayName = 'SelectItem'

export { Select, SelectItem }
