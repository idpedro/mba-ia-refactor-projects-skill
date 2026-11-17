================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python + Flask 3.0.0 (SQLite via Flask-SQLAlchemy 3.1.1)
Files:   15 analyzed | ~1158 lines of code

## Summary
CRITICAL: 7 | HIGH: 11 | MEDIUM: 23 | LOW: 5

## Findings

### [CRITICAL] Hardcoded credentials and secrets (AP-01)
File: app.py:13
Description: `app.config['SECRET_KEY'] = 'super-secret-key-123'` fixa a chave de assinatura no código-fonte.
Impact: Qualquer pessoa com acesso ao repositório conhece a chave; tokens ou sessões assinados com ela podem ser forjados.
Recommendation: P-01 — ler `SECRET_KEY` do ambiente em `config/settings.py`. Sem a variável, gerar uma chave aleatória por processo e avisar no log.

### [CRITICAL] Hardcoded credentials and secrets (AP-01)
File: services/notification_service.py:9-10
Description: `self.email_user = 'taskmanager@gmail.com'` e `self.email_password = 'senha123'` ficam no construtor de `NotificationService`.
Impact: A credencial SMTP vaza com o código.
Recommendation: P-01 — o serviço nunca é chamado (ver AP-09 e AP-21) e será removido, o que elimina a credencial.

### [CRITICAL] God class / God module (AP-03)
File: routes/task_routes.py:11-299
Description: O módulo de 299 linhas registra rotas, executa queries (`Task.query`, `User.query.get`, `Category.query.get`), aplica regras (overdue, validação, tags) e monta o JSON campo a campo (`get_tasks`, `create_task`, `update_task`, `task_stats`).
Impact: Não dá para testar regras sem subir o Flask e sem banco; qualquer mudança toca tudo.
Recommendation: P-03 — dividir em `controllers/task_controller.py`, `services/task_service.py`, `models/task_model.py` e `views/task_routes.py`.

### [CRITICAL] God class / God module (AP-03)
File: routes/user_routes.py:10-211
Description: Rotas, queries, validação (regex de email, role), hash de senha e login convivem em um único módulo. `login()` (:185) e `delete_user` (:134) fazem regras de negócio dentro da rota.
Impact: A mesma falta de camadas, e a lógica de autenticação não pode ser reutilizada nem testada isoladamente.
Recommendation: P-03 — `controllers/user_controller.py`, `services/user_service.py`, `views/user_routes.py`.

### [CRITICAL] God class / God module (AP-03)
File: routes/report_routes.py:12-223
Description: O módulo mistura dois domínios, relatórios (`summary_report`, `user_report`) e CRUD de categorias (`get_categories`, `create_category`, `update_category`, `delete_category`). Faz agregações, queries e formatação de resposta no mesmo lugar.
Impact: Categorias são difíceis de achar (estão em `report_routes`) e as agregações não são testáveis.
Recommendation: P-03 — separar em `views/report_routes.py` + `services/report_service.py` e `views/category_routes.py` + `services/category_service.py`.

### [CRITICAL] Plaintext or weak password storage (AP-05)
File: models/user.py:29, 32; seed.py:19, 25, 31
Description: `set_password` e `check_password` usam `hashlib.md5(pwd.encode())`, sem salt. O seed grava as senhas `1234`, `abcd` e `pass` por esse caminho.
Impact: MD5 sem salt é quebrado em segundos por rainbow table ou brute force; um vazamento do banco expõe todas as senhas.
Recommendation: P-04 — `werkzeug.security.generate_password_hash` / `check_password_hash` em `models/user_model.py`, com verificação de hashes MD5 legados e re-hash no login.

### [CRITICAL] Sensitive data exposure (AP-06)
File: models/user.py:21
Description: `User.to_dict()` inclui `'password': self.password`. O hash sai em `GET /users/<id>` (routes/user_routes.py:33), `POST /users` (:85), `PUT /users/<id>` (:129) e `POST /login` (:209).
Impact: Qualquer cliente recebe o hash MD5 de senha, que se quebra com facilidade.
Recommendation: P-05 — remover `password` do serializer em `models/user_model.py`.

