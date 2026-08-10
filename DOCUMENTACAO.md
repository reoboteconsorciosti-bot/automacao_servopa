# Painel Servopa Consórcios - Documentação

## Visão Geral

Este projeto é um **Painel de Controle para Automação de Lances de Crédito** da Servopa Consórcios. Trata-se de uma aplicação web monorepo composta por um frontend em Next.js e um backend (reservado) para execução de automações via Selenium e geração de PDFs.

**Nome do projeto:** consultor-automacao  
**Versão atual:** 0.1.0  
**Idioma da interface:** Português (Brasil)

---

## Estrutura do Monorepo

```
painel-servopa-consorcios/
├── backend/                      # Pasta reservada para a API REST (ainda não implementada)
│   └── README.md                 # Documentação dos endpoints esperados
├── frontend/                     # Aplicação Next.js (painel web)
│   ├── app/                      # App Router (Next.js 16)
│   │   ├── automacao/page.tsx    # Página de automação
│   │   ├── usuarios/page.tsx     # Página de usuários
│   │   ├── globals.css           # Estilos globais + tema Tailwind v4
│   │   ├── layout.tsx            # Layout raiz (sidebar + main)
│   │   └── page.tsx              # Redireciona para /automacao
│   ├── components/
│   │   ├── automation/           # Componentes do módulo de automação
│   │   ├── users/                # Componentes do módulo de usuários
│   │   ├── ui/                   # Componentes base shadcn/ui
│   │   ├── page-header.tsx       # Cabeçalho padrão das páginas
│   │   └── sidebar.tsx           # Navegação lateral
│   ├── lib/
│   │   ├── api-client.ts         # Wrapper fetch para integração com API
│   │   ├── mock-data.ts          # Dados mockados (desenvolvimento)
│   │   └── utils.ts              # Funções utilitárias (cn, etc.)
│   ├── services/
│   │   ├── automation-service.ts # Funções de integração - Automação
│   │   └── users-service.ts      # Funções de integração - Usuários
│   ├── types/index.ts            # Tipos TypeScript compartilhados
│   ├── public/                   # Assets estáticos
│   ├── Dockerfile                # Build Docker multi-stage
│   ├── next.config.mjs           # Configurações Next.js
│   ├── tsconfig.json             # Configurações TypeScript
│   └── package.json              # Dependências do frontend
├── package.json                  # Workspace root (pnpm)
├── pnpm-workspace.yaml           # Configuração do workspace
└── .gitignore
```

---

## Stack Tecnológica

### Frontend
| Tecnologia | Versão | Descrição |
|---|---|---|
| **Next.js** | 16.3.0 | Framework React com App Router e Server Components |
| **React** | 19 | Biblioteca de UI |
| **TypeScript** | 5.7.3 | Tipagem estática |
| **Tailwind CSS** | 4.3.3 | Framework CSS utilitário |
| **shadcn/ui** | 4.8.0 | Componentes de UI reutilizáveis |
| **lucide-react** | 1.16.0 | Biblioteca de ícones |
| **@base-ui/react** | 1.5.0 | Componentes sem estilo (headless) |
| **@vercel/analytics** | 1.6.1 | Analytics em produção |

### Gerenciamento de Pacotes
- **pnpm** (via corepack) - Gerenciador de pacotes e workspace

### Containerização
- **Docker** - Imagem multi-stage baseada em `node:20-alpine`

---

## Instalação e Configuração

### Pré-requisitos
- Node.js 20+
- pnpm (instalado via `corepack enable`)

### Passos de Instalação

1. **Clonar o repositório**
```bash
git clone <url-do-repositorio>
cd painel-servopa-consorcios
```

2. **Instalar dependências do workspace**
```bash
pnpm install
```

3. **Configurar variáveis de ambiente**
   - Copiar `frontend/.env.example` para `frontend/.env.local`
   - Ajustar `NEXT_PUBLIC_API_URL` para a URL do backend

```bash
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Scripts Disponíveis (Root)

Executados a partir da raiz do projeto:

| Comando | Descrição |
|---|---|
| `pnpm dev` | Inicia o frontend em modo desenvolvimento |
| `pnpm build` | Faz o build de produção do frontend |
| `pnpm start` | Inicia o servidor em modo produção |
| `pnpm lint` | Executa lint no frontend |

### Scripts (Frontend)

| Comando | Descrição |
|---|---|
| `next dev` | Dev server em `http://localhost:3000` |
| `next build` | Build otimizado + standalone para Docker |
| `next start` | Servidor de produção |
| `eslint .` | Análise estática de código |

---

## Docker

O projeto inclui um `Dockerfile` multi-stage em `frontend/Dockerfile`:

