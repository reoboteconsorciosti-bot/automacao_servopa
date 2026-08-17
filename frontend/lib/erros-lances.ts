import { readFile, unlink } from 'fs/promises'
import path from 'path'
import type { ErroLanceBloco, ErroLanceItem } from '@/types'

/**
 * `erros_lances.txt` é escrito pelo backend Python (engine.py -> salvar_log_erros)
 * na raiz do monorepo, um nível acima de `frontend/`. Em `next dev`/`next start`,
 * `process.cwd()` aponta para `frontend/`, então subimos um nível.
 */
const CANDIDATOS = [
  path.join(process.cwd(), '..', 'erros_lances.txt'),
  path.join(process.cwd(), 'erros_lances.txt'),
]

export async function readErrosLancesContent(): Promise<string | null> {
  for (const candidato of CANDIDATOS) {
    try {
      return await readFile(candidato, 'utf-8')
    } catch {
      continue
    }
  }
  return null
}

/** Apaga o arquivo erros_lances.txt (limpa todo o histórico de erros de uma vez). */
export async function deleteErrosLancesFile(): Promise<boolean> {
  let deletedAny = false
  for (const candidato of CANDIDATOS) {
    try {
      await unlink(candidato)
      deletedAny = true
    } catch {
      continue
    }
  }
  return deletedAny
}

/**
 * Cada execução com erro gera um bloco assim, separado por linhas de "=":
 *
 * ======================================================================
 * Consultor: Patricia
 * Data/Hora: 12/08/2026 15:31:48
 * Total de cotas com erro: 1
 * ----------------------------------------------------------------------
 * Cota: 1560,1546,3
 *   Status : ERRO_BENIGNO
 *   Motivo : A cota possui Lance Fidelidade e não pode ser processada.
 * ======================================================================
 */
export function parseErrosLances(content: string): ErroLanceBloco[] {
  const blocos = content
    .split(/={5,}/g)
    .map((b) => b.trim())
    .filter(Boolean)

  const resultado: ErroLanceBloco[] = []

  for (const bloco of blocos) {
    const consultantMatch = bloco.match(/Consultor:\s*(.+)/)
    if (!consultantMatch) continue

    const dateMatch = bloco.match(/Data\/Hora:\s*(.+)/)
    const totalMatch = bloco.match(/Total de cotas com erro:\s*(\d+)/)

    const errors: ErroLanceItem[] = []
    const cotaRegex = /Cota:\s*(.+?)\s*\n\s*Status\s*:\s*(.+?)\s*\n\s*Motivo\s*:\s*(.+)/g
    let match: RegExpExecArray | null
    while ((match = cotaRegex.exec(bloco)) !== null) {
      errors.push({
        cota: match[1].trim(),
        status: match[2].trim(),
        motivo: match[3].trim(),
      })
    }

    resultado.push({
      consultant: consultantMatch[1].trim(),
      dateTime: dateMatch ? dateMatch[1].trim() : '',
      total: totalMatch ? Number(totalMatch[1]) : errors.length,
      errors,
    })
  }

  // Bloco mais recente primeiro (o arquivo é append-only, cresce do mais antigo pro mais novo).
  return resultado.reverse()
}
