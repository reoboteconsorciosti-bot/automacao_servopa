'use client'

import * as React from 'react'
import { Check } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useAutomation } from '@/contexts/automation-context'
import { cn, normalizeName } from '@/lib/utils'

/**
 * Lista fixa dos consultores (abas da planilha) que a automação cobre. O "V"
 * ao lado de um nome só aparece depois de uma confirmação manual — o botão
 * "Esse consultor foi concluído" na section Automação — não só por o nome
 * ter sido digitado no campo. Lê `consultoresConcluidos` direto do
 * AutomationContext (o mesmo Provider montado no AppShell que mantém o
 * estado da automação vivo entre seções), sem precisar de nenhuma chamada de
 * API: é só front-end conversando com front-end através do estado
 * compartilhado.
 */
const CONSULTORES = [
  'Antigos',
  'HS',
  'Antigos 2025/26',
  'Disal - Autobote',
  'Carlos',
  'Eduardo',
  'Felipe Teles',
  'Flavia',
  'Isabeli',
  'Jessica',
  'Jonas',
  'Kamila',
  'Karen',
  'Kassio',
  'Lucas Pietro',
  'Lucas Roques',
  'Marcelo',
  'Murilo',
  'Patricia',
  'Renan',
  'Raphael',
  'Renata',
  'Santarosa',
  'Vinicios',
]

export function ChecklistView() {
  const { consultantName, consultoresConcluidos } = useAutomation()
  const total = consultoresConcluidos.size

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 p-4 sm:p-8">
      <PageHeader
        title="Checklist"
        description='Marca "V" quando o consultor é confirmado como concluído em Automação (botão "Esse consultor foi concluído").'
      />

      <Card className="overflow-hidden p-0">
        <CardHeader className="p-5">
          <CardTitle>Consultores</CardTitle>
          <CardDescription>
            {total} de {CONSULTORES.length} concluídos
            {consultantName.trim() ? ` · em Automação agora: "${consultantName.trim()}"` : ''}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-0 p-0">
          {CONSULTORES.map((nome, idx) => {
            const marcado = consultoresConcluidos.has(normalizeName(nome))
            return (
              <div
                key={nome}
                className={cn(
                  'flex items-center justify-between gap-3 px-5 py-3 text-sm',
                  idx !== CONSULTORES.length - 1 && 'border-b border-border/40',
                  marcado && 'bg-primary/5',
                )}
              >
                <span className={cn('font-medium', marcado ? 'text-foreground' : 'text-muted-foreground')}>
                  {nome}
                </span>
                <span
                  className={cn(
                    'flex size-6 items-center justify-center rounded-full border transition-colors',
                    marcado
                      ? 'border-primary bg-primary text-primary-foreground'
                      : 'border-border text-transparent',
                  )}
                  aria-label={marcado ? `${nome} concluído` : undefined}
                >
                  <Check className="size-4" />
                </span>
              </div>
            )
          })}
        </CardContent>
      </Card>
    </div>
  )
}