### [HIGH] Business logic in the controller / route (AP-07)
File: routes/task_routes.py:11-63, 85-154, 156-223, 273-299
Description: `get_tasks` calcula `overdue` e resolve `user_name` e `category_name`; `create_task` e `update_task` validam status, prioridade, datas e tags; `task_stats` agrega contagens e a taxa de conclusão. Os handlers de 60 a 70 linhas passam muito do limite de ~40.
Impact: As regras ficam presas ao HTTP e não podem ser reutilizadas nem testadas.
Recommendation: P-06 — `services/task_service.py` (regras e agregações) chamado por `controllers/task_controller.py`.

### [HIGH] Business logic in the controller / route (AP-07)
File: routes/user_routes.py:42-90, 92-132, 134-151, 153-183
Description: Em `create_user` e `update_user` a rota valida o email, o tamanho da senha e o role. `delete_user` apaga as tasks do usuário (:140-142). `get_user_tasks` recalcula `overdue` (:171-180).
Impact: Mesmo problema: regras de usuário sem camada própria.
Recommendation: P-06 — `services/user_service.py` e `controllers/user_controller.py`.

### [HIGH] Business logic in the controller / route (AP-07)
File: routes/report_routes.py:12-101, 103-155
Description: `summary_report` e `user_report` fazem a agregação completa, com contagens por status e prioridade, lista de overdue, atividade dos últimos 7 dias e produtividade por usuário, dentro do handler.
Impact: A lógica de relatório não é testável e é duplicada em `task_stats`.
Recommendation: P-06 — `services/report_service.py`.

### [HIGH] Tight coupling / no dependency injection (AP-08)
File: app.py:9-31; routes/task_routes.py:2; routes/user_routes.py:2; routes/report_routes.py:2
Description: `app` é criado no escopo do módulo, sem `create_app()`. Todas as rotas importam o singleton `db` e os models concretos, e `db.create_all()` roda na importação (:30-31).
Impact: Não dá para criar apps isolados (testes, configuração por ambiente). Importar `app` já abre o banco.
Recommendation: P-07 — app factory `create_app()` em `app.py`, com composição de blueprints e `db` por injeção.

### [HIGH] Tight coupling / no dependency injection (AP-08)
File: services/notification_service.py:4-48
Description: `NotificationService` é definido, mas nenhum módulo o importa ou instancia (grep de `NotificationService` e `notification_service` fora do próprio arquivo: 0 resultados).
Impact: É um serviço órfão, nunca ligado à aplicação.
Recommendation: P-07 / P-08 — remover o serviço (nada o consome).

### [HIGH] Mutable global state (AP-09)
File: services/notification_service.py:6
Description: `self.notifications = []` acumula um dict por notificação (`notify_task_assigned`, :31) em coleção que viveria durante todo o processo. Só `get_notifications` (:43) a lê, e ninguém o chama.
Impact: Estado em memória que cresce sem limite e se perde no restart, se algum dia for ligado.
Recommendation: P-08 — apagar a coleção junto com o serviço. Nada lê esse dado, então não há o que persistir. O grep de AP-09 deve ficar sem hits.

### [HIGH] Non-atomic multi-step writes and orphaned data (AP-10)
File: routes/report_routes.py:211-223
Description: `delete_category` faz `db.session.delete(cat)` sem tocar nas tasks que usam o `category_id`. O SQLite não impõe FK, então as tasks ficam apontando para uma categoria inexistente.
Impact: Dados órfãos; `GET /tasks` passa a devolver `category_name: None` com `category_id` preenchido.
Recommendation: P-11 — na mesma transação, zerar `Task.category_id` das tasks afetadas, em `services/category_service.py`.

### [HIGH] Missing authentication / authorization (AP-11)
File: routes/user_routes.py:10-25, 42-90, 92-132, 134-151, 185-211
Description: Nenhuma rota de usuário exige autenticação. `create_user` aceita `role` do corpo (:52, :71-78), então qualquer um se cadastra como `admin`. `update_user` muda `role` e `active` de qualquer usuário (:119-125), `delete_user` apaga qualquer conta e `GET /users` lista nome e email de todos. O login devolve o token falso `'fake-jwt-token-' + str(user.id)` (:210).
Impact: Qualquer cliente anônimo escala para admin, altera ou exclui contas e lista dados pessoais.
Recommendation: P-16 — `middlewares/auth.py` com token assinado, `@require_auth`, e verificações de owner-or-admin e admin em `controllers/user_controller.py`.

