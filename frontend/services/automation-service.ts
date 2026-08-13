import { apiFetch } from '@/lib/api-client'
import type { AutomationConfig, AutomationHistoryItem, AutomationStatus, GeneratedPdf } from '@/types'

/**
 * Funções prontas para consumir a API da automação.
 */

export function startAutomation(config: AutomationConfig): Promise<AutomationStatus> {
  return apiFetch<AutomationStatus>('/api/automation/start', {
    method: 'POST',
    body: JSON.stringify(config),
  })
}

export function stopAutomation(): Promise<AutomationStatus> {
  return apiFetch<AutomationStatus>('/api/automation/stop', {
    method: 'POST',
  })
}

export function getAutomationStatus(): Promise<AutomationStatus> {
  return apiFetch<AutomationStatus>('/api/automation/status')
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

