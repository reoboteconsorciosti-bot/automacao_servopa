'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import { Lock, Mail, LogIn, Bot, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { login } from '@/services/auth-service'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = React.useState('')
  const [password, setPassword] = React.useState('')
  const [submitting, setSubmitting] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
  }

  async function handleLogin() {
    setError(null)
    if (!email || !password) {
      setError('Preencha e-mail e senha.')
      return
    }
    try {
      setSubmitting(true)
      const result = await login({ email, password })
      if (result.ok && result.user) {
        // Backend retorna created_at (snake_case) — frontend espera createdAt (camelCase)
        const backendUser = result.user as unknown as Record<string, unknown>
        const mappedUser = {
          id: backendUser.id as string | number,
          name: (backendUser.name as string) ?? '',
          email: (backendUser.email as string) ?? '',
          document: (backendUser.document as string | null) ?? null,
          createdAt: (backendUser.createdAt as string) ?? (backendUser.created_at as string) ?? '',
        }
        try {
          localStorage.setItem('servopa.user', JSON.stringify(mappedUser))
          localStorage.setItem('servopa.authAt', String(Date.now()))
        } catch {
          // ignore
        }
        router.push('/automacao')
        router.refresh()
      } else {
        setError(result.message || 'Falha ao realizar login.')
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Erro ao conectar com o servidor.'
      setError(msg)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-background via-background to-muted/40 p-4">
      <Card className="w-full max-w-md overflow-hidden border-border/60 shadow-2xl shadow-primary/5">
        <div className="flex flex-col items-center gap-3 border-b border-sidebar-border bg-sidebar/40 px-8 py-10 text-center">
          <div className="flex size-16 items-center justify-center rounded-2xl bg-sidebar-primary text-sidebar-primary-foreground shadow-lg shadow-primary/30">
            <Bot className="size-8" />
          </div>
          <div className="flex flex-col gap-1">
            <h1 className="text-xl font-semibold tracking-tight text-sidebar-foreground">
              Servopa Consórcios
            </h1>
            <p className="text-sm text-muted-foreground">
              Painel de Automação de Lances
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-5 px-8 py-8">
          <div className="flex flex-col gap-2">
            <Label htmlFor="email">E-mail</Label>
            <div className="relative">
              <Mail className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="email"
                name="email"
                type="email"
                placeholder="email@servopa.com.br"
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="pl-10"
                required
              />
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="password">Senha</Label>
            <div className="relative">
              <Lock className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="password"
                name="password"
                type="password"
                placeholder="Mínimo 4 caracteres"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    void handleLogin()
                  }
                }}
                className="pl-10"
                required
              />
            </div>
          </div>

          {error && (
            <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {error}
            </div>
          )}

          <Button
            type="button"
            onClick={handleLogin}
            disabled={submitting}
            className="mt-2 w-full gap-2"
          >
            {submitting ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Entrando...
              </>
            ) : (
              <>
                <LogIn className="size-4" />
                Entrar
              </>
            )}
          </Button>
        </form>
      </Card>
    </div>
  )
}