### [HIGH] Missing authentication / authorization (AP-11)
File: routes/task_routes.py:11-299
Description: Todas as 7 rotas de task são anônimas. `PUT /tasks/<id>` (:156) e `DELETE /tasks/<id>` (:225) alteram ou apagam tasks de qualquer usuário, e `create_task` aceita qualquer `user_id` (:105).
Impact: Qualquer cliente anônimo lê, altera, reatribui e apaga dados de todos os usuários.
Recommendation: P-16 — autenticação obrigatória e escrita só para dono ou admin.

### [HIGH] Missing authentication / authorization (AP-11)
File: routes/report_routes.py:12-155, 167-223
Description: `/reports/summary` (:12) e `/reports/user/<id>` (:103, devolve o email, :141) são anônimas, assim como a escrita em categorias (:167, :190, :211).
Impact: Vazamento de métricas e emails por usuário, e qualquer um apaga ou renomeia categorias.
Recommendation: P-16 — autenticação em tudo; relatório geral e escrita de categorias só para admin; relatório de usuário para dono ou admin.

### [HIGH] Debug mode and unsafe defaults in the entry point (AP-12)
File: app.py:34, 15
Description: `app.run(debug=True, host='0.0.0.0', port=5000)` expõe o debugger Werkzeug em todas as interfaces. `CORS(app)` (:15) libera todas as origens.
Impact: Execução remota de código pelo console do debugger e acesso cross-origin irrestrito.
Recommendation: P-01 — `DEBUG` desligado, `HOST=127.0.0.1` por padrão e lista de origens CORS explícita (`CORS_ORIGINS`) em `config/settings.py`.

### [MEDIUM] N+1 queries (AP-13)
File: routes/task_routes.py:41-57, 275-281
Description: `get_tasks` chama `User.query.get(t.user_id)` e `Category.query.get(t.category_id)` dentro do loop (1 + 2N queries). `task_stats` roda 5 `COUNT` separados e ainda carrega todas as tasks (:281).
Impact: O custo cresce linearmente com o número de tasks.
Recommendation: P-09 — `joinedload` / `GROUP BY` em `models/task_model.py`.

### [MEDIUM] N+1 queries (AP-13)
File: routes/user_routes.py:22
Description: `len(u.tasks)` dentro do loop de `get_users` dispara um lazy load por usuário.
Impact: N+1 em `GET /users`.
Recommendation: P-09 — contagem por `GROUP BY user_id` em uma query só.

### [MEDIUM] N+1 queries (AP-13)
File: routes/report_routes.py:19-28, 55-61, 163
Description: `summary_report` roda 9 `COUNT` separados por status e prioridade, e uma query de tasks por usuário (:56). `get_categories` faz `Task.query.filter_by(category_id=c.id).count()` por categoria.
Impact: Dezenas de queries por request.
Recommendation: P-09 — agregações com `GROUP BY` em `services/report_service.py`.

### [MEDIUM] Duplicated logic (AP-14)
File: routes/task_routes.py:17-28, 30-39, 71-80, 110, 177, 284-287; models/task.py:50-60
Description: A regra de overdue está escrita em 4 lugares nas rotas, e `Task.is_overdue()` existe mas é ignorada. `get_tasks` monta o dict campo a campo em vez de usar `to_dict()`. A lista de status aparece como literal em :110 e :177.
Impact: Corrigir a regra exige mexer em vários pontos.
Recommendation: P-12 — uma única `is_overdue()` e uma constante de status em `models/task_model.py`.

### [MEDIUM] Duplicated logic (AP-14)
File: routes/user_routes.py:15-23, 61, 106, 162-181
Description: A regex de email se repete em :61 e :106 (e em `helpers.py:21`). `get_user_tasks` copia a regra de overdue e monta o dict manualmente, e o role é validado com literais em :71 e :120.
Impact: Mesmas regras duplicadas, com risco de divergência.
Recommendation: P-12 — validadores únicos em `controllers/validators.py`.

