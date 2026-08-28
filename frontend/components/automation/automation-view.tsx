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
import { API_URL } from '@/lib/api-client'
import type { AutomationStatusValue, GeneratedPdf, QuotaProgressItem } from '@/types'
import { getActiveJobs, getAutomationStatus, startAutomation, stopAutomation } from '@/services/automation-service'

// Placar de execução: uma instância deste componente/aba acompanha SÓ o job
// que ela mesma iniciou (identificado por jobId) — o servidor pode estar
// rodando outras automações de outros consultores/computadores ao mesmo
// tempo, em slots separados, sem afetar esta.

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

/** Encontra linhas repetidas (cota digitada mais de uma vez) na lista de
 * cotas — compara o texto exato de cada linha, não os campos já separados,
 * então pega duplicata mesmo com espaçamento diferente após o trim. */
function encontrarCotasRepetidas(texto: string): string[] {
  const linhas = texto
    .split(/\r?\n/)
    .map((linha) => linha.trim())
    .filter((linha) => linha !== '')

  const cotasJaVistas = new Set<string>()
  const cotasRepetidas = new Set<string>()

  for (const cota of linhas) {
    if (cotasJaVistas.has(cota)) {
      cotasRepetidas.add(cota)
    } else {
      cotasJaVistas.add(cota)
    }
  }

  return Array.from(cotasRepetidas)
}

/** Deriva a URL do WebSocket a partir da API_URL (http -> ws, https -> wss),
 * identificando qual execução (job) acompanhar entre as que podem estar
 * rodando ao mesmo tempo no servidor. */
function buildLiveViewUrl(jobId: string): string {
  const wsBase = API_URL.replace(/^http/, 'ws')
  return `${wsBase}/api/automation/live?job_id=${encodeURIComponent(jobId)}`
}

type LiveMessage =
  | { type: 'frame'; image: string }
  | { type: 'status'; status: 'idle' | 'running' | 'finished' | 'error' | 'unavailable' }
  | { type: 'progress'; items: QuotaProgressItem[] }

interface AutomationViewProps {
  pdfs: GeneratedPdf[]
}

const STORAGE_KEY = 'servopa.user'

