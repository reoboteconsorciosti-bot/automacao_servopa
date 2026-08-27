'use client'

import * as React from 'react'
import { AlertTriangle, Download, FileWarning, Loader2, RefreshCw, Trash2 } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { API_URL } from '@/lib/api-client'
import { deleteErrosLances, getErrosLances } from '@/services/erros-lances-service'
import type { ErroLanceBloco } from '@/types'

function StatusBadge({ status }: { status: string }) {
  const isCritico = status.toUpperCase().includes('CRITICO')
  return (
    <span
      className={
        isCritico
          ? 'inline-flex items-center gap-1.5 rounded-full bg-rose-500/10 px-2.5 py-1 text-xs font-semibold text-rose-500 border border-rose-500/20'
          : 'inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 px-2.5 py-1 text-xs font-semibold text-amber-500 border border-amber-500/20'
      }
    >
      {status}
    </span>
  )
}

export function ErrosLancesView() {
  const [blocos, setBlocos] = React.useState<ErroLanceBloco[]>([])
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)
  const [deleting, setDeleting] = React.useState(false)

  const loadErros = React.useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getErrosLances()
      setBlocos(Array.isArray(data.blocos) ? data.blocos : [])
    } catch (err) {
      console.error('Erro ao buscar erros_lances.txt:', err)
      setError('Não foi possível carregar o arquivo de erros de lances.')
      setBlocos([])
    } finally {
      setLoading(false)
    }
  }, [])

  React.useEffect(() => {
    void loadErros()
  }, [loadErros])

  async function handleDeleteAll() {
    if (
      !window.confirm(
        'Excluir todos os erros de lances registrados? Essa ação apaga o arquivo erros_lances.txt e não pode ser desfeita.',
      )
    ) {
      return
    }
    setDeleting(true)
    try {
      await deleteErrosLances()
      setBlocos([])
    } catch (err) {
      console.error('Erro ao excluir erros_lances.txt:', err)
      window.alert('Não foi possível excluir os erros de lances. Tente novamente.')
    } finally {
      setDeleting(false)
    }
  }

  const totalErros = React.useMemo(
    () => blocos.reduce((acc, b) => acc + b.errors.length, 0),
    [blocos],
  )

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 p-4 sm:p-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader
          title="Erros de Lances"
          description="Cotas que não puderam ser registradas em execuções anteriores da automação (erros_lances.txt)."
        />
        <div className="flex gap-2 self-start sm:self-auto">
          <Button variant="outline" size="sm" onClick={loadErros} disabled={loading} className="gap-2">
            <RefreshCw className={`size-4 ${loading ? 'animate-spin' : ''}`} />
            Atualizar
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={blocos.length === 0}
            className="gap-2"
            nativeButton={false}
            render={<a href={`${API_URL}/api/erros-lances/download`} target="_blank" rel="noopener noreferrer" />}
          >
            <Download className="size-4" />
            Baixar TXT
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleDeleteAll}
            disabled={deleting || blocos.length === 0}
            className="gap-2 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
          >
            {deleting ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Trash2 className="size-4" />
            )}
            Excluir todos
          </Button>
        </div>
      </div>

      <Card className="overflow-hidden border-border/60">
        <CardHeader className="border-b border-border/40 p-5">
          <CardTitle>Execuções com erro</CardTitle>
          <CardDescription>
            {totalErros > 0
              ? `${totalErros} cota${totalErros === 1 ? '' : 's'} com erro em ${blocos.length} execuç${blocos.length === 1 ? 'ão' : 'ões'}.`
              : 'Nenhum erro registrado até agora.'}
          </CardDescription>
        </CardHeader>

        <CardContent className="p-5">
          {loading ? (
            <div className="flex flex-col items-center justify-center p-12 text-center">
              <Loader2 className="size-8 animate-spin text-primary" />
              <p className="mt-3 text-sm text-muted-foreground">Lendo erros_lances.txt...</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center p-12 text-center">
              <AlertTriangle className="size-10 text-rose-500/70" />
              <h3 className="mt-3 text-base font-semibold">Falha ao carregar</h3>
              <p className="mt-1 text-sm text-muted-foreground">{error}</p>
            </div>
          ) : blocos.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-12 text-center">
              <FileWarning className="size-10 text-muted-foreground/60" />
              <h3 className="mt-3 text-base font-semibold">Nenhum erro encontrado</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Todas as execuções da automação foram concluídas sem erros de cota.
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {blocos.map((bloco, idx) => (
                <div
                  key={`${bloco.consultant}-${bloco.dateTime}-${idx}`}
                  className="flex flex-col gap-3 rounded-lg border border-border/60 bg-muted/20 p-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex flex-col">
                      <span className="font-medium text-foreground">{bloco.consultant}</span>
                      <span className="text-xs text-muted-foreground tabular-nums">
                        {bloco.dateTime}
                      </span>
                    </div>
                    <span className="text-xs font-medium text-muted-foreground">
                      {bloco.total} {bloco.total === 1 ? 'cota' : 'cotas'} com erro
                    </span>
                  </div>

                  <div className="flex flex-col gap-2 border-t border-border/40 pt-3">
                    {bloco.errors.map((erro, i) => (
                      <div
                        key={`${erro.cota}-${i}`}
                        className="flex flex-col gap-1.5 rounded-md border border-border/60 bg-background p-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4"
                      >
                        <div className="flex flex-col gap-1">
                          <span className="font-mono text-xs text-foreground">
                            Cota: {erro.cota}
                          </span>
                          <span className="text-xs text-muted-foreground">{erro.motivo}</span>
                        </div>
                        <StatusBadge status={erro.status} />
                      </div>
                    ))}
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
