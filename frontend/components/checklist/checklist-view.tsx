'use client'

import * as React from 'react'
import { Check } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useAutomation } from '@/contexts/automation-context'
import { cn } from '@/lib/utils'

/**
 * Lista fixa dos consultores (abas da planilha) que a automação cobre. Marca
 * "V" ao lado de um nome assim que ele bater com o "Nome do consultor"
 * digitado na section Automação — lida direto do AutomationContext (o mesmo
 * Provider montado no AppShell que mantém o estado da automação vivo entre
 * seções), sem precisar de nenhuma chamada de API: é só front-end
 * conversando com front-end através do estado compartilhado.
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

/** Normaliza pra comparar sem se importar com maiúscula/minúscula, acento ou
 * espaço sobrando (ex.: "carlos " digitado deve bater com "Carlos" da lista). */
const DIACRITICOS = /[̀-ͯ]/g

function normalizar(texto: string): string {
  return texto.trim().toLowerCase().normalize('NFD').replace(DIACRITICOS, '')
}

export function ChecklistView() {
  const { consultantName } = useAutomation()
  const nomeAtualNormalizado = normalizar(consultantName)

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 p-4 sm:p-8">
      <PageHeader
        title="Checklist"
        description="Marca automaticamente quando o nome digitado em Automação bate com um consultor da lista."
      />

      <Card className="overflow-hidden p-0">
        <CardHeader className="p-5">
          <CardTitle>Consultores</CardTitle>
          <CardDescription>
            {consultantName.trim()
              ? `Nome atual em Automação: "${consultantName.trim()}"`
              : 'Nenhum nome digitado em Automação no momento.'}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-0 p-0">
          {CONSULTORES.map((nome, idx) => {
            const marcado = nomeAtualNormalizado.length > 0 && normalizar(nome) === nomeAtualNormalizado
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
                  aria-label={marcado ? `${nome} selecionado` : undefined}
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
