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
import { PdfTable } from '@/components/automation/pdf-table'
import type { AutomationStatusValue, GeneratedPdf } from '@/types'
import { startAutomation, stopAutomation } from '@/services/automation-service'

interface ParsedQuota {
  grupo: string
  cota: string
  digito: string
}

function parseQuotaLines(raw: string): ParsedQuota[] {
  return raw
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [grupo, cota, digito] = line.split(',').map((s) => s.trim())
      return { grupo, cota, digito }
    })
    .filter((q) => q.grupo && q.cota && q.digito)
}

interface AutomationViewProps {
  pdfs: GeneratedPdf[]
}

export function AutomationView({ pdfs }: AutomationViewProps) {
  const [consultantName, setConsultantName] = React.useState('')
  const [quotasText, setQuotasText] = React.useState('')
  const [status, setStatus] = React.useState<AutomationStatusValue>('idle')
  const timerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null)

  React.useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [])

  const parsedQuotas = React.useMemo(() => parseQuotaLines(quotasText), [quotasText])
  const validQuotaCount = parsedQuotas.length
  const hasValidQuotas = validQuotaCount > 0

  const [isStopping, setIsStopping] = React.useState(false)

  async function handleStart() {
    if (!consultantName.trim() || status === 'running' || !hasValidQuotas) return
    setStatus('running')

    try {
      const response = await startAutomation({
        consultantName,
        bids: parsedQuotas.map((q, idx) => ({
          id: String(idx + 1),
          quota: `${q.grupo},${q.cota},${q.digito}`,
          bidValue: '0',
        })),
      })
      if (response && response.status) {
        setStatus(response.status)
      }
    } catch (err) {
      console.error('Erro ao iniciar automação:', err)
      setStatus('error')
    }
  }

  async function handleStop() {
    setIsStopping(true)
    if (timerRef.current) clearTimeout(timerRef.current)
    try {
      await stopAutomation()
    } catch (err) {
      console.error('Erro ao parar automação:', err)
    } finally {
      setStatus('idle')
      setIsStopping(false)
    }
  }

  async function handleReset() {
    if (timerRef.current) clearTimeout(timerRef.current)
    try {
      await stopAutomation()
    } catch {
      // ignore
    }
    setStatus('idle')
  }

  const isRunning = status === 'running'

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
                  placeholder="Ex.: Ana Beatriz Souza"
                  disabled={isRunning}
                />
              </div>

              <div className="flex flex-col gap-2">
                <Label htmlFor="quotas">
                  Lista de Cotas (grupo,cota,dígito — uma por linha)
                </Label>
                <Textarea
                  id="quotas"
                  name="quotas"
                  value={quotasText}
                  onChange={(e) => setQuotasText(e.target.value)}
                  disabled={isRunning}
                  placeholder={[
                    '1561,1197,7',
                    '1561,1265,5',
                  ].join('\n')}
                />
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
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Execução</CardTitle>
              <CardDescription>Inicie a automação com as configurações acima.</CardDescription>
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
              <LiveView status={status} />
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
