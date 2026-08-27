import { apiFetch } from '@/lib/api-client'
import type { ErroLanceBloco } from '@/types'

/**
 * Funções prontas para consumir a API de erros de lances (erros_lances.txt).
 *
 * Antes, a tela lia o arquivo direto do disco via uma rota própria do
 * Next.js — funcionava só em desenvolvimento local (frontend e backend na
 * mesma máquina). Em produção, frontend e backend são containers Docker
 * separados com filesystems isolados, então precisa passar pelo backend de
 * verdade (mesmo padrão de histórico/PDFs).
 */

export function getErrosLances(): Promise<{ blocos: ErroLanceBloco[] }> {
  return apiFetch<{ blocos: ErroLanceBloco[] }>('/api/erros-lances')
}

export function deleteErrosLances(): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>('/api/erros-lances', {
    method: 'DELETE',
  })
}
