import { cn } from '../../utils/helpers'

function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('animate-pulse rounded-md border-2 border-ink/20 bg-muted', className)}
      {...props}
    />
  )
}

export { Skeleton }
