import { apiFetch } from '@/lib/api-client'
import type { LoginRequest, LoginResponse, SessionResponse } from '@/types'

export function login(data: LoginRequest): Promise<LoginResponse> {
  return apiFetch<LoginResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function logout(): Promise<{ ok: boolean; message: string }> {
  return apiFetch('/api/auth/logout', { method: 'POST' })
}

/**
 * Consulta quem está logado a partir do cookie de sessão HttpOnly. Como esse
 * cookie não pode ser lido via JavaScript (é o ponto todo de ser HttpOnly),
 * esta é a única forma confiável do front-end confirmar a sessão atual com o
 * backend — diferente de simplesmente ler algo salvo no localStorage.
 */
export function getSession(): Promise<SessionResponse> {
  return apiFetch<SessionResponse>('/api/auth/me')
}
