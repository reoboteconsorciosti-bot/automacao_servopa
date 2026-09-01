'use client'

import * as React from 'react'
import { API_URL } from '@/lib/api-client'
import { normalizeName } from '@/lib/utils'
import {
  getActiveJobs,
  getAutomationStatus,
  startAutomation,
  stopAutomation,
} from '@/services/automation-service'
import type { AutomationStatusValue, QuotaProgressItem } from '@/types'

/**
 * Estado da automação vivendo aqui (no AppShell, que nunca desmonta enquanto
 * o usuário navega entre seções) em vez de dentro da página /automacao.
 *
 * Antes, esse estado (jobId, progresso, nome do consultor, cotas digitadas)
 * ficava dentro de AutomationView e era perdido toda vez que o usuário
 * trocava de seção pelo menu, porque o React desmonta o componente da página
 * anterior — a tentativa de "restaurar" via localStorage num useEffect ao
 * montar de novo se mostrou frágil na prática. Colocando o estado num nível
 * que nunca desmonta, o problema desaparece pela raiz: não precisa restaurar
 * nada, porque nunca é perdido.
 */

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

const USER_STORAGE_KEY = 'servopa.user'
// Sobrevive a reload de página inteira (F5) ou fechar/abrir aba — a troca de
// seção pelo menu já não depende mais disso, mas continua útil pra não
// perder o acompanhamento se o usuário der F5 durante uma execução.
const JOB_STORAGE_KEY = 'servopa.automation.activeJob'
// Consultores marcados como "concluído" na Checklist — o "V" só aparece
// depois de uma confirmação manual (botão "Esse consultor foi concluído" em
// Automação), não só por o nome ter sido digitado. Fica salvo aqui pra
// sobreviver tanto à troca de seção quanto a um F5/fechar e abrir o painel
// de novo.
const CONCLUIDOS_STORAGE_KEY = 'servopa.checklist.concluidos'

interface PersistedJob {
  jobId: string
  consultantName: string
  quotasText: string
}

function persistJob(job: PersistedJob) {
  try {
    localStorage.setItem(JOB_STORAGE_KEY, JSON.stringify(job))
  } catch {
    // ignore — pior caso, só não sobrevive a um F5
  }
}

function clearPersistedJob() {
  try {
    localStorage.removeItem(JOB_STORAGE_KEY)
  } catch {
    // ignore
  }
}

interface AutomationContextValue {
  consultantName: string
  setConsultantName: (v: string) => void
  quotasText: string
  setQuotasText: (v: string) => void
  status: AutomationStatusValue
  errorMessage: string | null
  jobId: string | null
  frame: string | null
  connected: boolean
  progress: QuotaProgressItem[]
  capacity: { activeCount: number; maxConcurrentAutomations: number } | null
  isStopping: boolean
  isRunning: boolean
  parsedQuotas: ParsedQuota[]
  validQuotaCount: number
  hasValidQuotas: boolean
  cotasRepetidas: string[]
  temCotasRepetidas: boolean
  handleStart: () => Promise<void>
  handleStop: () => Promise<void>
  handleReset: () => Promise<void>
  consultoresConcluidos: Set<string>
  marcarConsultorConcluido: (nome: string) => void
}

const AutomationContext = React.createContext<AutomationContextValue | null>(null)

