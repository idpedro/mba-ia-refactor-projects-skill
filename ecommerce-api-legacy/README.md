# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
npm install
npm start
```

A aplicação sobe em `http://127.0.0.1:3000`. Nenhuma variável de ambiente é obrigatória; as opcionais estão em `.env.example` (`PORT`, `HOST`, `DB_PATH`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `SEED_USER_PASSWORD`).

O banco SQLite é em memória por padrão e carrega os seeds no boot. Quando `ADMIN_PASSWORD` ou `SEED_USER_PASSWORD` não estão definidas, a senha da conta correspondente é gerada e impressa uma única vez no log de inicialização.

## Autenticação

- `POST /api/checkout` é público para e-mails novos. Para um e-mail já cadastrado, envie a senha correta em `pwd` (ou autentique-se como o próprio usuário ou como admin).
- `GET /api/admin/financial-report` e `DELETE /api/users/:id` exigem a conta admin via HTTP Basic (`Authorization: Basic base64(email:senha)`): sem credenciais → `401`, usuário comum → `403`.

## Estrutura

```
src/
├── app.js            # composition root (createApp) e inicialização
├── config/           # variáveis de ambiente
├── constants/        # papéis de usuário
├── database/         # conexão promisificada, schema/migrações, seed
├── models/           # acesso a dados por entidade
├── services/         # pagamento, relatório, senhas
├── controllers/      # casos de uso
├── validators/       # validação do checkout
├── middlewares/      # auth, asyncHandler, errorHandler
├── routes/           # rotas Express
└── utils/logger.js
```

Exemplos de requisições estão em `api.http`.
