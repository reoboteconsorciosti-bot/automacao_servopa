import { CheckCircle2, CircleDashed, Loader2, XCircle } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { AutomationStatusValue } from '@/types'

const statusConfig: Record<
  AutomationStatusValue,
  { label: string; description: string; variant: 'neutral' | 'default' | 'success' | 'destructive'; icon: typeof CircleDashed; spin?: boolean }
> = {
  idle: {
    label: 'Aguardando execução',
    description: 'A automação está pronta para ser iniciada.',
    variant: 'neutral',
    icon: CircleDashed,
  },
  running: {
    label: 'Executando',
    description: 'A automação está em andamento.',
    variant: 'default',
    icon: Loader2,
    spin: true,
  },
  finished: {
    label: 'Finalizado',
    description: 'A automação foi concluída com sucesso.',
    variant: 'success',
    icon: CheckCircle2,
  },
  error: {
    label: 'Erro',
    description: 'Ocorreu um erro durante a execução.',
    variant: 'destructive',
    icon: XCircle,
  },
}

export function StatusIndicator({ status }: { status: AutomationStatusValue }) {
  const config = statusConfig[status]
  const Icon = config.icon

  return (
    <div className="flex items-center gap-4">
      <div
        className={cn(
          'flex size-11 shrink-0 items-center justify-center rounded-full',
          status === 'idle' && 'bg-muted text-muted-foreground',
          status === 'running' && 'bg-primary/10 text-primary',
          status === 'finished' && 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
          status === 'error' && 'bg-destructive/10 text-destructive',
        )}
      >
        <Icon className={cn('size-5', config.spin && 'animate-spin')} />
      </div>
      <div className="flex flex-col gap-1">
        <Badge variant={config.variant} className="w-fit">
          {config.label}
        </Badge>
        <p className="text-sm text-muted-foreground">{config.description}</p>
      </div>
    </div>
  )
}
