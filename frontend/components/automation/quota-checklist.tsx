import { CheckCircle2, CircleDashed, Loader2, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { QuotaProgressItem, QuotaProgressStatus } from '@/types'

interface QuotaChecklistProps {
  items: QuotaProgressItem[]
}

function statusIcon(status: QuotaProgressStatus) {
  switch (status) {
    case 'SUCESSO':
      return <CheckCircle2 className="size-4 shrink-0 text-emerald-500" />
    case 'ERRO_BENIGNO':
    case 'ERRO_CRITICO':
    case 'invalido':
      return <XCircle className="size-4 shrink-0 text-destructive" />
    case 'processando':
      return <Loader2 className="size-4 shrink-0 animate-spin text-primary" />
    case 'pendente':
    default:
      return <CircleDashed className="size-4 shrink-0 text-muted-foreground/50" />
  }
}

function statusLabel(status: QuotaProgressStatus) {
  switch (status) {
    case 'SUCESSO':
      return 'Concluído'
    case 'ERRO_BENIGNO':
      return 'Não processado'
    case 'ERRO_CRITICO':
      return 'Erro'
    case 'invalido':
      return 'Formato inválido'
    case 'processando':
      return 'Processando...'
    case 'pendente':
    default:
      return 'Pendente'
  }
}

export function QuotaChecklist({ items }: QuotaChecklistProps) {
  if (items.length === 0) return null

  const doneCount = items.filter((i) => i.status === 'SUCESSO').length

  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm font-medium tabular-nums text-muted-foreground">
        Progresso: <span className="text-primary">{doneCount}</span> / {items.length} concluídas
      </p>
      <ul className="flex flex-col gap-1.5 rounded-lg border border-border bg-muted/30 p-3">
        {items.map((item, idx) => (
          <li
            key={`${item.quota}-${idx}`}
            className="flex items-center justify-between gap-2 text-sm"
            title={item.message ?? undefined}
          >
            <span
              className={cn(
                'flex items-center gap-2 truncate',
                item.status === 'SUCESSO' && 'text-foreground',
                item.status === 'pendente' && 'text-muted-foreground',
              )}
            >
              {statusIcon(item.status)}
              <span className="truncate">{item.quota}</span>
            </span>
            <span className="shrink-0 text-xs text-muted-foreground">
              {statusLabel(item.status)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
