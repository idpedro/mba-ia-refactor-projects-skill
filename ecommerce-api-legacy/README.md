# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
npm install
npm start
```

A aplicação sobe em `http://localhost:3000`. O banco SQLite é em memória e já carrega seeds automaticamente no boot.

Configuração via variáveis de ambiente (veja `.env.example`): `PORT`, `DB_PATH`, `PAYMENT_GATEWAY_KEY`, `ADMIN_TOKEN`, `LOG_LEVEL`. As rotas `/api/admin/financial-report` e `DELETE /api/users/:id` exigem `Authorization: Bearer <ADMIN_TOKEN>` (sem `ADMIN_TOKEN` definido respondem 403).

Exemplos de requisições estão em `api.http`.
