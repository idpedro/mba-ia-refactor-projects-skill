# code-smells-project

API de E-commerce em Python/Flask usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
pip install -r requirements.txt
python app.py
```

A aplicação sobe em `http://localhost:5000`. O banco SQLite (`loja.db`) é criado automaticamente no primeiro boot, já com produtos e usuários de exemplo. As variáveis de ambiente aceitas estão em `.env.example`.

## Autenticação

`POST /login` devolve um `token`; envie-o como `Authorization: Bearer <token>` nas rotas protegidas.

- Públicas: `GET /`, `GET /health`, `POST /login`, `POST /usuarios`, `GET /produtos`, `GET /produtos/busca`, `GET /produtos/<id>`.
- Autenticada: `POST /pedidos` (o `usuario_id` deve ser o do próprio token, salvo admin).
- Dono ou admin: `GET /usuarios/<id>`, `GET /pedidos/usuario/<id>`.
- Somente admin: `POST/PUT/DELETE /produtos`, `GET /usuarios`, `GET /pedidos`, `PUT /pedidos/<id>/status`, `GET /relatorios/vendas`, `POST /admin/reset-db`, `POST /admin/query` (apenas uma instrução `SELECT`, somente leitura).

Credenciais de desenvolvimento do seed:

| Email | Senha | Tipo |
|---|---|---|
| admin@loja.com | admin123 | admin |
| joao@email.com | 123456 | cliente |
| maria@email.com | senha123 | cliente |
