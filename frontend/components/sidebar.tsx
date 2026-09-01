'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import * as React from 'react'
import { AlertTriangle, Bot, History, ListChecks, LogOut, UserRound, Users } from 'lucide-react'
import { cn } from '@/lib/utils'
import { logout as logoutRequest } from '@/services/auth-service'
import type { User } from '@/types'

const navItems = [
  { href: '/usuarios', label: 'Usuários', icon: Users },
  { href: '/automacao', label: 'Automação', icon: Bot },
  { href: '/checklist', label: 'Checklist', icon: ListChecks },
  { href: '/erros-lances', label: 'Erros Lances', icon: AlertTriangle },
  { href: '/historico', label: 'Histórico', icon: History },
]

const STORAGE_KEY = 'servopa.user'

function getStoredUser(): User | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    return JSON.parse(raw) as User
  } catch {
    return null
  }
}

export function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const [user, setUser] = React.useState<User | null>(null)

  React.useEffect(() => {
    setUser(getStoredUser())
    const handler = () => setUser(getStoredUser())
    window.addEventListener('storage', handler)
    return () => window.removeEventListener('storage', handler)
  }, [])

  async function handleLogout() {
    try {
      // Limpa o cookie de sessão HttpOnly no backend — sem isso, ele continua
      // válido mesmo depois de sair (o front-end não consegue apagá-lo sozinho
      // via JavaScript, já que HttpOnly bloqueia justamente esse acesso).
      await logoutRequest()
    } catch {
      // segue com o logout local mesmo se a chamada falhar (ex.: backend offline)
    }
    try {
      localStorage.removeItem(STORAGE_KEY)
      localStorage.removeItem('servopa.authAt')
    } catch {
      // ignore
    }
    setUser(null)
    router.push('/login')
    router.refresh()
  }

  return (
    <aside className="flex w-16 flex-col border-r border-sidebar-border bg-sidebar md:w-60">
      <div className="flex h-16 items-center gap-2.5 border-b border-sidebar-border px-4">
        <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
          <Bot className="size-5" />
        </div>
        <div className="hidden flex-col md:flex">
          <span className="text-sm font-semibold leading-tight text-sidebar-foreground">Servopa</span>
          <span className="text-xs leading-tight text-muted-foreground">Automação</span>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-1 p-2">
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
          const Icon = item.icon
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={isActive ? 'page' : undefined}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                'justify-center md:justify-start',
                isActive
                  ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                  : 'text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-foreground',
              )}
            >
              <Icon className="size-5 shrink-0" />
              <span className="hidden md:inline">{item.label}</span>
            </Link>
          )
        })}
      </nav>

      <div className="border-t border-sidebar-border p-3">
        <div className="hidden flex-col gap-3 md:flex">
          <div className="flex items-center gap-2 rounded-lg bg-sidebar-accent/30 px-3 py-2">
            <div className="flex size-8 items-center justify-center rounded-full bg-sidebar-primary/15 text-sidebar-primary">
              <UserRound className="size-4" />
            </div>
            <div className="min-w-0 flex flex-col">
              <span className="truncate text-sm font-medium text-sidebar-foreground">
                {user?.name ?? 'Visitante'}
              </span>
              <span className="truncate text-xs text-muted-foreground">
                {user?.email ?? 'Não autenticado'}
              </span>
            </div>
          </div>

          <button
            type="button"
            onClick={handleLogout}
            className="flex items-center justify-start gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
            aria-label="Sair"
            title="Sair"
          >
            <LogOut className="size-5 shrink-0" />
            <span>Sair</span>
          </button>
        </div>

        <div className="flex flex-col items-center justify-center gap-1 md:hidden">
          <button
            type="button"
            onClick={handleLogout}
            className="flex size-10 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
            aria-label="Sair"
            title="Sair"
          >
            <LogOut className="size-5" />
          </button>
        </div>
      </div>
    </aside>
  )
}
