import * as React from 'react'
import { cn } from '../../utils/helpers'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link'
  size?: 'default' | 'sm' | 'lg' | 'icon'
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', ...props }, ref) => {
    return (
      <button
        className={cn(
          // Neobrutalism: hard ink border + offset shadow, slams down on press
          'nb-press inline-flex items-center justify-center gap-2 whitespace-nowrap border-2 border-ink font-bold uppercase tracking-wide',
          'focus-visible:outline-none focus-visible:ring-0 disabled:pointer-events-none disabled:opacity-50',
          {
            'bg-primary text-primary-foreground shadow-nb hover:shadow-nb-lg':
              variant === 'default',
            'bg-destructive text-destructive-foreground shadow-nb hover:shadow-nb-lg':
              variant === 'destructive',
            'bg-secondary text-secondary-foreground shadow-nb hover:shadow-nb-lg':
              variant === 'secondary',
            'bg-card text-foreground shadow-nb hover:shadow-nb-lg':
              variant === 'outline',
            'bg-transparent text-foreground hover:bg-muted': variant === 'ghost',
            'border-0 bg-transparent p-0 shadow-none hover:underline': variant === 'link',
            'h-11 px-5 text-sm': size === 'default',
            'h-9 px-3 text-xs': size === 'sm',
            'h-12 px-7 text-base': size === 'lg',
            'h-11 w-11': size === 'icon',
          },
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = 'Button'

export { Button }
