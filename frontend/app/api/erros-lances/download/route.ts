import { NextResponse } from 'next/server'
import { readErrosLancesContent } from '@/lib/erros-lances'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

/** Devolve o conteúdo bruto de erros_lances.txt, exatamente como está em disco (UTF-8),
 * como download de arquivo — sem nenhum parsing/reformatação. */
export async function GET() {
  const content = await readErrosLancesContent()
  if (content === null) {
    return NextResponse.json(
      { error: 'Arquivo erros_lances.txt não encontrado.' },
      { status: 404 },
    )
  }

  return new NextResponse(content, {
    status: 200,
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
      'Content-Disposition': 'attachment; filename="erros_lances.txt"',
    },
  })
}
