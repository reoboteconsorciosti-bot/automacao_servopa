import { apiFetch } from '@/lib/api-client'
import type { AutomationConfig, AutomationStatus, GeneratedPdf } from '@/types'

/**
 * Funções prontas para consumir a API da automação.
 * Os endpoints reais (Selenium, geração de PDFs, etc.) serão implementados no backend.
 */

export function startAutomation(config: AutomationConfig): Promise<AutomationStatus> {
  return apiFetch<AutomationStatus>('/automation/start', {
    method: 'POST',
    body: JSON.stringify(config),
  })
}

export function stopAutomation(): Promise<AutomationStatus> {
  return apiFetch<AutomationStatus>('/automation/stop', {
    method: 'POST',
  })
}

export function getAutomationStatus(): Promise<AutomationStatus> {
  return apiFetch<AutomationStatus>('/automation/status')
}

export function getPdfs(): Promise<GeneratedPdf[]> {
  return apiFetch<GeneratedPdf[]>('/pdfs')
}
