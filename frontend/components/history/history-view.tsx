'use client'

import * as React from 'react'
import {
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Search,
  UserCheck,
  FileText,
  FileClock,
  RefreshCw,
  Trash2,
} from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { deleteAutomationHistory, getAutomationHistory } from '@/services/automation-service'
import { formatDateBrasilia } from '@/lib/utils'
import type { AutomationHistoryItem } from '@/types'

/**
 * O backend junta as cotas com ", " (vírgula + espaço) em `quotas_summary`.
 * Cada cota individual pode conter vírgulas internas (ex.: "1556,2514,4"),
 * mas nunca vírgula seguida de espaço — por isso dividir por /,\s+/ isola
 * corretamente cada cota, mesmo nesse formato.
 */
function splitQuotas(summary: string): string[] {
  return summary
    .split(/,\s+/)
    .map((q) => q.trim())
    .filter(Boolean)
}

function StatusBadge({ status }: { status: string }) {
  switch (status) {
    case 'finished':
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-semibold text-emerald-500 border border-emerald-500/20">
          <CheckCircle2 className="size-3.5" />
          Concluído
        </span>
      )
    case 'running':
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-500/10 px-2.5 py-1 text-xs font-semibold text-blue-500 border border-blue-500/20 animate-pulse">
          <Loader2 className="size-3.5 animate-spin" />
          Em andamento
        </span>
      )
    case 'error':
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full bg-rose-500/10 px-2.5 py-1 text-xs font-semibold text-rose-500 border border-rose-500/20">
          <AlertCircle className="size-3.5" />
          Erro
        </span>
      )
    case 'idle':
    default:
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 px-2.5 py-1 text-xs font-semibold text-amber-500 border border-amber-500/20">
          <Clock className="size-3.5" />
          Interrompido
        </span>
      )
  }
}

