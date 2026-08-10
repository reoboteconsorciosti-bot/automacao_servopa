import { MonitorPlay } from 'lucide-react'
import type { AutomationStatusValue } from '@/types'

interface LiveViewProps {
  status: AutomationStatusValue
}

export function LiveView({ status }: LiveViewProps) {
  const isRunning = status === 'running'

  return (
    <div className="relative flex aspect-video w-full flex-col items-center justify-center gap-4 overflow-hidden rounded-lg border border-dashed border-border bg-muted/40 p-6 text-center">
      <div className="flex items-center gap-2 self-start rounded-md bg-background/80 px-2.5 py-1 text-xs font-medium text-muted-foreground">
        <span
          className={
            isRunning
              ? 'size-2 animate-pulse rounded-full bg-emerald-500'
              : 'size-2 rounded-full bg-muted-foreground/40'
          }
        />
        {isRunning ? 'Transmitindo' : 'Offline'}
      </div>

      <div className="flex flex-col items-center gap-3">
        <div className="flex size-14 items-center justify-center rounded-full bg-background text-muted-foreground shadow-xs">
          <MonitorPlay className="size-7" />
        </div>
        <div className="flex max-w-sm flex-col gap-1">
          <p className="text-sm font-medium">Visualização da automação</p>
          <p className="text-sm text-muted-foreground text-pretty">
            A transmissão da automação será disponibilizada pelo backend.
          </p>
        </div>
      </div>
    </div>
  )
}
