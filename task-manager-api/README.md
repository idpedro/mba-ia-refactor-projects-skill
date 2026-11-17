# task-manager-api

API de Task Manager em Python/Flask usada como entrada do desafio `refactor-arch`, organizada em camadas (`config`, `models`, `controllers`, `services`, `views`, `middlewares`).

## Como rodar

```bash
pip install -r requirements.txt
python seed.py
python app.py
```

A aplicação sobe em `http://127.0.0.1:5000`. O `seed.py` popula o banco SQLite (`instance/tasks.db`) com usuários, categorias e tasks de exemplo. Rode-o antes do primeiro boot.

Variáveis de ambiente: veja `.env.example`. Para expor a API fora da máquina local, defina `HOST=0.0.0.0` e `CORS_ORIGINS` explicitamente.

## Autenticação

`POST /login` devolve um `token` assinado. Envie-o em `Authorization: Bearer <token>`. Rotas públicas: `GET /`, `GET /health`, `POST /login` e `POST /users` (cadastro, sempre com `role: user` sem token de admin). As demais exigem token (`401` sem ele, `403` sem permissão).

| Rota | Acesso |
|---|---|
| `GET /users`, `DELETE /users/<id>`, `GET /reports/summary`, `POST/PUT/DELETE /categories` | admin |
| `GET/PUT /users/<id>`, `GET /users/<id>/tasks`, `GET /reports/user/<id>` | próprio usuário ou admin (`role` e `active` só admin altera) |
| `PUT/DELETE /tasks/<id>` | dono da task ou admin |
| demais leituras e `POST /tasks` | qualquer usuário autenticado |

Usuários do seed: `joao@email.com` / `1234` (admin), `maria@email.com` / `abcd` (user), `pedro@email.com` / `pass` (manager).
