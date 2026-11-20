# task-manager-api

API de Task Manager em Python/Flask usada como entrada do desafio `refactor-arch`, já refatorada para MVC (`src/`): config, models, controllers, services, views (blueprints) e middlewares (autenticação e tratamento de erros), montados em `src/app.py` (`create_app`).

## Como rodar

```bash
pip install -r requirements.txt
python seed.py
python app.py
```

A aplicação sobe em `http://127.0.0.1:5000`, sem precisar de nenhuma variável de ambiente (todas são opcionais; veja `.env.example`). O `seed.py` popula o banco SQLite (`instance/tasks.db`) com usuários, categorias e tasks de exemplo — **rode-o antes do primeiro boot**.

As senhas das contas semeadas vêm de `SEED_ADMIN_PASSWORD` / `SEED_USER_PASSWORD`; sem elas, o seed gera uma senha aleatória por conta e a exibe **uma única vez** no log. Ao subir sobre um banco criado pela versão antiga, o app troca as senhas padrão públicas daquela versão da mesma forma e converte os hashes MD5 para scrypt.

## Autenticação

`POST /login` devolve um `token` assinado; envie-o como `Authorization: Bearer <token>`.

| Acesso | Rotas |
|---|---|
| Público | `GET /`, `GET /health`, `POST /login`, `POST /users` (cadastro, sempre com role `user`) |
| Autenticado | `GET /tasks`, `GET /tasks/search`, `GET /tasks/stats`, `POST /tasks`, `GET /categories` — não-admins veem e criam só as próprias tasks |
| Dono ou admin | `GET/PUT/DELETE /tasks/<id>`, `GET/PUT /users/<id>`, `GET /users/<id>/tasks`, `GET /reports/user/<id>` |
| Admin | `GET /users`, `DELETE /users/<id>`, `GET /reports/summary`, `POST/PUT/DELETE /categories` |

Erros sempre em JSON: `{"error": "<mensagem>"}`.