export function AutomationProvider({ children }: { children: React.ReactNode }) {
  const [consultantName, setConsultantName] = React.useState('')
  const [sessionUser, setSessionUser] = React.useState<{ name: string; email: string } | null>(null)
  const [quotasText, setQuotasText] = React.useState('')
  const [status, setStatus] = React.useState<AutomationStatusValue>('idle')
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null)
  // Identifica a execução (job) que esta sessão iniciou. O servidor pode ter
  // outras automações rodando ao mesmo tempo em slots diferentes — sem isso,
  // /status, /stop e o WebSocket /live não saberiam qual acompanhar.
  const [jobId, setJobId] = React.useState<string | null>(null)
  const timerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null)

  // Estado do WebSocket de acompanhamento ao vivo (frames do navegador + checklist de cotas)
  const [frame, setFrame] = React.useState<string | null>(null)
  const [connected, setConnected] = React.useState(false)
  const [progress, setProgress] = React.useState<QuotaProgressItem[]>([])
  const [isStopping, setIsStopping] = React.useState(false)

  // Nomes (já normalizados) dos consultores marcados como concluídos na
  // Checklist. Carrega do localStorage uma vez ao montar o Provider.
  const [consultoresConcluidos, setConsultoresConcluidos] = React.useState<Set<string>>(new Set())

  React.useEffect(() => {
    try {
      const raw = localStorage.getItem(CONCLUIDOS_STORAGE_KEY)
      if (raw) {
        const lista = JSON.parse(raw)
        if (Array.isArray(lista)) {
          setConsultoresConcluidos(new Set(lista))
        }
      }
    } catch {
      // ignore
    }
  }, [])

  function marcarConsultorConcluido(nome: string) {
    const normalizado = normalizeName(nome)
    if (!normalizado) return
    setConsultoresConcluidos((prev) => {
      const next = new Set(prev)
      next.add(normalizado)
      try {
        localStorage.setItem(CONCLUIDOS_STORAGE_KEY, JSON.stringify(Array.from(next)))
      } catch {
        // ignore
      }
      return next
    })
  }

  // Quantos "computadores"/slots estão ocupados agora no servidor (de todos
  // os usuários, não só desta sessão) — o servidor roda até
  // maxConcurrentAutomations automações ao mesmo tempo.
  const [capacity, setCapacity] = React.useState<{ activeCount: number; maxConcurrentAutomations: number } | null>(
    null,
  )

  React.useEffect(() => {
    try {
      const raw = localStorage.getItem(USER_STORAGE_KEY)
      if (raw) {
        const u = JSON.parse(raw)
        if (u && u.name) {
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

  // Roda uma única vez, quando o AppShell monta (login ou F5) — checa se
  // havia uma execução salva de antes do reload e, se o backend confirmar
  // que ela ainda existe, retoma o acompanhamento.
  React.useEffect(() => {
    let cancelled = false

    async function restoreJob() {
      let saved: PersistedJob | null = null
      try {
        const raw = localStorage.getItem(JOB_STORAGE_KEY)
        saved = raw ? (JSON.parse(raw) as PersistedJob) : null
      } catch {
        saved = null
      }
      if (!saved?.jobId) return

      setConsultantName(saved.consultantName || '')
      setQuotasText(saved.quotasText || '')

      try {
        const result = await getAutomationStatus(saved.jobId)
        if (cancelled) return

        if (result.status === 'idle') {
          localStorage.removeItem(JOB_STORAGE_KEY)
          return
        }

        setJobId(saved.jobId)
        setStatus(result.status)
      } catch {
        // Falha pontual de rede ao checar — mantém o registro salvo.
      }
    }

    void restoreJob()
    return () => {
      cancelled = true
    }
  }, [])

  const parsedQuotas = React.useMemo(() => parseQuotaLines(quotasText), [quotasText])
  const validQuotaCount = parsedQuotas.length
  const hasValidQuotas = validQuotaCount > 0
  const cotasRepetidas = React.useMemo(() => encontrarCotasRepetidas(quotasText), [quotasText])
  const temCotasRepetidas = cotasRepetidas.length > 0

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
              return
            }
            const finalStatus = data.status
            setFrame(null)
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

  // Reforço independente do WebSocket: consulta /automation/status
  // periodicamente enquanto roda, garantindo que o painel não fique preso em
  // "Executando" caso a mensagem de conclusão do WebSocket se perca.
  React.useEffect(() => {
    if (!isRunning || !jobId) return

    let cancelled = false
    const interval = setInterval(async () => {
      try {
        const result = await getAutomationStatus(jobId)
        if (!cancelled && result.status !== 'running') {
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
        persistJob({ jobId: response.jobId, consultantName, quotasText })
      }
    } catch (err) {
      console.error('Erro ao iniciar automação:', err)
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
      clearPersistedJob()
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
    clearPersistedJob()
  }

  const value: AutomationContextValue = {
    consultantName,
    setConsultantName,
    quotasText,
    setQuotasText,
    status,
    errorMessage,
    jobId,
    frame,
    connected,
    progress,
    capacity,
    isStopping,
    isRunning,
    parsedQuotas,
    validQuotaCount,
    hasValidQuotas,
    cotasRepetidas,
    temCotasRepetidas,
    handleStart,
    handleStop,
    handleReset,
    consultoresConcluidos,
    marcarConsultorConcluido,
  }

  return <AutomationContext.Provider value={value}>{children}</AutomationContext.Provider>
}

export function useAutomation(): AutomationContextValue {
  const ctx = React.useContext(AutomationContext)
  if (!ctx) {
    throw new Error('useAutomation precisa ser usado dentro de <AutomationProvider>')
  }
  return ctx
}
