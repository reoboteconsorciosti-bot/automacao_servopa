import type { GeneratedPdf, User } from '@/types'

export const mockUsers: User[] = [
  {
    id: '1',
    name: 'Ana Beatriz Souza',
    email: 'ana.souza@servopa.com.br',
    createdAt: '2026-01-12',
  },
  {
    id: '2',
    name: 'Carlos Henrique Lima',
    email: 'carlos.lima@servopa.com.br',
    createdAt: '2026-02-03',
  },
  {
    id: '3',
    name: 'Fernanda Oliveira',
    email: 'fernanda.oliveira@servopa.com.br',
    createdAt: '2026-02-20',
  },
  {
    id: '4',
    name: 'João Pedro Martins',
    email: 'joao.martins@servopa.com.br',
    createdAt: '2026-03-08',
  },
]

export const mockPdfs: GeneratedPdf[] = []
