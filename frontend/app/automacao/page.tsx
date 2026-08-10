import { AutomationView } from '@/components/automation/automation-view'
import { mockPdfs } from '@/lib/mock-data'

export default function AutomacaoPage() {
  return <AutomationView pdfs={mockPdfs} />
}
