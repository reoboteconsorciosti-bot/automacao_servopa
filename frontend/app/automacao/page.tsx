import { AutomationView } from '@/components/automation/automation-view'
import { getPdfs } from '@/services/automation-service'

export const dynamic = 'force-dynamic'

export default async function AutomacaoPage() {
  const pdfs = await getPdfs().catch(() => [])
  return <AutomationView pdfs={pdfs} />
}
