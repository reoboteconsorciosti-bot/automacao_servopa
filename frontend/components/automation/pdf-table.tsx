'use client'

import * as React from 'react'
import { Download, Eye, FileText, FolderDown, Loader2, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { API_URL } from '@/lib/api-client'
import { deletePdf } from '@/services/automation-service'
import type { GeneratedPdf } from '@/types'

function pdfUrl(pdf: GeneratedPdf, download: boolean): string {
  const base = pdf.url.startsWith('http') ? pdf.url : `${API_URL}${pdf.url}`
  return download ? `${base}?download=1` : base
}

const downloadAllUrl = `${API_URL}/api/pdfs/download-all`

export function PdfTable({ pdfs }: { pdfs: GeneratedPdf[] }) {
  const [items, setItems] = React.useState(pdfs)
  const [deletingId, setDeletingId] = React.useState<string | null>(null)

  // Mantém sincronizado caso a lista vinda do servidor mude (ex.: navegação/refresh).
  React.useEffect(() => {
    setItems(pdfs)
  }, [pdfs])

  async function handleDelete(pdf: GeneratedPdf) {
    if (!window.confirm(`Excluir o PDF "${pdf.fileName}"? Essa ação não pode ser desfeita.`)) {
      return
    }
    setDeletingId(pdf.id)
    try {
      await deletePdf(pdf.id)
      setItems((prev) => prev.filter((p) => p.id !== pdf.id))
    } catch (err) {
      console.error('Erro ao excluir PDF:', err)
      window.alert('Não foi possível excluir o PDF. Tente novamente.')
    } finally {
      setDeletingId(null)
    }
  }

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 p-10 text-center">
        <FileText className="size-6 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">Nenhum PDF gerado ainda.</p>
      </div>
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          <TableHead>Nome do PDF</TableHead>
          <TableHead>Consultor</TableHead>
          <TableHead>Data</TableHead>
          <TableHead className="text-right">
            <div className="flex items-center justify-end gap-2">
              Ações
              <Button
                variant="outline"
                size="xs"
                nativeButton={false}
                render={<a href={downloadAllUrl} target="_blank" rel="noopener noreferrer" />}
              >
                <FolderDown data-icon="inline-start" />
                Baixar todos
              </Button>
            </div>
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((pdf) => (
          <TableRow key={pdf.id}>
            <TableCell>
              <span className="flex items-center gap-2 font-medium">
                <FileText className="size-4 shrink-0 text-muted-foreground" />
                {pdf.fileName}
              </span>
            </TableCell>
            <TableCell className="text-muted-foreground">{pdf.consultantName}</TableCell>
            <TableCell className="text-muted-foreground tabular-nums">{pdf.createdAt}</TableCell>
            <TableCell>
              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  nativeButton={false}
                  render={<a href={pdfUrl(pdf, false)} target="_blank" rel="noopener noreferrer" />}
                >
                  <Eye data-icon="inline-start" />
                  Visualizar
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  nativeButton={false}
                  render={<a href={pdfUrl(pdf, true)} target="_blank" rel="noopener noreferrer" />}
                >
                  <Download data-icon="inline-start" />
                  Download
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  aria-label="Excluir PDF"
                  onClick={() => handleDelete(pdf)}
                  disabled={deletingId === pdf.id}
                  className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                >
                  {deletingId === pdf.id ? (
                    <Loader2 data-icon="inline-start" className="animate-spin" />
                  ) : (
                    <Trash2 data-icon="inline-start" />
                  )}
                  Excluir
                </Button>
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
