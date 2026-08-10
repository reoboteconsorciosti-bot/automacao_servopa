'use client'

import * as React from 'react'
import { Pencil, Plus, Trash2, UserRound } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Modal } from '@/components/ui/modal'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { UserFormModal } from '@/components/users/user-form-modal'
import {
  createUser,
  deleteUser,
  getUsers,
  updateUser,
} from '@/services/users-service'
import type { User, UserInput } from '@/types'

interface UsersViewProps {
  initialUsers: User[]
}

export function UsersView({ initialUsers }: UsersViewProps) {
  const [users, setUsers] = React.useState<User[]>(initialUsers)
  const [loading, setLoading] = React.useState(true)
  const [formOpen, setFormOpen] = React.useState(false)
  const [editing, setEditing] = React.useState<User | null>(null)
  const [deleting, setDeleting] = React.useState<User | null>(null)

  async function loadUsers() {
    try {
      setLoading(true)
      const data = await getUsers()
      setUsers(data)
    } catch (err) {
      console.error('Erro ao carregar usuários:', err)
      setUsers(initialUsers)
    } finally {
      setLoading(false)
    }
  }

  React.useEffect(() => {
    void loadUsers()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function openCreate() {
    setEditing(null)
    setFormOpen(true)
  }

  function openEdit(user: User) {
    setEditing(user)
    setFormOpen(true)
  }

  async function handleSubmit(data: UserInput & { password: string }) {
    try {
      const payload: UserInput & { password?: string | null } = {
        name: data.name,
        email: data.email,
        document: data.document,
      }

      if (editing) {
        if (data.password && data.password.length > 0) {
          payload.password = data.password
        } else {
          payload.password = null
        }
        const updated = await updateUser(editing.id, payload)
        setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)))
      } else {
        payload.password = data.password
        const created = await createUser(payload)
        setUsers((prev) => [created, ...prev])
      }
      setFormOpen(false)
    } catch (err) {
      console.error('Erro ao salvar usuário:', err)
    }
  }

  async function confirmDelete() {
    if (!deleting) return
    try {
      await deleteUser(deleting.id)
      setUsers((prev) => prev.filter((u) => u.id !== deleting.id))
    } catch (err) {
      console.error('Erro ao excluir usuário:', err)
    } finally {
      setDeleting(null)
    }
  }

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6 p-4 sm:p-8">
      <PageHeader
        title="Usuários"
        description="Gerencie os usuários que utilizam a automação."
        action={
          <Button onClick={openCreate}>
            <Plus data-icon="inline-start" />
            Novo usuário
          </Button>
        }
      />

      <Card className="overflow-hidden p-0">
        {users.length === 0 ? (
          <div className="flex flex-col items-center gap-3 p-12 text-center">
            <div className="flex size-12 items-center justify-center rounded-full bg-muted">
              <UserRound className="size-6 text-muted-foreground" />
            </div>
            <div className="flex flex-col gap-1">
              <p className="text-sm font-medium">
                {loading ? 'Carregando usuários...' : 'Nenhum usuário cadastrado'}
              </p>
              <p className="text-sm text-muted-foreground">
                Cadastre o primeiro usuário para começar.
              </p>
            </div>
            <Button variant="outline" onClick={openCreate} disabled={loading}>
              <Plus data-icon="inline-start" />
              Novo usuário
            </Button>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead>Nome</TableHead>
                <TableHead>E-mail</TableHead>
                <TableHead>CPF</TableHead>
                <TableHead>Cadastro</TableHead>
                <TableHead className="text-right">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((user) => (
                <TableRow key={user.id}>
                  <TableCell className="font-medium">{user.name}</TableCell>
                  <TableCell className="text-muted-foreground">{user.email}</TableCell>
                  <TableCell className="text-muted-foreground tabular-nums">
                    {user.document || '—'}
                  </TableCell>
                  <TableCell className="text-muted-foreground tabular-nums">
                    {user.createdAt}
                  </TableCell>
                  <TableCell>
                    <div className="flex justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => openEdit(user)}
                        aria-label={`Editar ${user.name}`}
                      >
                        <Pencil />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => setDeleting(user)}
                        aria-label={`Excluir ${user.name}`}
                        className="text-muted-foreground hover:text-destructive"
                      >
                        <Trash2 />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>

      <UserFormModal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        onSubmit={handleSubmit}
        user={editing}
      />

      <Modal
        open={deleting !== null}
        onClose={() => setDeleting(null)}
        title="Excluir usuário"
        description={
          deleting
            ? `Tem certeza que deseja excluir ${deleting.name}? Esta ação não pode ser desfeita.`
            : ''
        }
      >
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => setDeleting(null)}>
            Cancelar
          </Button>
          <Button variant="destructive" onClick={confirmDelete}>
            Excluir
          </Button>
        </div>
      </Modal>
    </div>
  )
}
