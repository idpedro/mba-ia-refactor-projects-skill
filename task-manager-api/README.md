# task-manager-api

API de Task Manager em Python/Flask usada como entrada do desafio `refactor-arch`, já refatorada para MVC: config externalizada, models com persistência, controllers com as regras, services para relatórios e notificações, views finas e tratamento de erros centralizado.

## Como rodar

```bash
pip install -r requirements.txt
python seed.py
python app.py
```

A aplicação sobe em `http://127.0.0.1:5000`. O `seed.py` recria o banco SQLite (`instance/tasks.db`) com usuários, categorias e tasks de exemplo; **rode-o antes do primeiro boot**. A configuração vem de variáveis de ambiente ou de um `.env` (veja `.env.example`).

## Autenticação

Todas as rotas exigem `Authorization: Bearer <token>`, exceto `GET /`, `GET /health`, `POST /login` e `POST /users` (cadastro). O token vem do campo `token` de `POST /login`:

```bash
curl -s -X POST localhost:5000/login -H 'Content-Type: application/json' \
  -d '{"email": "joao@email.com", "password": "1234"}'
```

Usuários do seed: `joao@email.com` / `1234` (admin), `maria@email.com` / `abcd` (user), `pedro@email.com` / `pass` (manager).

| Acesso | Rotas |
|---|---|
| Público | `GET /`, `GET /health`, `POST /login`, `POST /users` |
| Autenticado | `GET /tasks`, `GET /tasks/<id>`, `GET /tasks/search`, `GET /tasks/stats`, `POST /tasks`, `GET /categories` |
| Dono ou admin | `PUT`/`DELETE /tasks/<id>`, `GET`/`PUT /users/<id>`, `GET /users/<id>/tasks`, `GET /reports/user/<id>` |
| Admin | `GET /users`, `DELETE /users/<id>`, `GET /reports/summary`, `POST`/`PUT`/`DELETE /categories` |

Sem token ou com token inválido a resposta é `401`; sem permissão, `403`. Quem não é admin só cria ou reatribui tasks para si mesmo e não altera `role`/`active`. No cadastro público, `role` é ignorado e o usuário é criado como `user`.

## Estrutura

```
app.py                      # entrypoint: create_app() + app.run
seed.py
src/
├── app.py                  # composition root
├── config/settings.py
├── database.py
├── errors.py
├── models/                 # task_model, user_model, category_model
├── controllers/            # task, user, category + validators
├── services/               # report_service, notification_service
├── middlewares/            # auth (tokens e guards), error_handler
└── views/                  # blueprints: tasks, users, categories, reports, index
```
