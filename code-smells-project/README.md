# code-smells-project

API de E-commerce em Python/Flask, refatorada para MVC com a skill `refactor-arch`.

## Como rodar

```bash
pip install -r requirements.txt
python app.py
```

A aplicação sobe em `http://127.0.0.1:5000`. O banco SQLite (`loja.db`) é criado no primeiro boot, com produtos e usuários de exemplo. As variáveis de ambiente (todas opcionais) estão em `.env.example`.

## Autenticação

`POST /login` devolve um `token`; envie-o em `Authorization: Bearer <token>`.

| Acesso | Rotas |
|---|---|
| Público | `/`, `/health`, `POST /login`, `POST /usuarios`, `GET /produtos`, `GET /produtos/busca`, `GET /produtos/<id>` |
| Login | `POST /pedidos` (só para o próprio usuário) |
| Dono ou admin | `GET /usuarios/<id>`, `GET /pedidos/usuario/<id>` |
| Admin | `GET /usuarios`, `POST/PUT/DELETE /produtos`, `GET /pedidos`, `PUT /pedidos/<id>/status`, `GET /relatorios/vendas`, `POST /admin/reset-db`, `POST /admin/query` (somente `SELECT`) |

Sem credencial a resposta é `401`; com papel insuficiente, `403`.

Usuários de demonstração (senhas gravadas como hash): `admin@loja.com` / `admin123` (admin), `joao@email.com` / `123456`, `maria@email.com` / `senha123`.

## Estrutura

```
app.py                     # entry point
src/app.py                 # create_app(): composition root
src/config/settings.py     # variáveis de ambiente
src/database.py            # conexão por requisição, schema, seed
src/models/                # acesso a dados (SQL parametrizado)
src/services/              # auth, notificações, relatório
src/controllers/           # casos de uso e validação
src/views/                 # blueprints
src/middlewares/           # auth e tratamento de erros
```
