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
  /** Lista de cotas e seus respectivos lances. */
  bids: BidQuota[]
}

export interface GeneratedPdf {
  id: string
  fileName: string
  consultantName: string
  createdAt: string
  url: string
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