export function AutomationView({ pdfs }: AutomationViewProps) {
  const [consultantName, setConsultantName] = React.useState('')
  const [sessionUser, setSessionUser] = React.useState<{ name: string; email: string } | null>(null)
  const [quotasText, setQuotasText] = React.useState('')
  const [status, setStatus] = React.useState<AutomationStatusValue>('idle')
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null)
  // Identifica a execução (job) que ESTA aba/sessão iniciou. O servidor pode
  // ter outras automações rodando ao mesmo tempo em slots diferentes — sem
  // isso, /status, /stop e o WebSocket /live não saberiam qual acompanhar.
  const [jobId, setJobId] = React.useState<string | null>(null)
  const timerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null)

  // Estado do WebSocket de acompanhamento ao vivo (frames do navegador + checklist de cotas)
  const [frame, setFrame] = React.useState<string | null>(null)
  const [connected, setConnected] = React.useState(false)
  const [progress, setProgress] = React.useState<QuotaProgressItem[]>([])

  React.useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) {
        const u = JSON.parse(raw)
        if (u && u.name) {
          // Guarda o usuário logado só para registrar "quem executou" no histórico
          // (userName/userEmail) — o nome do consultor é um dado à parte, digitado
          // manualmente, e não deve vir pré-preenchido com o usuário da sessão.
          setSessionUser(u)
        }
      }
    } catch {
      // ignore
    }
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [])

  const parsedQuotas = React.useMemo(() => parseQuotaLines(quotasText), [quotasText])
  const validQuotaCount = parsedQuotas.length
  const hasValidQuotas = validQuotaCount > 0
  const cotasRepetidas = React.useMemo(() => encontrarCotasRepetidas(quotasText), [quotasText])

  // Quantos "computadores"/slots estão ocupados agora no servidor (de todos
  // os usuários, não só desta aba) — o servidor roda até maxConcurrentAutomations
  // automações ao mesmo tempo, cada uma em seu próprio perfil de Firefox.
  const [capacity, setCapacity] = React.useState<{ activeCount: number; maxConcurrentAutomations: number } | null>(
    null,
  )

  React.useEffect(() => {
    let cancelled = false
    async function poll() {
      try {
        const result = await getActiveJobs()
        if (!cancelled) {
          setCapacity({
            activeCount: result.activeCount,
            maxConcurrentAutomations: result.maxConcurrentAutomations,
          })
        }
      } catch {
        // ignora falhas pontuais — é só um indicador informativo
      }
    }
    void poll()
    const interval = setInterval(poll, 5000)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [])

  const [isStopping, setIsStopping] = React.useState(false)

  const isRunning = status === 'running'

  // Conecta ao WebSocket de acompanhamento enquanto a automação estiver rodando
  React.useEffect(() => {
    if (!isRunning || !jobId) {
      setFrame(null)
      setConnected(false)
      return
    }

    let socket: WebSocket | null = null
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null
    let cancelled = false

    function connect() {
      socket = new WebSocket(buildLiveViewUrl(jobId as string))

      socket.onopen = () => setConnected(true)

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as LiveMessage
          if (data.type === 'frame') {
            setFrame(`data:image/png;base64,${data.image}`)
          } else if (data.type === 'status') {
            if (data.status === 'unavailable') {
              // Falha pontual ao capturar a tela — não diz nada sobre o status geral.
              return
            }
            const finalStatus = data.status
            setFrame(null)
            // O backend fechou o navegador sozinho (fim natural da execução, sem
            // clique manual em "Parar") — reflete o resultado real (concluída ou
            // com erro) no painel automaticamente, sem assumir sucesso.
            setStatus((prev) => (prev === 'running' ? finalStatus : prev))
          } else if (data.type === 'progress') {
            setProgress(data.items)
          }
        } catch {
          // ignora mensagens inesperadas
        }
      }

      socket.onclose = () => {
        setConnected(false)
        if (!cancelled) {
          reconnectTimer = setTimeout(connect, 2000)
        }
      }

      socket.onerror = () => {
        socket?.close()
      }
    }

    connect()

    return () => {
      cancelled = true
      if (reconnectTimer) clearTimeout(reconnectTimer)
      socket?.close()
    }
  }, [isRunning, jobId])

  // Reforço independente do WebSocket: consulta /automation/status periodicamente
  // enquanto roda, garantindo que o painel não fique preso em "Executando" caso
  // a mensagem de conclusão do WebSocket se perca por algum motivo.
  React.useEffect(() => {
    if (!isRunning || !jobId) return

    let cancelled = false
    const interval = setInterval(async () => {
      try {
        const result = await getAutomationStatus(jobId)
        if (!cancelled && result.status !== 'running') {
          // Usa o status real devolvido pelo backend ("finished"/"error"/"idle"),
          // nunca assume sucesso só porque parou de rodar.
          setStatus((prev) => (prev === 'running' ? result.status : prev))
        }
      } catch {
        // ignora falhas pontuais de rede — o WebSocket é a via principal
      }
    }, 5000)

    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [isRunning, jobId])

  async function handleStart() {
    if (!consultantName.trim() || status === 'running' || !hasValidQuotas) return
    setErrorMessage(null)
    setStatus('running')
    setJobId(null)
    setProgress(
      parsedQuotas.map((q) => ({
        quota: `${q.grupo}.${q.cota}-${q.digito}`,
        status: 'pendente',
      })),
    )

    try {
      const response = await startAutomation({
        consultantName,
        userName: sessionUser?.name || consultantName,
        userEmail: sessionUser?.email || '',
        bids: parsedQuotas.map((q, idx) => ({
          id: String(idx + 1),
          quota: `${q.grupo},${q.cota},${q.digito}`,
          bidValue: '0',
        })),
      })
      if (response && response.status) {
        setStatus(response.status)
      }
      if (response?.jobId) {
        setJobId(response.jobId)
      }
    } catch (err) {
      console.error('Erro ao iniciar automação:', err)
      // Mensagem do backend (ex.: 409 "todas as N automações simultâneas
      // já estão em uso") já vem formatada pelo apiFetch em err.message —
      // mostra ela em vez de um "Erro" genérico, pra deixar claro o que
      // aconteceu e o que fazer (ex.: esperar um slot liberar).
      setErrorMessage(err instanceof Error ? err.message : 'Erro ao iniciar automação.')
      setStatus('error')
    }
  }

  async function handleStop() {
    setIsStopping(true)
    if (timerRef.current) clearTimeout(timerRef.current)
    try {
      if (jobId) {
        await stopAutomation(jobId)
      }
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
      if (jobId) {
        await stopAutomation(jobId)
      }
    } catch {
      // ignore
    }
    setStatus('idle')
    setProgress([])
    setErrorMessage(null)
    setJobId(null)
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
