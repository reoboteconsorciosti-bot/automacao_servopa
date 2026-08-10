import * as React from 'react'
import { cn } from '@/lib/utils'

function Textarea({ className, ...props }: React.ComponentProps<'textarea'>) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        'flex min-h-[220px] w-full rounded-xl border border-input bg-muted/20 px-4 py-3 text-sm shadow-xs transition-colors outline-none resize-y',
        'placeholder:text-muted-foreground',
        'focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/30',
        'disabled:cursor-not-allowed disabled:opacity-50',
        'aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20',
        className,
      )}
      {...props}
    />
  )
}

export { Textarea }
