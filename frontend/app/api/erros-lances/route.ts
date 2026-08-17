import { NextResponse } from 'next/server'
import { deleteErrosLancesFile, parseErrosLances, readErrosLancesContent } from '@/lib/erros-lances'

// Sempre lê o arquivo do disco na hora da requisição — nunca cacheia.
export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

export async function GET() {
  try {
    const content = await readErrosLancesContent()
    if (content === null) {
      return NextResponse.json({ blocos: [] })
    }
    return NextResponse.json({ blocos: parseErrosLances(content) })
  } catch (err) {
    console.error('Erro ao ler erros_lances.txt:', err)
    return NextResponse.json(
      { error: 'Não foi possível ler o arquivo de erros de lances.' },
      { status: 500 },
    )
  }
}

/** Apaga todo o histórico de erros de uma vez (remove o arquivo erros_lances.txt). */
export async function DELETE() {
  try {
    await deleteErrosLancesFile()
    return NextResponse.json({ ok: true })
  } catch (err) {
    console.error('Erro ao excluir erros_lances.txt:', err)
    return NextResponse.json(
      { error: 'Não foi possível excluir o arquivo de erros de lances.' },
      { status: 500 },
    )
  }
}
