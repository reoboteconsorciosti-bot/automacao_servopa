import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

const DIACRITICOS = /[̀-ͯ]/g

/** Normaliza um nome pra comparar sem se importar com maiúscula/minúscula,
 * acento ou espaço sobrando (ex.: "carlos " digitado deve bater com "Carlos"
 * da lista de consultores). Usado pra casar o nome digitado em Automação com
 * a lista fixa da Checklist. */
export function normalizeName(texto: string): string {
  return texto.trim().toLowerCase().normalize('NFD').replace(DIACRITICOS, '')
}

/**
 * Formata uma string de data/hora ISO (ex.: "2026-08-27T17:58:38.034+00:00",
 * como vem do backend em UTC) para o horário de Brasília (America/Sao_Paulo,
 * UTC-3) no formato "dd/mm/aaaa hh:mm:ss".
 *
 * A conversão de fuso usa Intl (só a API do JS sabe as regras de fuso/horário
 * de verão de cada região); o REARRANJO pro formato brasileiro é feito por
 * regex + replace sobre a string já convertida, capturando mês/dia/ano/hora
 * do formato "M/D/AAAA, HH:MM:SS" (locale en-US, previsível) e remontando na
 * ordem dd/mm/aaaa com zero à esquerda.
 */
const PADRAO_DATA_EN_US = /^(\d{1,2})\/(\d{1,2})\/(\d{4}),\s*(\d{2}:\d{2}:\d{2})$/

export function formatDateBrasilia(isoString: string): string {
  const date = new Date(isoString)
  if (isNaN(date.getTime())) return isoString

  const emBrasilia = date.toLocaleString('en-US', {
    timeZone: 'America/Sao_Paulo',
    hour12: false,
  })
  // emBrasilia chega como "M/D/AAAA, HH:MM:SS" — ex.: "8/27/2026, 14:58:38"

  // Se o padrão não bater por algum motivo inesperado, .replace() devolve a
  // string original sem alterar — ainda utilizável (já no fuso certo), só
  // não reordenada.
  return emBrasilia.replace(
    PADRAO_DATA_EN_US,
    (_match, mes: string, dia: string, ano: string, hora: string) =>
      `${dia.padStart(2, '0')}/${mes.padStart(2, '0')}/${ano} ${hora}`,
  )
}
