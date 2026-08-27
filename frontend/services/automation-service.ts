import { apiFetch } from '@/lib/api-client'
import type {
  ActiveJobsResponse,
  AutomationConfig,
  AutomationHistoryItem,
  AutomationStatus,
  GeneratedPdf,
} from '@/types'

/**
 * Funções prontas para consumir a API da automação.
 *
 * O servidor suporta várias automações rodando ao mesmo tempo (um slot de
 * Firefox por execução) — por isso stop/status pedem o `jobId` retornado por
 * startAutomation, identificando qual execução específica você quer
 * consultar/parar, em vez de assumir que só existe "a" automação atual.
 */

export function startAutomation(config: AutomationConfig): Promise<AutomationStatus> {
  return apiFetch<AutomationStatus>('/api/automation/start', {
    method: 'POST',
    body: JSON.stringify(config),
  })
}

export function stopAutomation(jobId: string): Promise<AutomationStatus> {
  return apiFetch<AutomationStatus>(`/api/automation/stop?job_id=${encodeURIComponent(jobId)}`, {
    method: 'POST',
  })
}

export function getAutomationStatus(jobId: string): Promise<AutomationStatus> {
  return apiFetch<AutomationStatus>(`/api/automation/status?job_id=${encodeURIComponent(jobId)}`)
}

/** Lista as automações rodando agora no servidor (todos os usuários, não só a sua). */
export function getActiveJobs(): Promise<ActiveJobsResponse> {
  return apiFetch<ActiveJobsResponse>('/api/automation/jobs')
}

export function getPdfs(): Promise<GeneratedPdf[]> {
  return apiFetch<GeneratedPdf[]>('/api/pdfs')
}

export function getAutomationHistory(): Promise<AutomationHistoryItem[]> {
  return apiFetch<AutomationHistoryItem[]>('/api/automation/history')
}

export function deleteAutomationHistory(id: string): Promise<void> {
  return apiFetch<void>(`/api/automation/history/${id}`, {
    method: 'DELETE',
  })
}

export function deletePdf(id: string): Promise<void> {
  return apiFetch<void>(`/api/pdfs/${id}`, {
    method: 'DELETE',
  })
}