### [MEDIUM] Duplicated logic (AP-14)
File: routes/report_routes.py:34-43, 132-135
Description: A regra de overdue é reescrita em `summary_report` e `user_report`.
Impact: Quinta e sexta cópias da regra.
Recommendation: P-12 — reutilizar a regra do model.

### [MEDIUM] Duplicated logic (AP-14)
File: models/task.py:38-48
Description: `validate_status` e `validate_priority` duplicam as listas e os limites das rotas e nunca são chamados.
Impact: Código morto que parece ser a fonte da regra, mas não é.
Recommendation: P-12 — tornar a validação única e usada.

### [MEDIUM] Duplicated logic (AP-14)
File: utils/helpers.py:19-23, 57-116
Description: `validate_email`, `process_task_data`, `VALID_STATUSES`, `VALID_ROLES`, `MIN_TITLE_LENGTH` etc. repetem as validações das rotas, mas nenhuma rota os importa.
Impact: Existem helpers de validação ignorados, enquanto cada rota valida por conta própria.
Recommendation: P-12 — consolidar em `controllers/validators.py`.

### [MEDIUM] Missing or inconsistent input validation (AP-15)
File: routes/task_routes.py:87, 113, 167, 182, 261, 264
Description: `priority < 1` (:113, :182) e `len(data['title'])` (:167) levantam `TypeError` com tipos errados, e `int(priority)` / `int(user_id)` em `search_tasks` levantam `ValueError`. As exceções saem como 500. `request.get_json()` (:87, :162) falha com 415/400 fora do JSON.
Impact: Entrada malformada derruba a rota com 500 em vez de 400.
Recommendation: P-12 — validadores de tipo em `controllers/validators.py`, com resposta 400.

### [MEDIUM] Missing or inconsistent input validation (AP-15)
File: routes/user_routes.py:102-103, 106, 115, 125
Description: `update_user` não valida `name`; `re.match` e `len` recebem valores não string; `active` é atribuído sem checar o tipo. O create exige `name`, `email` e `password`, e o update não aplica as mesmas regras.
Impact: 500 e dados inconsistentes.
Recommendation: P-12.

### [MEDIUM] Missing or inconsistent input validation (AP-15)
File: routes/report_routes.py:173-180, 196-202
Description: `update_category` faz `'name' in data` sem checar `data is None` (500). `create_category` e `update_category` não validam o formato de `color` nem o tamanho de `name` e `description` (colunas `String(7)`, `String(100)`), embora o helper `is_valid_color` exista.
Impact: 500 ou truncamento silencioso.
Recommendation: P-12.

### [MEDIUM] Scattered or leaky error handling (AP-16)
File: routes/task_routes.py:62, 137, 204, 236
Description: `except:` sem tipo em `get_tasks`, `create_task`, `update_task` e `delete_task` engole qualquer erro. `except Exception` repete rollback e `print` em cada handler.
Impact: Falhas reais ficam invisíveis.
Recommendation: P-10 — `middlewares/error_handler.py` e `errors.py` com exceções de domínio.

### [MEDIUM] Scattered or leaky error handling (AP-16)
File: routes/user_routes.py:87-90, 130, 149
Description: `except:` e `except Exception` com `print` e rollback repetidos; o texto da exceção só vai ao stdout (:89).
Impact: Tratamento duplicado, sem log estruturado.
Recommendation: P-10.

### [MEDIUM] Scattered or leaky error handling (AP-16)
File: routes/report_routes.py:186, 207, 221
Description: `except:` bare em create, update e delete de categoria.
Impact: Erros mascarados, sempre devolvidos como 500 genérico.
Recommendation: P-10.

### [MEDIUM] Scattered or leaky error handling (AP-16)
File: app.py:9-31
Description: Não há `@app.errorhandler`. Rotas inexistentes devolvem HTML 404, e exceções não previstas devolvem o HTML 500 do Flask, numa API JSON.
Impact: Contrato de erro inconsistente.
Recommendation: P-10 — handler central com JSON `{'error': ...}`.

