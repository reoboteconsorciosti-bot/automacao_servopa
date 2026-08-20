export interface User {
  id: string | number
  name: string
  email: string
  document?: string | null
  createdAt: string
}

export type UserInput = Omit<User, 'id' | 'createdAt'>

export type AutomationStatusValue = 'idle' | 'running' | 'finished' | 'error'

export interface AutomationStatus {
  status: AutomationStatusValue
  message?: string
  updatedAt: string
}

/** Uma cota de lance informada pelo consultor. */
export interface BidQuota {
  id: string
  /** Número/identificação da cota. */
  quota: string
  /** Valor do lance para a cota. */
  bidValue: string
}

export interface AutomationConfig {
  consultantName: string
  userName?: string
  userEmail?: string
  /** Lista de cotas e seus respectivos lances. */
  bids: BidQuota[]
}

export interface AutomationHistoryItem {
  id: string
  executedBy: {
    id?: string | number
    name: string
    email: string
  }
  consultantName: string
  quotasCount: number
  quotasSummary: string
  createdAt: string
  status: AutomationStatusValue
  pdfFilename?: string | null
}

export interface GeneratedPdf {
  id: string
  fileName: string
  consultantName: string
  createdAt: string
  url: string
}

/** Status de processamento de uma cota individual durante a execução. */
export type QuotaProgressStatus =
  | 'pendente'
  | 'processando'
  | 'SUCESSO'
  | 'ERRO_BENIGNO'
  | 'ERRO_CRITICO'
  | 'invalido'

export interface QuotaProgressItem {
  quota: string
  status: QuotaProgressStatus
  message?: string | null
}

/** Um erro individual de cota dentro de um bloco de execução do erros_lances.txt. */
export interface ErroLanceItem {
  cota: string
  status: string
  motivo: string
}

/** Um bloco de execução (delimitado por "====") do erros_lances.txt. */
export interface ErroLanceBloco {
  consultant: string
  dateTime: string
  total: number
  errors: ErroLanceItem[]
}

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  ok: boolean
  message: string
  user?: User | null
}

/** Resposta de GET /api/auth/me — quem está logado, segundo o cookie de sessão HttpOnly. */
export interface SessionResponse {
  authenticated: boolean
  user: { id: string | number; email: string; name: string } | null
}
