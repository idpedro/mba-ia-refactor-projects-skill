# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
npm install
ADMIN_TOKEN=troque-este-token npm start
```

A aplicação sobe em `http://localhost:3000`. O banco SQLite é em memória e já carrega seeds automaticamente no boot.

Variáveis de ambiente (veja `.env.example`):

| Variável | Padrão | Uso |
|---|---|---|
| `PORT` | `3000` | Porta HTTP |
| `DB_PATH` | `:memory:` | Caminho do SQLite |
| `PAYMENT_GATEWAY_KEY` | vazio | Chave do gateway de pagamento |
| `ADMIN_TOKEN` | vazio | Token das rotas administrativas |
| `LOG_LEVEL` | `info` | `debug`, `info`, `warn`, `error` |

## Autenticação

- `POST /api/checkout` é público. Se o e-mail (`eml`) já existir, `pwd` precisa ser a senha da conta (senão `401`). Para um usuário novo, `pwd` é obrigatório.
- `GET /api/admin/financial-report` e `DELETE /api/users/:id` exigem `Authorization: Bearer <ADMIN_TOKEN>`. Sem token, com token errado, ou com `ADMIN_TOKEN` não definido, a resposta é `401`.

Usuário do seed: `leonan@fullcycle.com.br` / senha `123`.

Exemplos de requisições estão em `api.http`.

## Estrutura

```
src/
├── app.js            # composition root
├── config/           # variáveis de ambiente
├── database/         # conexão, schema e seed
├── models/           # acesso a dados por entidade
├── services/         # pagamento, senha, cache, relatório
├── controllers/      # casos de uso
├── validators/       # validação de entrada
├── routes/           # mapeamento HTTP → controller
└── middlewares/      # auth de admin, tratamento de erros
```
