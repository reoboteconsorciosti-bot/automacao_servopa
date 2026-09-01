'use client'

import * as React from 'react'
import { Loader2, Play, RotateCcw, Square } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { StatusIndicator } from '@/components/automation/status-indicator'
import { LiveView } from '@/components/automation/live-view'
import { QuotaChecklist } from '@/components/automation/quota-checklist'
import { PdfTable } from '@/components/automation/pdf-table'
import { useAutomation } from '@/contexts/automation-context'
import type { GeneratedPdf } from '@/types'

// Placar de execução: o estado (jobId, progresso, nome do consultor, cotas
// digitadas) mora no AutomationProvider (montado uma vez no AppShell, que
// nunca desmonta ao trocar de seção pelo menu) — este componente só lê e
// exibe. Trocar de seção e voltar para Automação não perde mais nada, porque
// o Provider continua vivo o tempo todo, rodando a automação em segundo
// plano independentemente de qual página está sendo exibida.

interface AutomationViewProps {
  pdfs: GeneratedPdf[]
}

export function AutomationView({ pdfs }: AutomationViewProps) {
  const {
    consultantName,
    setConsultantName,
    quotasText,
    setQuotasText,
    status,
    errorMessage,
    frame,
    connected,
    progress,
    capacity,
    isStopping,
    isRunning,
    validQuotaCount,
    hasValidQuotas,
    cotasRepetidas,
    temCotasRepetidas,
    handleStart,
    handleStop,
    handleReset,
  } = useAutomation()

  // Um <textarea> nativo não colore trechos individuais do texto (só cor
  // uniforme) — para destacar as linhas repetidas em amarelo mantendo o
  // campo editável, sobrepomos um <div> com as mesmas linhas atrás do
  // textarea (que fica com o texto transparente, só o cursor/seleção
  // visíveis) e sincronizamos o scroll entre os dois via ref.
  const quotasTextareaRef = React.useRef<HTMLTextAreaElement>(null)
  const quotasOverlayRef = React.useRef<HTMLDivElement>(null)

  function handleQuotasScroll() {
    if (quotasTextareaRef.current && quotasOverlayRef.current) {
      quotasOverlayRef.current.scrollTop = quotasTextareaRef.current.scrollTop
      quotasOverlayRef.current.scrollLeft = quotasTextareaRef.current.scrollLeft
    }
  }

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6 p-4 sm:p-8">
      <PageHeader
        title="Automação"
        description="Configure e acompanhe a execução da automação de lances de crédito."
      />

      <div className="grid gap-6 lg:grid-cols-5">
        {/* Coluna de configuração e execução */}
        <div className="flex flex-col gap-6 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Dados da automação</CardTitle>
              <CardDescription>
                Preencha os dados do consultor e a lista de cotas do consórcio.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="consultant">Nome do consultor</Label>
                <Input
                  id="consultant"
                  name="consultant"
                  value={consultantName}
                  onChange={(e) => setConsultantName(e.target.value)}
                  placeholder="Coloque o nome do consultor"
                  disabled={isRunning}
                />
                <p className="text-xs text-muted-foreground">
                  Esse nome é usado para criar a pasta dos PDFs gerados.
                </p>
              </div>

              <div className="flex flex-col gap-2">
                <Label htmlFor="quotas">
                  Lista de Cotas (grupo,cota,dígito — uma por linha)
                </Label>
                <div className="relative">
                  {temCotasRepetidas && (
                    <div
                      ref={quotasOverlayRef}
                      aria-hidden="true"
                      className="pointer-events-none absolute inset-0 overflow-hidden whitespace-pre-wrap break-words rounded-xl border border-transparent px-4 py-3 text-sm"
                    >
                      {quotasText.split(/\r?\n/).map((linha, i) => (
                        <div
                          key={i}
                          className={
                            cotasRepetidas.includes(linha.trim())
                              ? 'rounded-[3px] bg-yellow-400/40'
                              : undefined
                          }
                        >
                          {/* linha vazia precisa de conteúdo pra não colapsar a altura */}
                          {linha.length > 0 ? linha : ' '}
                        </div>
                      ))}
                    </div>
                  )}
                  <Textarea
                    id="quotas"
                    name="quotas"
                    ref={quotasTextareaRef}
                    value={quotasText}
                    onChange={(e) => setQuotasText(e.target.value)}
                    onScroll={temCotasRepetidas ? handleQuotasScroll : undefined}
                    disabled={isRunning}
                    placeholder={[
                      '1561,1197,7',
                      '1561,1265,5',
                    ].join('\n')}
                    className={temCotasRepetidas ? 'relative bg-transparent text-transparent caret-foreground' : 'relative'}
                  />
                </div>
                <p className="text-sm font-medium tabular-nums text-muted-foreground">
                  Total de Cotas Válidas:{' '}
                  <span
                    className={
                      validQuotaCount > 0
                        ? 'text-primary'
                        : 'text-muted-foreground'
                    }
                  >
                    {validQuotaCount}
                  </span>
                </p>

                {cotasRepetidas.length > 0 && (
                  <p className="text-sm font-medium text-destructive">
                    Cota{cotasRepetidas.length === 1 ? '' : 's'} repetida
                    {cotasRepetidas.length === 1 ? '' : 's'} na lista: {cotasRepetidas.join(', ')}
                  </p>
                )}
              </div>

              {/* Checklist de progresso por cota (aparece quando há uma execução em andamento ou recém-concluída) */}
              <QuotaChecklist items={progress} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Execução</CardTitle>
              <CardDescription>Inicie a automação com as configurações acima.</CardDescription>
              {capacity && (
                <p className="text-xs text-muted-foreground">
                  {capacity.activeCount} de {capacity.maxConcurrentAutomations} automações simultâneas em uso no
                  servidor agora
                </p>
              )}
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              {isRunning ? (
                <Button
                  size="lg"
                  variant="destructive"
                  className="h-12 w-full text-base font-semibold transition-all hover:bg-destructive/90"
                  onClick={handleStop}
                  disabled={isStopping}
                >
                  {isStopping ? (
                    <>
                      <Loader2 className="size-5 animate-spin" />
                      Encerrando navegador...
                    </>
                  ) : (
                    <>
                      <Square className="size-5 fill-current" />
                      Parar Automação
                    </>
                  )}
                </Button>
              ) : (
                <Button
                  size="lg"
                  className="h-12 w-full text-base"
                  onClick={handleStart}
                  disabled={!consultantName.trim() || !hasValidQuotas}
                >
                  <Play data-icon="inline-start" />
                  Iniciar Automação
                </Button>
              )}

              <div className="rounded-lg border border-border bg-muted/30 p-4">
                <StatusIndicator status={status} />
              </div>

              {status === 'error' && errorMessage && (
                <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                  {errorMessage}
                </div>
              )}

              {(status === 'finished' || status === 'error') && (
                <Button variant="outline" onClick={handleReset}>
                  <RotateCcw data-icon="inline-start" />
                  Reiniciar
                </Button>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Coluna da visualização ao vivo */}
        <div className="lg:col-span-3">
          <Card className="h-full">
            <CardHeader>
              <CardTitle>Ver automação ao vivo</CardTitle>
              <CardDescription>
                Acompanhe a execução da automação em tempo real.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <LiveView status={status} frame={frame} connected={connected} />
            </CardContent>
          </Card>
        </div>
      </div>

      {/* PDFs gerados */}
      <Card className="overflow-hidden p-0">
        <CardHeader className="p-5">
          <CardTitle>PDFs gerados</CardTitle>
          <CardDescription>Arquivos gerados pelas execuções da automação.</CardDescription>
        </CardHeader>
        <PdfTable pdfs={pdfs} />
      </Card>
    </div>
  )
}
