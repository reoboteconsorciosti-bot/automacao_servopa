'use client'

import * as React from 'react'
import { Modal } from '@/components/ui/modal'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import type { User, UserInput } from '@/types'

interface UserFormModalProps {
  open: boolean
  onClose: () => void
  onSubmit: (data: UserInput & { password: string }) => void
  user?: User | null
}

const emptyForm: UserInput & { password: string } = {
  name: '',
  email: '',
  password: '',
}

export function UserFormModal({ open, onClose, onSubmit, user }: UserFormModalProps) {
  const [form, setForm] = React.useState(emptyForm)

  React.useEffect(() => {
    if (open) {
      setForm(
        user
          ? {
              name: user.name,
              email: user.email,
              password: '',
            }
          : emptyForm,
      )
    }
  }, [open, user])

  function handleChange(field: keyof typeof emptyForm) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((prev) => ({ ...prev, [field]: e.target.value }))
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    onSubmit(form)
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={user ? 'Editar usuário' : 'Novo usuário'}
      description={
        user
          ? 'Atualize os dados do usuário. Deixe a senha em branco para manter a atual.'
          : 'Preencha os dados para cadastrar um novo usuário.'
      }
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <Label htmlFor="name">Nome</Label>
          <Input
            id="name"
            name="name"
            value={form.name}
            onChange={handleChange('name')}
            placeholder="Nome completo"
            required
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="email">E-mail</Label>
          <Input
            id="email"
            name="email"
            type="email"
            value={form.email}
            onChange={handleChange('email')}
            placeholder="email@servopa.com.br"
            required
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="password">{user ? 'Senha (opcional)' : 'Senha'}</Label>
          <Input
            id="password"
            name="password"
            type="password"
            value={form.password}
            onChange={handleChange('password')}
            placeholder={user ? 'Deixe em branco para manter' : 'Mínimo 4 caracteres'}
            required={!user}
          />
        </div>
        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit">{user ? 'Salvar alterações' : 'Cadastrar'}</Button>
        </div>
      </form>
    </Modal>
  )
}