### [MEDIUM] Scattered or leaky error handling (AP-16)
File: utils/helpers.py:46, 48, 88
Description: `except:` bare em `parse_date` e `process_task_data`.
Impact: Mesmo anti-padrão (em código sem uso hoje).
Recommendation: P-10 — capturar `ValueError` ao reaproveitar `parse_date`.

### [MEDIUM] Deprecated APIs (AP-17)
File: routes/task_routes.py:31, 42, 51, 67, 72, 117, 122, 158, 188, 195, 215, 227, 285
Description: `datetime.utcnow()` (obsoleto no Python 3.12) e `Model.query.get(id)` (legado desde o SQLAlchemy 2.0).
Impact: Warnings hoje; quebra em versões futuras.
Recommendation: P-13 — `datetime.now(timezone.utc)` e `db.session.get(Model, id)`.

### [MEDIUM] Deprecated APIs (AP-17)
File: routes/user_routes.py:29, 94, 136, 155, 172
Description: Mesmo uso de `query.get` e `utcnow`.
Impact: Idem.
Recommendation: P-13 — `db.session.get(User, id)`.

### [MEDIUM] Deprecated APIs (AP-17)
File: routes/report_routes.py:35, 42, 45, 71, 105, 133, 192, 213
Description: `utcnow()` e `Model.query.get`.
Impact: Idem.
Recommendation: P-13.

### [MEDIUM] Deprecated APIs (AP-17)
File: models/task.py:15, 16, 52; models/user.py:14; models/category.py:11
Description: `default=datetime.utcnow` nas colunas e em `is_overdue`.
Impact: Idem.
Recommendation: P-13 — `default=lambda: datetime.now(timezone.utc)`, preservando datetimes naive no banco.

### [MEDIUM] Deprecated APIs (AP-17)
File: services/notification_service.py:35; utils/helpers.py:38
Description: `datetime.utcnow()` em código morto.
Impact: Idem.
Recommendation: P-13 — removido junto com o código morto (AP-21).

### [MEDIUM] Configuration in code instead of a config module (AP-18)
File: app.py:11, 34
Description: `'sqlite:///tasks.db'`, a porta `5000` e o host são literais no entry point.
Impact: Não dá para configurar por ambiente.
Recommendation: P-01 — `config/settings.py` lendo `DATABASE_URL`, `PORT`, `HOST` do ambiente, com `.env.example`.

### [MEDIUM] Configuration in code instead of a config module (AP-18)
File: services/notification_service.py:7-8
Description: `smtp.gmail.com` e `587` como literais.
Impact: Idem.
Recommendation: P-01 — removido junto com o serviço.

### [LOW] Magic numbers and strings (AP-19)
File: routes/task_routes.py:96, 99, 110, 113, 177, 181-182; routes/user_routes.py:64, 71, 115, 120; routes/report_routes.py:45, 180; models/task.py:39, 46
Description: Limites `3`, `200`, `1`..`5`, `4`; `'done'`, `'cancelled'` inline; janela de `7` dias; `'#000000'`. As constantes de `utils/helpers.py:110-116` existem e não são usadas.
Impact: Regras sem nome, repetidas.
Recommendation: P-14 — constantes em `config/settings.py` e `models/`.

### [LOW] Poor naming (AP-20)
File: routes/task_routes.py:16, 41; routes/user_routes.py:14, 37, 161; routes/report_routes.py:33, 55, 161; models/category.py:14; report_routes.py:24-28
Description: `t`, `u`, `c`, `d`, `e`, `p1`..`p5`, `cat`, `pwd`.
Impact: Leitura mais lenta.
Recommendation: P-14 — renomear identificadores internos; os campos de request/response ficam como estão.

