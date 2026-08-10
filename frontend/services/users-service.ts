import { apiFetch } from '@/lib/api-client'
import type { User, UserInput } from '@/types'

export function getUsers(): Promise<User[]> {
  return apiFetch<User[]>('/api/users')
}

export function getUser(id: string | number): Promise<User> {
  return apiFetch<User>(`/api/users/${id}`)
}

export function createUser(data: UserInput & { password?: string | null }): Promise<User> {
  return apiFetch<User>('/api/users', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateUser(
  id: string | number,
  data: UserInput & { password?: string | null },
): Promise<User> {
  return apiFetch<User>(`/api/users/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export function deleteUser(id: string | number): Promise<void> {
  return apiFetch<void>(`/api/users/${id}`, {
    method: 'DELETE',
  })
}
