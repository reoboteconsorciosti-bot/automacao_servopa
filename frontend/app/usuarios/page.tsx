import { UsersView } from '@/components/users/users-view'
import { mockUsers } from '@/lib/mock-data'

export default function UsuariosPage() {
  return <UsersView initialUsers={mockUsers} />
}
