import { MonitorPlay, WifiOff } from 'lucide-react'
import type { AutomationStatusValue } from '@/types'

interface LiveViewProps {
  status: AutomationStatusValue
  frame: string | null
  connected: boolean
}

export function LiveView({ status, frame, connected }: LiveViewProps) {
  const isRunning = status === 'running'

  return (
    <div className="relative flex aspect-video w-full flex-col items-center justify-center gap-4 overflow-hidden rounded-lg border border-dashed border-border bg-muted/40 p-6 text-center">
      <div className="absolute left-3 top-3 z-10 flex items-center gap-2 rounded-md bg-background/80 px-2.5 py-1 text-xs font-medium text-muted-foreground">
        <span
          className={
            isRunning && connected
              ? 'size-2 animate-pulse rounded-full bg-emerald-500'
              : 'size-2 rounded-full bg-muted-foreground/40'
          }
        />
        {isRunning ? (connected ? 'Transmitindo' : 'Conectando...') : 'Offline'}
      </div>

      {frame ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={frame}
          alt="Tela do navegador da automação em execução"
          className="absolute inset-0 size-full object-contain bg-black"
        />
      ) : (
        <div className="flex flex-col items-center gap-3">
          <div className="flex size-14 items-center justify-center rounded-full bg-background text-muted-foreground shadow-xs">
            {isRunning ? (
              <MonitorPlay className="size-7" />
            ) : (
              <WifiOff className="size-7" />
            )}
          </div>
          <div className="flex max-w-sm flex-col gap-1">
            <p className="text-sm font-medium">Visualização da automação</p>
            <p className="text-sm text-muted-foreground text-pretty">
              {isRunning
                ? 'Aguardando o primeiro frame do navegador...'
                : 'Inicie a automação para acompanhar a execução em tempo real.'}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
