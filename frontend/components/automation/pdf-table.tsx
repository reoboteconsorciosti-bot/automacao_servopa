import { Download, Eye, FileText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { GeneratedPdf } from '@/types'

export function PdfTable({ pdfs }: { pdfs: GeneratedPdf[] }) {
  if (pdfs.length === 0) {
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
          <TableHead className="text-right">Ações</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {pdfs.map((pdf) => (
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
                <Button variant="outline" size="sm">
                  <Eye data-icon="inline-start" />
                  Visualizar
                </Button>
                <Button variant="outline" size="sm">
                  <Download data-icon="inline-start" />
                  Download
                </Button>
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
