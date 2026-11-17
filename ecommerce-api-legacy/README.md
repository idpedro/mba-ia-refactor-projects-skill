# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express, refatorada pela skill `refactor-arch` para uma arquitetura em camadas (MVC). O relatório da auditoria está em `reports/audit-project-2.md`.

## Como rodar

```bash
npm install
ADMIN_TOKEN=troque-este-token npm start
```

Se o `npm` bloquear o script de instalação do `sqlite3`, rode `npm install-scripts approve sqlite3`. A permissão fica registrada em `allowScripts` no `package.json`.

A aplicação sobe em `http://127.0.0.1:3000` (somente loopback por padrão). O banco SQLite é em memória e carrega as seeds no boot.

Exemplos de requisições estão em `api.http`.

## Configuração

Todas as variáveis são opcionais; veja `.env.example`.

| Variável | Padrão | Uso |
|---|---|---|
| `PORT` | `3000` | Porta HTTP |
| `HOST` | `127.0.0.1` | Interface de escuta. `0.0.0.0` expõe a API na rede |
| `DB_PATH` | `:memory:` | Caminho do SQLite; um arquivo persiste os dados |
| `PAYMENT_GATEWAY_KEY` | vazio | Chave do gateway de pagamento |
| `ADMIN_TOKEN` | vazio | Token das rotas administrativas |
| `LOG_LEVEL` | `info` | `debug`, `info`, `warn` ou `error` |

## Endpoints

| Método | Rota | Acesso |
|---|---|---|
| `POST` | `/api/checkout` | Público |
| `GET` | `/api/admin/financial-report` | Admin |
| `DELETE` | `/api/users/:id` | Admin |

As rotas de admin exigem `Authorization: Bearer <ADMIN_TOKEN>`. Sem o header ou com token inválido a resposta é `401`. Com `ADMIN_TOKEN` vazio elas respondem `401` a todos.

Erros continuam em texto puro, com os mesmos textos e status de antes (`Bad Request`, `Curso não encontrado`, `Pagamento recusado`). Um erro inesperado responde `500 Erro interno` e o detalhe vai só para o log.

## Estrutura

```
src/
├── app.js                  # composition root
├── config/index.js
├── errors.js
├── database/               # connection (promisificada, com transação), schema, seed
├── models/                 # user, course, enrollment, payment, auditLog
├── services/               # password (scrypt), payment, report
├── controllers/            # checkout, report, user
├── validators/             # checkout.validator.js
├── routes/                 # checkout, admin, user
├── middlewares/            # adminAuth, asyncHandler, errorHandler
└── utils/logger.js
```
