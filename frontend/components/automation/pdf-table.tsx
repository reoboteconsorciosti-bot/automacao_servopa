'use client'

import * as React from 'react'
import { Download, Eye, FileText, FolderDown, Loader2, Search, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { API_URL } from '@/lib/api-client'
import { deletePdf } from '@/services/automation-service'
import { formatDateBrasilia } from '@/lib/utils'
import type { GeneratedPdf } from '@/types'

function pdfUrl(pdf: GeneratedPdf, download: boolean): string {
  const base = pdf.url.startsWith('http') ? pdf.url : `${API_URL}${pdf.url}`
  return download ? `${base}?download=1` : base
}

function downloadAllUrl(consultant?: string): string {
  const base = `${API_URL}/api/pdfs/download-all`
  return consultant ? `${base}?consultant=${encodeURIComponent(consultant)}` : base
}

/** Agrupa os PDFs por consultor, preservando a ordem (mais recente primeiro) já vinda da API. */
function groupByConsultant(items: GeneratedPdf[]): Map<string, GeneratedPdf[]> {
  const groups = new Map<string, GeneratedPdf[]>()
  for (const pdf of items) {
    const key = pdf.consultantName || 'Sem consultor'
    const group = groups.get(key)
    if (group) {
      group.push(pdf)
    } else {
      groups.set(key, [pdf])
    }
  }
  return groups
}

export function PdfTable({ pdfs }: { pdfs: GeneratedPdf[] }) {
  const [items, setItems] = React.useState(pdfs)
  const [deletingId, setDeletingId] = React.useState<string | null>(null)
  const [consultantFilter, setConsultantFilter] = React.useState('')

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

  const filteredItems = React.useMemo(() => {
    const term = consultantFilter.trim().toLowerCase()
    if (!term) return items
    return items.filter((pdf) => pdf.consultantName?.toLowerCase().includes(term))
  }, [items, consultantFilter])

  const groups = React.useMemo(() => groupByConsultant(filteredItems), [filteredItems])

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 p-10 text-center">
        <FileText className="size-6 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">Nenhum PDF gerado ainda.</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 p-5">
      {/* Busca por consultor + baixar tudo */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:w-72">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Buscar por consultor..."
            value={consultantFilter}
            onChange={(e) => setConsultantFilter(e.target.value)}
            className="pl-9 text-sm"
          />
        </div>
        <Button
          variant="outline"
          size="sm"
          nativeButton={false}
          render={<a href={downloadAllUrl()} target="_blank" rel="noopener noreferrer" />}
        >
          <FolderDown data-icon="inline-start" />
          Baixar todos
        </Button>
      </div>

      {groups.size === 0 ? (
        <div className="flex flex-col items-center gap-2 p-10 text-center">
          <FileText className="size-6 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            Nenhum consultor encontrado para &quot;{consultantFilter}&quot;.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {Array.from(groups.entries()).map(([consultant, consultantPdfs]) => (
            <div
              key={consultant}
              className="flex flex-col gap-3 rounded-lg border border-border/60 bg-muted/20 p-4"
            >
              {/* Cabeçalho do container: consultor + baixar ZIP desse consultor */}
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-col">
                  <span className="font-medium text-foreground">{consultant}</span>
                  <span className="text-xs text-muted-foreground">
                    {consultantPdfs.length} {consultantPdfs.length === 1 ? 'PDF' : 'PDFs'}
                  </span>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  nativeButton={false}
                  render={<a href={downloadAllUrl(consultant)} target="_blank" rel="noopener noreferrer" />}
                >
                  <FolderDown data-icon="inline-start" />
                  Baixar ZIP deste consultor
                </Button>
              </div>

              {/* PDFs desse consultor, cada um com suas próprias ações */}
              <div className="flex flex-col gap-2 border-t border-border/40 pt-3">
                {consultantPdfs.map((pdf) => (
                  <div
                    key={pdf.id}
                    className="flex flex-col gap-2 rounded-md border border-border/60 bg-background p-3 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="flex items-center gap-2 overflow-hidden">
                      <FileText className="size-4 shrink-0 text-muted-foreground" />
                      <div className="flex flex-col overflow-hidden">
                        <span className="truncate text-sm font-medium">{pdf.fileName}</span>
                        <span className="text-xs text-muted-foreground tabular-nums">
                          {formatDateBrasilia(pdf.createdAt)}
                        </span>
                      </div>
                    </div>

                    <div className="flex shrink-0 justify-end gap-2">
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
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
