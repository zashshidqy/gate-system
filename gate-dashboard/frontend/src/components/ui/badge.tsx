import * as React from 'react'
import { cn } from '../../utils/helpers'

interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?:
    | 'default'
    | 'secondary'
    | 'destructive'
    | 'outline'
    | 'success'
    | 'warning'
    | 'info'
    | 'purple'
}

const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant = 'default', ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'nb-label inline-flex items-center gap-1 rounded-md border-2 border-ink px-2.5 py-1',
          {
            'bg-primary text-primary-foreground': variant === 'default',
            'bg-secondary text-secondary-foreground': variant === 'secondary',
            'bg-destructive text-destructive-foreground': variant === 'destructive',
            'bg-success text-success-foreground': variant === 'success',
            'bg-warning text-warning-foreground': variant === 'warning',
            'bg-info text-info-foreground': variant === 'info',
            'bg-nb-purple text-ink': variant === 'purple',
            'bg-card text-foreground': variant === 'outline',
          },
          className
        )}
        {...props}
      />
    )
  }
)
Badge.displayName = 'Badge'

export { Badge }
