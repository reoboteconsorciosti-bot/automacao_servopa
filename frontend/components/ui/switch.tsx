'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

interface SwitchProps {
  checked: boolean
  onCheckedChange: (checked: boolean) => void
  disabled?: boolean
  id?: string
  className?: string
  'aria-label'?: string
}

function Switch({ checked, onCheckedChange, disabled, id, className, ...props }: SwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      id={id}
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onCheckedChange(!checked)}
      className={cn(
        'inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full border border-transparent transition-colors outline-none',
        'focus-visible:ring-3 focus-visible:ring-ring/40',
        'disabled:cursor-not-allowed disabled:opacity-50',
        checked ? 'bg-primary' : 'bg-input',
        className,
      )}
      {...props}
    >
      <span
        className={cn(
          'pointer-events-none block size-4 rounded-full bg-background shadow-sm transition-transform',
          checked ? 'translate-x-4' : 'translate-x-0.5',
        )}
      />
    </button>
  )
}

export { Switch }
