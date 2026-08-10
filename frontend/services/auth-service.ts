import { apiFetch } from '@/lib/api-client'
import type { LoginRequest, LoginResponse } from '@/types'

export function login(data: LoginRequest): Promise<LoginResponse> {
  return apiFetch<LoginResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}