export function HistoryView() {
  const [history, setHistory] = React.useState<AutomationHistoryItem[]>([])
  const [loading, setLoading] = React.useState(true)
  const [searchTerm, setSearchTerm] = React.useState('')
  const [deletingId, setDeletingId] = React.useState<string | null>(null)

  const loadHistory = React.useCallback(async () => {
    setLoading(true)
    try {
      const data = await getAutomationHistory()
      setHistory(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error('Erro ao buscar histórico:', err)
      setHistory([])
    } finally {
      setLoading(false)
    }
  }, [])

  async function handleDelete(item: AutomationHistoryItem) {
    const label = item.executedBy?.name || item.consultantName || 'este registro'
    if (!window.confirm(`Excluir "${label}" do histórico? Essa ação não pode ser desfeita.`)) {
      return
    }
    setDeletingId(item.id)
    try {
      await deleteAutomationHistory(item.id)
      setHistory((prev) => prev.filter((h) => h.id !== item.id))
    } catch (err) {
      console.error('Erro ao excluir registro do histórico:', err)
      window.alert('Não foi possível excluir o registro. Tente novamente.')
    } finally {
      setDeletingId(null)
    }
  }

  React.useEffect(() => {
    void loadHistory()
  }, [loadHistory])

  const filteredHistory = React.useMemo(() => {
    if (!searchTerm.trim()) return history
    const term = searchTerm.toLowerCase()
    return history.filter(
      (item) =>
        item.executedBy?.name?.toLowerCase().includes(term) ||
        item.executedBy?.email?.toLowerCase().includes(term) ||
        item.consultantName?.toLowerCase().includes(term) ||
        item.quotasSummary?.toLowerCase().includes(term),
    )
  }, [history, searchTerm])

  const metrics = React.useMemo(() => {
    const total = history.length
    const finished = history.filter((i) => i.status === 'finished').length
    const uniqueUsers = new Set(history.map((i) => i.executedBy?.email).filter(Boolean)).size
    const totalQuotas = history.reduce((acc, i) => acc + (i.quotasCount || 0), 0)
    return { total, finished, uniqueUsers, totalQuotas }
  }, [history])

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 p-4 sm:p-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader
          title="Histórico de Automações"
          description="Registro completo de execuções no banco de dados por usuário, data e horário."
        />
        <Button variant="outline" size="sm" onClick={loadHistory} disabled={loading} className="self-start sm:self-auto gap-2">
          <RefreshCw className={`size-4 ${loading ? 'animate-spin' : ''}`} />
          Atualizar
        </Button>
      </div>

      {/* Cards de Métricas */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="border-border/60 bg-card/60 backdrop-blur">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total de Execuções
            </CardTitle>
            <FileClock className="size-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.total}</div>
            <p className="text-xs text-muted-foreground">Registradas no histórico</p>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/60 backdrop-blur">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Concluídas com Sucesso
            </CardTitle>
            <CheckCircle2 className="size-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-500">{metrics.finished}</div>
            <p className="text-xs text-muted-foreground">Execuções finalizadas</p>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/60 backdrop-blur">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Usuários Distintos
            </CardTitle>
            <UserCheck className="size-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.uniqueUsers}</div>
            <p className="text-xs text-muted-foreground">Executaram a automação</p>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/60 backdrop-blur">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Cotas Processadas
            </CardTitle>
            <FileText className="size-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.totalQuotas}</div>
            <p className="text-xs text-muted-foreground">Total acumulado de cotas</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabela do Histórico */}
      <Card className="overflow-hidden border-border/60">
        <CardHeader className="border-b border-border/40 p-5">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>Histórico por Usuário</CardTitle>
              <CardDescription>
                Lista de automações disparadas e gravadas no banco de dados.
              </CardDescription>
            </div>
            <div className="relative w-full sm:w-72">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Buscar por usuário ou cota..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9 text-sm"
              />
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-5">
          {loading ? (
            <div className="flex flex-col items-center justify-center p-12 text-center">
              <Loader2 className="size-8 animate-spin text-primary" />
              <p className="mt-3 text-sm text-muted-foreground">Carregando histórico do banco...</p>
            </div>
          ) : filteredHistory.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-12 text-center">
              <FileClock className="size-10 text-muted-foreground/60" />
              <h3 className="mt-3 text-base font-semibold">Nenhum registro encontrado</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                {searchTerm
                  ? 'Nenhum resultado corresponde à sua busca.'
                  : 'Nenhuma automação foi executada ainda.'}
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {filteredHistory.map((item) => (
                <div
                  key={item.id}
                  className="flex flex-col gap-3 rounded-lg border border-border/60 bg-muted/20 p-4"
                >
                  {/* Cabeçalho do container: usuário da sessão + status + excluir */}
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex flex-col">
                      <span className="font-medium text-foreground">
                        {item.executedBy?.name || 'Usuário Desconhecido'}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {item.executedBy?.email || '-'}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <StatusBadge status={item.status} />
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        aria-label="Excluir registro do histórico"
                        onClick={() => handleDelete(item)}
                        disabled={deletingId === item.id}
                        className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                      >
                        {deletingId === item.id ? (
                          <Loader2 className="size-4 animate-spin" />
                        ) : (
                          <Trash2 className="size-4" />
                        )}
                      </Button>
                    </div>
                  </div>

                  {/* Metadados: consultor + data */}
                  <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-muted-foreground">
                    <span>
                      Consultor:{' '}
                      <span className="font-medium text-foreground">
                        {item.consultantName || '-'}
                      </span>
                    </span>
                    <span className="tabular-nums">{formatDateBrasilia(item.createdAt)}</span>
                  </div>

                  {/* Cotas: cada uma em sua própria div dentro do container do usuário */}
                  <div className="flex flex-col gap-1.5 border-t border-border/40 pt-3">
                    <span className="text-[11px] font-medium text-muted-foreground">
                      {item.quotasCount || 0} {item.quotasCount === 1 ? 'cota' : 'cotas'}
                    </span>
                    {item.quotasSummary ? (
                      <div className="flex flex-wrap gap-1.5">
                        {splitQuotas(item.quotasSummary).map((quota, i) => (
                          <div
                            key={`${item.id}-${i}`}
                            className="rounded-md border border-border/60 bg-background px-2 py-1 font-mono text-xs text-foreground"
                          >
                            {quota}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <span className="text-xs text-muted-foreground">Nenhuma cota</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