### [LOW] Unused imports and dead code (AP-21)
File: app.py:7; routes/task_routes.py:7; routes/user_routes.py:6; routes/report_routes.py:7-8; models/task.py:3; utils/helpers.py:3-7, 9-108; models/user.py:34-38; services/notification_service.py:1-48; requirements.txt
Description: Imports sem uso: `os, sys, json` (app.py), `json, os, sys, time` (task_routes), `hashlib, json` (user_routes), `format_date, calculate_percentage, json` (report_routes), `json` (task.py), `os, json, sys, math, hashlib` (helpers.py). Funções nunca chamadas: quase todo `utils/helpers.py`, `User.is_admin`, `NotificationService`. As dependências `marshmallow` e `requests` também não são importadas.
Impact: Ruído e superfície de manutenção.
Recommendation: remover. O `is_admin` será reaproveitado pela autorização (P-16).

### [LOW] Print-debugging instead of logging (AP-22)
File: routes/task_routes.py:149, 153, 219, 234; routes/user_routes.py:83, 89, 147; services/notification_service.py:21, 24; utils/helpers.py:39, 41
Description: `print(...)` é o único mecanismo de log.
Impact: Sem nível, formato ou destino configurável.
Recommendation: P-15 — módulo `logging` configurado em `config/settings.py` / `app.py`.

### [LOW] Verbose control flow (AP-23)
File: models/task.py:40-43, 46-48, 50-60; models/user.py:35-38; routes/task_routes.py:30-39, 141, 210, 283-287; routes/user_routes.py:171-180; routes/report_routes.py:59-61, 119-135; utils/helpers.py:103
Description: `if ...: return True else: return False`, pirâmide de `if` aninhados para `overdue`, `type(x) == list` em vez de `isinstance`, `x = x + 1` em loops de contagem.
Impact: Mais linhas e mais chances de erro para uma regra simples.
Recommendation: P-14 — expressões booleanas diretas, `isinstance`, `sum()`.

================================
Total: 46 findings
================================

## Decisions requiring approval
1. Autenticação — `POST /login` passa a devolver um token assinado (itsdangerous, já incluído no Flask) no mesmo campo `token`, no lugar de `fake-jwt-token-<id>`. Todas as rotas exigem `Authorization: Bearer <token>`, exceto `GET /`, `GET /health`, `POST /login` e `POST /users` (cadastro) — default: aplicado sempre, sem variável de ambiente; sem credenciais responde `401`.
2. Autorização — `GET /users` e `GET /reports/summary` só para admin; `GET /users/<id>`, `GET /users/<id>/tasks`, `GET /reports/user/<id>` e `PUT /users/<id>` para o próprio usuário ou admin; `DELETE /users/<id>` e escrita em `/categories` só admin; `PUT`/`DELETE /tasks/<id>` só para o dono da task ou admin; demais leituras para qualquer autenticado — default: não-autorizado recebe `403`.
3. Auto-atribuição de role — `POST /users` sem token só cria `role: user`; pedir `admin` ou `manager` sem token de admin responde `403`, e `PUT /users/<id>` só altera `role` e `active` com token de admin — default: 403.
4. Campo `password` removido de todas as respostas de usuário (`/users`, `/users/<id>`, `/login`) — default: removido.
5. Formato do hash de senha: MD5 → hash salgado do Werkzeug. O login ainda aceita hashes MD5 antigos e os regrava no novo formato; `seed.py` já grava o novo — default: sim.
6. `SECRET_KEY` vem do ambiente; sem a variável, uma chave aleatória é gerada a cada boot (tokens deixam de valer após reiniciar) e um aviso vai para o log — default: sim.
7. Entry point seguro: `debug` desligado, bind em `127.0.0.1` (`HOST=0.0.0.0` só por opt-in) e CORS com lista explícita via `CORS_ORIGINS` (default `http://localhost:3000`) — default: sim.
8. `DELETE /categories/<id>` zera `category_id` das tasks afetadas na mesma transação — default: sim.
9. Entradas inválidas que hoje geram 500 (tipos errados, `int()` em `/tasks/search`, corpo não JSON) passam a responder `400`; rotas inexistentes e erros inesperados respondem JSON `{"error": ...}` — default: sim.
10. `NotificationService` (nunca usado, com credenciais e estado em memória) é removido; as dependências sem uso (`marshmallow`, `requests`) saem do `requirements.txt` — default: sim.
11. Nomes de campos de request e response ficam como estão; `DELETE /users/<id>` continua apagando as tasks do usuário, agora de forma atômica — default: mantido.

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
