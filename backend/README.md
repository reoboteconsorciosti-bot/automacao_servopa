# Backend

Pasta reservada para o servidor da aplicação (API REST).

O frontend em `../frontend` consome esta API através dos services em
`frontend/services/*`, usando a variável de ambiente `NEXT_PUBLIC_API_URL`.

Endpoints esperados pelo frontend:

- `GET    /users`               - lista de usuários
- `POST   /users`               - cria usuário
- `PUT    /users/:id`           - atualiza usuário
- `DELETE /users/:id`           - remove usuário
- `POST   /automation/start`    - inicia a automação (recebe nome do consultor e cotas)
- `GET    /automation/status`   - status atual da automação
- `GET    /automation/pdfs`     - PDFs gerados