### Estágios
1. **deps** - Instala dependências com `pnpm install --frozen-lockfile`
2. **builder** - Executa `pnpm build` com `output: 'standalone'`
3. **runner** - Imagem mínima de produção com usuário não-root

### Build e Execução

```bash
cd frontend
docker build -t servopa-automacao .
docker run -p 3000:3000 -e NEXT_PUBLIC_API_URL=http://sua-api:8000 servopa-automacao
```

---

## Módulos da Aplicação

### 1. Automação (`/automacao`)

Página principal do painel. Permite configurar e executar a automação de lances de crédito.

**Componentes:**
- [automation-view.tsx](file:///c:/Users/Notebook%20Lenovo/Downloads/painel-servopa-consorcios/frontend/components/automation/automation-view.tsx) - Componente principal
- [status-indicator.tsx](file:///c:/Users/Notebook%20Lenovo/Downloads/painel-servopa-consorcios/frontend/components/automation/status-indicator.tsx) - Indicador visual de status
- [live-view.tsx](file:///c:/Users/Notebook%20Lenovo/Downloads/painel-servopa-consorcios/frontend/components/automation/live-view.tsx) - Área de visualização ao vivo
- [pdf-table.tsx](file:///c:/Users/Notebook%20Lenovo/Downloads/painel-servopa-consorcios/frontend/components/automation/pdf-table.tsx) - Tabela de PDFs gerados

**Funcionalidades:**
- Inserir nome do consultor
- Selecionar navegador (Firefox / Chrome)
- Iniciar / Reiniciar automação
- Acompanhar status em tempo real (`idle` | `running` | `finished` | `error`)
- Visualizar e baixar PDFs gerados

### 2. Usuários (`/usuarios`)

Gestão de usuários que têm acesso ao painel.

**Componentes:**
- [users-view.tsx](file:///c:/Users/Notebook%20Lenovo/Downloads/painel-servopa-consorcios/frontend/components/users/users-view.tsx) - Lista/tabela de usuários
- [user-form-modal.tsx](file:///c:/Users/Notebook%20Lenovo/Downloads/painel-servopa-consorcios/frontend/components/users/user-form-modal.tsx) - Modal de criação/edição

**Funcionalidades:**
- Listar usuários cadastrados
- Criar novo usuário (nome, e-mail, CPF)
- Editar usuário existente
- Excluir usuário (com confirmação)

### 3. Componentes UI Base (shadcn)

Localizados em `frontend/components/ui/`:

| Componente | Arquivo |
|---|---|
| Badge | [badge.tsx](file:///c:/Users/Notebook%20Lenovo/Downloads/painel-servopa-consorcios/frontend/components/ui/badge.tsx) |
| Button | [button.tsx](file:///c:/Users/Notebook%20Lenovo/Downloads/painel-servopa-consorcios/frontend/components/ui/button.tsx) |
| Card | [card.tsx](file:///c:/Users/Notebook%20Lenovo/Downloads/painel-servopa-consorcios/frontend/components/ui/card.tsx) |
| Input | [input.tsx](file:///c:/Users/Notebook%20Lenovo/Downloads/painel-servopa-consorcios/frontend/components/ui/input.tsx) |
| Label | [label.tsx](file:///c:/Users/Notebook%20Lenovo/Downloads/painel-servopa-consorcios/frontend/components/ui/label.tsx) |
| Modal | [modal.tsx](file:///c:/Users/Notebook%20Lenovo/Downloads/painel-servopa-consorcios/frontend/components/ui/modal.tsx) |
| Switch | [switch.tsx](file:///c:/Users/Notebook%20Lenovo/Downloads/painel-servopa-consorcios/frontend/components/ui/switch.tsx) |
| Table | [table.tsx](file:///c:/Users/Notebook%20Lenovo/Downloads/painel-servopa-consorcios/frontend/components/ui/table.tsx) |

---

## Tipos Compartilhados

Definidos em [types/index.ts](file:///c:/Users/Notebook%20Lenovo/Downloads/painel-servopa-consorcios/frontend/types/index.ts):

```typescript
// Usuários
interface User {
  id: string
  name: string
  email: string
  document: string
  createdAt: string
}

type UserInput = Omit<User, 'id' | 'createdAt'>

// Automação
type AutomationStatusValue = 'idle' | 'running' | 'finished' | 'error'

interface AutomationStatus {
  status: AutomationStatusValue
  message?: string
  updatedAt: string
}

interface BidQuota {
  id: string
  quota: string       // Número/identificação da cota
  bidValue: string    // Valor do lance
}

interface AutomationConfig {
  consultantName: string
  bids: BidQuota[]
}

interface GeneratedPdf {
  id: string
  fileName: string
  consultantName: string
  createdAt: string
  url: string
}
```

---

## Integração com Backend (API)

O backend ainda **não foi implementado**. O frontend está preparado para integração via REST.

### Cliente HTTP

[lib/api-client.ts](file:///c:/Users/Notebook%20Lenovo/Downloads/painel-servopa-consorcios/frontend/lib/api-client.ts) contém:
- `API_URL` - Base URL via `NEXT_PUBLIC_API_URL`
- `apiFetch<T>()` - Wrapper tipado em torno do `fetch`

### Endpoints Esperados

Conforme [backend/README.md](file:///c:/Users/Notebook%20Lenovo/Downloads/painel-servopa-consorcios/backend/README.md):

#### Usuários
| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/users` | Lista todos os usuários |
| `POST` | `/users` | Cria novo usuário |
| `GET` | `/users/:id` | Obtém um usuário |
| `PUT` | `/users/:id` | Atualiza usuário |
| `DELETE` | `/users/:id` | Remove usuário |

#### Automação
| Método | Endpoint | Descrição |
|---|---|---|
| `POST` | `/automation/start` | Inicia automação (recebe `AutomationConfig`) |
| `POST` | `/automation/stop` | Para a automação em execução |
| `GET` | `/automation/status` | Retorna status atual |
| `GET` | `/pdfs` | Lista PDFs gerados |

### Services Prontos

- [users-service.ts](file:///c:/Users/Notebook%20Lenovo/Downloads/painel-servopa-consorcios/frontend/services/users-service.ts) - `getUsers`, `getUser`, `createUser`, `updateUser`, `deleteUser`
- [automation-service.ts](file:///c:/Users/Notebook%20Lenovo/Downloads/painel-servopa-consorcios/frontend/services/automation-service.ts) - `startAutomation`, `stopAutomation`, `getAutomationStatus`, `getPdfs`

> **Nota:** Atualmente, as views utilizam dados mockados de `lib/mock-data.ts`. Quando o backend estiver pronto, basta substituir pelas chamadas dos services.

---

## Tema e Design System

### Cores
- **Primária:** Roxo (`oklch(0.52 0.19 258)` - light / `0.62` - dark)
- **Tema:** Suporte nativo a Light e Dark mode (via `prefers-color-scheme` + classe `.dark`)
- **Fonte:** Geist Sans + Geist Mono (carregadas do Google Fonts via `next/font`)

### Configuração Tailwind v4
Arquivo: [globals.css](file:///c:/Users/Notebook%20Lenovo/Downloads/painel-servopa-consorcios/frontend/app/globals.css)

- `@custom-variant dark` - Variante para tema escuro
- `@theme inline` - Tokens de design (cores, fontes, raios de borda)
- Variáveis CSS para sidebar, cards, charts, etc.

### Cabeçalhos de Segurança
Configurados em [next.config.mjs](file:///c:/Users/Notebook%20Lenovo/Downloads/painel-servopa-consorcios/frontend/next.config.mjs):
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `X-Frame-Options: SAMEORIGIN`
- `Permissions-Policy` - Bloqueia câmera, microfone e geolocalização

---

## Workspace (pnpm)

Configuração em [pnpm-workspace.yaml](file:///c:/Users/Notebook%20Lenovo/Downloads/painel-servopa-consorcios/pnpm-workspace.yaml):

```yaml
packages:
  - frontend
```

- Comandos executados via `pnpm --filter frontend <script>`
- Override global para `hono@4.12.25` (preparado para futura adição do backend)

---

## Convenções de Código

- **Import path alias:** `@/*` mapeia para `./*` (frontend)
- **Componentes cliente:** Usam `'use client'` no topo
- **Estilização:** Tailwind CSS + `cn()` para merge de classes
- **Ícones:** Sempre via `lucide-react`
- **Formulários:** Controle local via `useState`

---

## Próximos Passos (Roadmap)

- [ ] Implementar backend (API REST) com os endpoints listados
- [ ] Integrar Selenium para automação dos lances
- [ ] Implementar geração e armazenamento de PDFs
- [ ] Substituir dados mockados (`mock-data.ts`) por chamadas reais aos services
- [ ] Adicionar autenticação e autorização (login)
- [ ] Implementar streaming/websocket para visualização ao vivo da automação
- [ ] Adicionar validação de formulários (ex: Zod + React Hook Form)
- [ ] Adicionar pipeline CI/CD
- [ ] Deploy via container no Easypanel

---

## Observações Importantes

1. **Next.js `output: 'standalone'`** - O build produz uma versão otimizada para Docker, copiada manualmente no Dockerfile.
2. **`typescript.ignoreBuildErrors: true`** - Erros de tipo não bloqueiam o build. Recomenda-se ajustar antes da produção.
3. **`images.unoptimized: true`** - Imagens não são otimizadas pelo Next (compatibilidade com ambientes restritos).
4. **Vercel Analytics** - Carregado apenas em `NODE_ENV === 'production'.
