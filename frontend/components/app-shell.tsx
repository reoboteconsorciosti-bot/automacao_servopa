'use client'

import { usePathname, useRouter } from 'next/navigation'
import * as React from 'react'
import { Sidebar } from '@/components/sidebar'
import { AutomationProvider } from '@/contexts/automation-context'

const STORAGE_KEY = 'servopa.user'

/**
 * Wrapper que renderiza a sidebar apenas em rotas autenticadas.
 * Na página /login, renderiza somente o children sem sidebar e sem padding.
 * Nas demais rotas, verifica se há um usuário salvo no localStorage
 * e redireciona para /login caso não exista.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const isLoginPage = pathname === '/login'
  const [checked, setChecked] = React.useState(false)

  React.useEffect(() => {
    if (isLoginPage) {
      setChecked(true)
      return
    }
    // Verifica se o usuário está autenticado
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) {
        router.replace('/login')
        return
      }
    } catch {
      router.replace('/login')
      return
    }
    setChecked(true)
  }, [isLoginPage, router, pathname])

  if (isLoginPage) {
    return <>{children}</>
  }

  // Mostra nada enquanto verifica autenticação (evita flash da sidebar)
  if (!checked) {
    return null
  }

  return (
    <AutomationProvider>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 overflow-x-hidden">{children}</main>
      </div>
    </AutomationProvider>
  )
}
