/**
 * Base URL da API REST (backend desenvolvido separadamente).
 * Configurada via variável de ambiente NEXT_PUBLIC_API_URL.
 */
const RAW_API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
export const API_URL = RAW_API_URL.endsWith('/') ? RAW_API_URL.slice(0, -1) : RAW_API_URL

/**
 * Traduz mensagens de validação comuns do Pydantic (inglês → português).
 */
function translateValidationMessage(msg: string): string {
  const translations: [RegExp, string][] = [
    [/String should have at least (\d+) characters?/i, 'Mínimo $1 caracteres'],
    [/String should have at most (\d+) characters?/i, 'Máximo $1 caracteres'],
    [/value is not a valid email address/i, 'E-mail inválido'],
    [/Field required/i, 'Campo obrigatório'],
    [/Input should be a valid string/i, 'Valor deve ser um texto válido'],
  ]
  for (const [pattern, replacement] of translations) {
    if (pattern.test(msg)) {
      return msg.replace(pattern, replacement)
    }
  }
  return msg
}

/**
 * Wrapper simples em torno do fetch para padronizar as chamadas à API.
 * - Remove barras duplicadas na URL final
 * - Trata respostas 204 No Content (DELETE, etc.) sem tentar parsear JSON
 * - Lança erro com status + mensagem em caso de response.ok === false
 */
export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const safePath = path.startsWith('/') ? path : `/${path}`
  const url = `${API_URL}${safePath}`

  const response = await fetch(url, {
    // Necessário para o cookie de sessão HttpOnly (definido em /api/auth/login)
    // ser enviado/recebido nas chamadas — sem isso o navegador não anexa o
    // cookie em requisições cross-origin (frontend e backend em portas/domínios
    // diferentes), mesmo com o backend permitindo credentials no CORS.
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  })

  if (!response.ok) {
    const text = await response.text().catch(() => '')
    let detail = response.statusText
    if (text) {
      try {
        const json = JSON.parse(text)
        if (typeof json.detail === 'string') detail = json.detail
        else if (Array.isArray(json.detail) && json.detail.length > 0) {
          const first = json.detail[0]
          detail = typeof first?.msg === 'string' ? first.msg : text
        } else {
          detail = text
        }
      } catch {
        detail = text
      }
    }
    // Traduz mensagens de validação comuns do Pydantic (inglês → português)
    detail = translateValidationMessage(detail)
    throw new Error(`Erro na requisição ${response.status}: ${detail}`)
  }

  if (response.status === 204) {
    return undefined as unknown as T
  }

  return response.json() as Promise<T>
}
