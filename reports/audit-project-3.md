================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python + Flask 3.0.0 (SQLite via Flask-SQLAlchemy 3.1.1)
Files:   12 analyzed | ~1155 lines of code

## Summary
CRITICAL: 5 | HIGH: 10 | MEDIUM: 24 | LOW: 29

## Findings

### [CRITICAL] Hardcoded credentials and secrets (AP-01)
File: app.py:13
Description: `app.config['SECRET_KEY'] = 'super-secret-key-123'` fixa a chave de assinatura do Flask como literal no código-fonte versionado.
Impact: Qualquer pessoa com acesso ao repositório pode forjar sessões/tokens assinados com essa chave; a chave é a mesma em todos os ambientes.
Recommendation: P-01 — mover para `src/config/settings.py` lendo `SECRET_KEY` do ambiente (fallback `secrets.token_hex(32)`), com `.env.example` sem valor real.

### [CRITICAL] Hardcoded credentials and secrets (AP-01)
File: services/notification_service.py:9-10
Description: `NotificationService.__init__` define `self.email_user = 'taskmanager@gmail.com'` e `self.email_password = 'senha123'` como literais usados em `server.login(...)` (linha 17). O host/porta SMTP das linhas 7-8 são reportados à parte (AP-18).
Impact: A senha da conta de e-mail fica exposta a quem lê o código; trocar a credencial exige novo deploy.
Recommendation: P-01 — `SMTP_USER`/`SMTP_PASSWORD` em `src/config/settings.py` lidos do ambiente e injetados em `src/services/notification_service.py`.

### [CRITICAL] God class / God module (AP-03)
File: routes/report_routes.py:12-223
Description: O módulo `report_routes.py` mistura dois domínios (relatórios `/reports/*` e o CRUD completo de `/categories`) e, no mesmo arquivo, registra rotas, executa consultas (`Task.query...count()` x12), aplica regras de negócio (regra de atraso, taxa de conclusão, produtividade por usuário) e formata as respostas. Também se enquadra em AP-07 (handler `summary_report` com 90 linhas, 12-101).
Impact: Não é possível testar a agregação de relatórios nem o CRUD de categorias sem subir o Flask e o banco; qualquer mudança em categorias mexe no módulo de relatórios.
Recommendation: P-03 + P-06 — separar em `src/views/report_routes.py` + `src/services/report_service.py` e `src/views/category_routes.py` + `src/controllers/category_controller.py` + `src/models/category_model.py`.

### [CRITICAL] Plaintext or weak password storage (AP-05)
File: models/user.py:29, 32
Description: `set_password` grava `hashlib.md5(pwd.encode()).hexdigest()` e `check_password` compara com o mesmo MD5 sem salt. O `seed.py` (linhas 19, 26, 33) cria usuários com senhas triviais (`'1234'`, `'abcd'`, `'pass'`) por esse mesmo caminho.
Impact: MD5 sem salt é revertido por rainbow tables em segundos; senhas iguais geram hashes iguais. Um vazamento do banco (ou da API, ver AP-06) expõe as senhas.
Recommendation: P-04 — `werkzeug.security.generate_password_hash` / `check_password_hash` em `src/models/user_model.py`, com fallback para hashes MD5 legados (ver decisão 2).

### [CRITICAL] Sensitive data exposure (AP-06)
File: models/user.py:21, routes/user_routes.py:33, 85, 129, 209
Description: `User.to_dict()` inclui `'password': self.password` (o hash MD5), e esse dicionário é devolvido por `get_user` (GET /users/<id>), `create_user` (POST /users), `update_user` (PUT /users/<id>) e `login` (POST /login, chave `user`).
Impact: Qualquer cliente obtém o hash MD5 da senha de qualquer usuário via GET /users/<id>, que combinado com AP-05 equivale a vazar a senha.
Recommendation: P-05 — remover `password` de `to_dict()` em `src/models/user_model.py` (ver decisão 1).

### [HIGH] Business logic in the controller / route (fat controller) (AP-07)
File: routes/task_routes.py:11-63, 85-154, 156-223, 273-299
Description: `get_tasks` (53 linhas) monta o dicionário campo a campo, calcula a regra de atraso e resolve `user_name`/`category_name`; `create_task` (70 linhas) e `update_task` (68 linhas) fazem toda a validação de título/status/prioridade, checam existência de usuário/categoria, fazem parse de data e de tags; `task_stats` agrega contagens e taxa de conclusão.
Impact: As regras de tarefa só podem ser testadas via HTTP; qualquer novo ponto de entrada (CLI, job) teria que duplicá-las.
Recommendation: P-06 — `src/controllers/task_controller.py` com validação em `src/controllers/validators.py`; rotas finas em `src/views/task_routes.py`.

### [HIGH] Business logic in the controller / route (fat controller) (AP-07)
File: routes/user_routes.py:42-90, 92-132, 134-151, 185-211
Description: `create_user` (49 linhas) valida nome/e-mail/senha/role e unicidade de e-mail; `update_user` repete as regras; `delete_user` decide a exclusão em cascata das tasks; `login` decide autenticação, estado `active` e gera o token.
Impact: Regras de cadastro e autenticação acopladas ao Flask, sem teste unitário possível e duplicadas entre create/update.
Recommendation: P-06 — `src/controllers/user_controller.py` (e `auth` no mesmo controller), rotas finas em `src/views/user_routes.py`.

### [HIGH] Tight coupling / no dependency injection (AP-08)
File: app.py:9-31
Description: `app = Flask(__name__)` é criado no nível de módulo, sem `create_app()`; a configuração é aplicada por literais e `db.create_all()` roda como efeito colateral do import (linhas 30-31). `seed.py:2` depende de `from app import app, db`, e todas as rotas usam o singleton global `Model.query`.
Impact: Impossível criar uma instância da app com outra configuração (ex.: banco de teste); importar `app` já cria o schema no `tasks.db` real.
Recommendation: P-07 — app factory `create_app(settings)` em `src/app.py` como composition root; `app.py` raiz vira entrypoint fino; `seed.py` passa a usar a factory.

### [HIGH] Tight coupling / no dependency injection (AP-08)
File: services/notification_service.py:4-48
Description: `NotificationService` é definido mas nunca importado nem instanciado em lugar algum (código morto, também AP-21), e `send_email` abre `smtplib.SMTP(self.email_host, self.email_port)` diretamente (linha 15), sem injeção do transporte nem da configuração.
Impact: A notificação de atribuição de task nunca acontece; o serviço não pode ser testado sem um servidor SMTP real.
Recommendation: P-07 — configurar via `Settings`, instanciar uma vez em `src/app.py` e injetar no `TaskController`; modo "somente log" quando SMTP não está configurado.

### [HIGH] Mutable global state (AP-09)
File: services/notification_service.py:6, 31, 45
Description: `self.notifications = []` é usado como armazenamento: `notify_task_assigned` faz `append` e `get_notifications` filtra a lista em memória.
Impact: Os dados somem a cada restart e divergem entre processos/workers; a lista cresce sem limite.
Recommendation: P-08 — manter a lista apenas na instância única injetada pelo composition root em `src/services/notification_service.py` (persistência fora de escopo), sem estado de módulo.

### [HIGH] Non-atomic multi-step writes and orphaned data (AP-10)
File: routes/report_routes.py:211-223
Description: `delete_category` executa `db.session.delete(cat)` sem tratar as tasks cujo `category_id` aponta para a categoria; o SQLite não aplica FKs por padrão, então essas tasks ficam com `category_id` órfão.
Impact: Após a exclusão, GET /tasks devolve `category_id` de uma categoria inexistente (`category_name: null`), e filtros/relatórios por categoria ficam inconsistentes.
Recommendation: P-11 — no `CategoryController.delete` (`src/controllers/category_controller.py`), anular `category_id` das tasks e excluir a categoria na mesma transação (ver decisão 7).

### [HIGH] Missing authentication / authorization (AP-11)
File: routes/user_routes.py:52, 71, 92-132, 134-151, 210
Description: `create_user` aceita `role = data.get('role', 'user')` do corpo (qualquer um se cadastra como `admin`); `update_user` e `delete_user` não verificam quem chama (qualquer cliente altera senha/role ou exclui outro usuário); `login` devolve `'fake-jwt-token-' + str(user.id)`, um token adivinhável e sem assinatura.
Impact: Escalada de privilégio trivial e tomada de contas: basta conhecer o id do usuário.
Recommendation: P-05 — ignorar `role` no cadastro público; trocar o token falso por um token assinado (`itsdangerous`, já dependência do Flask) e adicionar guarda `require_auth` em `src/middlewares/auth.py` (ver decisões 3 e 4).

### [HIGH] Missing authentication / authorization (AP-11)
File: routes/task_routes.py:85, 156, 225
Description: `create_task`, `update_task` e `delete_task` (POST/PUT/DELETE /tasks) não têm nenhuma verificação de autenticação.
Impact: Qualquer cliente anônimo cria, altera ou apaga tarefas de qualquer usuário.
Recommendation: P-05 — aplicar a guarda `require_auth` de `src/middlewares/auth.py` nas rotas de escrita de `src/views/task_routes.py` (ver decisão 4).

### [HIGH] Missing authentication / authorization (AP-11)
File: routes/report_routes.py:167, 190, 211
Description: `create_category`, `update_category` e `delete_category` (POST/PUT/DELETE /categories) não têm verificação de autenticação.
Impact: Qualquer cliente anônimo altera ou apaga categorias (e, via AP-10, deixa tasks órfãs).
Recommendation: P-05 — guarda `require_auth` nas rotas de escrita de `src/views/category_routes.py` (ver decisão 4).

### [HIGH] Debug mode and unsafe defaults in the entry point (AP-12)
File: app.py:15, 34
Description: `app.run(debug=True, host='0.0.0.0', port=5000)` expõe o debugger do Werkzeug em todas as interfaces; `CORS(app)` libera qualquer origem sem lista configurável.
Impact: O debugger interativo do Werkzeug permite execução remota de código por qualquer máquina que alcance a porta.
Recommendation: P-01 — `DEBUG`, `HOST`, `PORT` e `CORS_ORIGINS` em `src/config/settings.py` (debug desligado e host `127.0.0.1` por padrão, ver decisão 5).

### [MEDIUM] N+1 queries (AP-13)
File: routes/task_routes.py:42, 51, 275-279
Description: `get_tasks` chama `User.query.get(t.user_id)` e `Category.query.get(t.category_id)` dentro do loop de tasks (2N+1 consultas); `task_stats` faz 5 `count()` separados e ainda carrega todas as tasks (linha 281).
Impact: O tempo de resposta cresce linearmente com o número de tasks.
Recommendation: P-09 — `joinedload(Task.user)`, `joinedload(Task.category)` e um `GROUP BY status` em `src/models/task_model.py`.

### [MEDIUM] N+1 queries (AP-13)
File: routes/report_routes.py:15-28, 56, 163
Description: `summary_report` dispara 12 `count()` (status e prioridade) em vez de dois `GROUP BY`, faz `Task.query.filter_by(user_id=u.id).all()` por usuário; `get_categories` faz `Task.query.filter_by(category_id=c.id).count()` por categoria.
Impact: Relatório e listagem de categorias fazem dezenas de consultas por requisição.
Recommendation: P-09 — contagens agrupadas em `src/models/task_model.py`, usadas por `src/services/report_service.py` e `src/controllers/category_controller.py`.

### [MEDIUM] N+1 queries (AP-13)
File: routes/user_routes.py:22
Description: `get_users` usa `len(u.tasks)`, que dispara o lazy-load do relacionamento `tasks` para cada usuário.
Impact: Uma consulta extra por usuário listado.
Recommendation: P-09 — contagem por `GROUP BY user_id` em `src/models/task_model.py`, consumida por `src/controllers/user_controller.py`.

### [MEDIUM] Duplicated logic (AP-14)
File: routes/task_routes.py:17-28, 30-39, 71-80, 96-100, 110, 113, 167-170, 177, 182, 283-287
Description: `get_tasks` reconstrói à mão o mesmo dicionário de `Task.to_dict()` (models/task.py:23-36); a regra de atraso é escrita três vezes, embora `Task.is_overdue()` exista (models/task.py:50); a lista de status e os limites de título/prioridade são copiados entre `create_task` e `update_task`, ignorando `Task.validate_status`, `utils/helpers.process_task_data` e `VALID_STATUSES`.
Impact: Mudar uma regra (ex.: novo status) exige editar vários pontos; as cópias já divergem (helpers aceita `dd/mm/YYYY`, as rotas não).
Recommendation: P-12 — um único `validate_task_payload` em `src/controllers/validators.py` e `to_dict(include_overdue=...)` em `src/models/task_model.py`.

### [MEDIUM] Duplicated logic (AP-14)
File: routes/user_routes.py:15-23, 61, 106, 71, 120, 171-180
Description: `get_users` monta o dicionário do usuário à mão em vez de usar `User.to_dict()`; a regex de e-mail aparece em `create_user` e `update_user` (além de `utils/helpers.validate_email`, não usada); a lista de roles está repetida; `get_user_tasks` repete a regra de atraso.
Impact: Regras de usuário divergem facilmente entre cadastro e atualização.
Recommendation: P-12 — validadores de usuário em `src/controllers/validators.py`, constantes em `src/models/user_model.py`, `Task.is_overdue()` como fonte única.

### [MEDIUM] Duplicated logic (AP-14)
File: routes/report_routes.py:19-22, 33-36, 67, 132-135, 151
Description: As contagens por status repetem `task_stats` (routes/task_routes.py:276-279); a regra de atraso aparece duas vezes; a fórmula `round((x / total) * 100, 2) if total > 0 else 0` é repetida, embora `calculate_percentage` seja importado (linha 7) e não usado.
Impact: Estatísticas de `/tasks/stats` e `/reports/summary` podem divergir com o tempo.
Recommendation: P-12 — contagens e percentual centralizados em `src/models/task_model.py` / `src/services/report_service.py`.

### [MEDIUM] Missing or inconsistent input validation (AP-15)
File: routes/task_routes.py:96, 113, 167, 182, 261, 264
Description: `len(title)` e `priority < 1` são aplicados sem checar tipo (um `priority: "alta"` gera `TypeError` → 500 HTML); `/tasks/search` faz `int(priority)` e `int(user_id)` sobre a query string sem tratamento (`?priority=x` → 500); `status` da busca não é validado.
Impact: Entrada inválida derruba a requisição com 500 em vez de 400, e o cliente não sabe o que corrigir.
Recommendation: P-12 — checagem de tipo em `src/controllers/validators.py`, levantando `ValidationError` (400) (ver decisão 6).

### [MEDIUM] Missing or inconsistent input validation (AP-15)
File: routes/user_routes.py:54, 102-103, 115, 124-125
Description: `name` não é checado quanto a tipo; `update_user` aceita `name` vazio; `len(data['password'])` quebra com valor não-string; `active` aceita qualquer tipo.
Impact: Dados inválidos persistidos (usuário sem nome, `active` com string) ou 500 em entrada malformada.
Recommendation: P-12 — validadores de usuário em `src/controllers/validators.py`.

### [MEDIUM] Missing or inconsistent input validation (AP-15)
File: routes/report_routes.py:173, 196-202
Description: `update_category` não verifica corpo vazio (`'name' in data` com `data = None` → `TypeError` → 500), aceita `name` vazio e `color` em qualquer formato (`utils/helpers.is_valid_color` existe e não é usado); `create_category` não checa o tipo de `name`.
Impact: 500 em corpo vazio e categorias com nome vazio/cor inválida.
Recommendation: P-12 — `validate_category_payload` em `src/controllers/validators.py`, mantendo as mensagens atuais.

### [MEDIUM] Scattered or leaky error handling (AP-16)
File: routes/task_routes.py:62, 137, 151, 204, 221, 236
Description: `get_tasks` envolve o handler inteiro em `try/except:` genérico; parse de data usa `except:` nu; commits usam `except:`/`except Exception as e` local em cada handler; não há handler central de erros na app.
Impact: Erros reais são mascarados (sem log), e o formato de erro depende de cada handler.
Recommendation: P-10 — `src/middlewares/error_handler.py` com `AppError`/`ValidationError`/`NotFoundError` e handler de `HTTPException`; handlers sem `try/except`.

### [MEDIUM] Scattered or leaky error handling (AP-16)
File: routes/user_routes.py:87, 130, 149
Description: `create_user` usa `except Exception as e` e só imprime `str(e)`; `update_user` e `delete_user` usam `except:` nu.
Impact: Falhas de banco são engolidas sem log estruturado.
Recommendation: P-10 — erros propagam até `src/middlewares/error_handler.py`.

### [MEDIUM] Scattered or leaky error handling (AP-16)
File: routes/report_routes.py:186, 207, 221
Description: `create_category`, `update_category` e `delete_category` usam `except:` nu em volta do commit.
Impact: Qualquer exceção (inclusive bugs) vira "Erro ao ..." sem log.
Recommendation: P-10 — `src/middlewares/error_handler.py`.

### [MEDIUM] Scattered or leaky error handling (AP-16)
File: utils/helpers.py:46, 49, 88
Description: `parse_date` aninha dois `except:` nus e `process_task_data` usa `except:` em `int(data['priority'])`.
Impact: `except:` nu captura até `KeyboardInterrupt`/`SystemExit`.
Recommendation: P-10 — capturar `ValueError`/`TypeError` explicitamente no validador em `src/controllers/validators.py` (o módulo helpers é removido, ver AP-21).

### [MEDIUM] Deprecated APIs (AP-17)
File: routes/task_routes.py:31, 42, 51, 67, 72, 117, 122, 158, 188, 195, 215, 227, 285
Description: `datetime.utcnow()` (obsoleto desde Python 3.12) e `Model.query.get(id)` (legado no SQLAlchemy 2.0 / Flask-SQLAlchemy 3.1.1).
Impact: `DeprecationWarning` em runtime e quebra futura ao atualizar Python/SQLAlchemy.
Recommendation: P-13 — `datetime.now(timezone.utc).replace(tzinfo=None)` via helper `utcnow()` e `db.session.get(Model, id)` em `src/models/`.

### [MEDIUM] Deprecated APIs (AP-17)
File: routes/user_routes.py:29, 94, 136, 155, 172
Description: `User.query.get(user_id)` e `datetime.utcnow()`.
Impact: Mesmos avisos/quebra futura.
Recommendation: P-13 — `db.session.get(User, id)` e `utcnow()` helper.

### [MEDIUM] Deprecated APIs (AP-17)
File: routes/report_routes.py:35, 42, 45, 71, 105, 133, 192, 213
Description: `datetime.utcnow()` e `User.query.get` / `Category.query.get`.
Impact: Mesmos avisos/quebra futura.
Recommendation: P-13 — `utcnow()` helper e `db.session.get(...)`.

### [MEDIUM] Deprecated APIs (AP-17)
File: models/task.py:15, 16, 52
Description: `default=datetime.utcnow`, `onupdate=datetime.utcnow` e `datetime.utcnow()` em `is_overdue`.
Impact: `DeprecationWarning` a cada insert/update.
Recommendation: P-13 — `default=utcnow` (naive UTC) em `src/models/task_model.py`.

### [MEDIUM] Deprecated APIs (AP-17)
File: models/user.py:14
Description: `created_at = db.Column(db.DateTime, default=datetime.utcnow)`.
Impact: `DeprecationWarning` a cada insert.
Recommendation: P-13 — `default=utcnow` em `src/models/user_model.py`.

### [MEDIUM] Deprecated APIs (AP-17)
File: models/category.py:11
Description: `created_at = db.Column(db.DateTime, default=datetime.utcnow)`.
Impact: `DeprecationWarning` a cada insert.
Recommendation: P-13 — `default=utcnow` em `src/models/category_model.py`.

### [MEDIUM] Deprecated APIs (AP-17)
File: services/notification_service.py:35
Description: `'timestamp': datetime.utcnow()`.
Impact: `DeprecationWarning`.
Recommendation: P-13 — `utcnow()` helper em `src/services/notification_service.py`.

### [MEDIUM] Deprecated APIs (AP-17)
File: utils/helpers.py:38
Description: `timestamp = datetime.utcnow()` em `log_action`.
Impact: `DeprecationWarning` (função morta, ver AP-21).
Recommendation: P-13 — removida junto com o módulo; logging via `logging`.

### [MEDIUM] Deprecated APIs (AP-17)
File: seed.py:66, 67, 69, 70, 74
Description: `datetime.utcnow() ± timedelta(...)` para gerar `due_date` dos dados de exemplo.
Impact: `DeprecationWarning` ao rodar o seed.
Recommendation: P-13 — usar o helper `utcnow()` de `src/models/`.

### [MEDIUM] Configuration in code instead of a config module (AP-18)
File: app.py:11, 34
Description: `'sqlite:///tasks.db'` e `port=5000` fixos no entrypoint.
Impact: Impossível apontar para outro banco ou porta sem editar código (a porta 5000 colide com outros serviços locais).
Recommendation: P-01 — `DATABASE_URL` e `PORT` em `src/config/settings.py`.

### [MEDIUM] Configuration in code instead of a config module (AP-18)
File: services/notification_service.py:7-8
Description: `self.email_host = 'smtp.gmail.com'` e `self.email_port = 587` fixos no serviço.
Impact: O provedor SMTP não pode variar por ambiente.
Recommendation: P-01 — `SMTP_HOST`/`SMTP_PORT` em `src/config/settings.py`.

### [LOW] Magic numbers and strings (AP-19)
File: routes/task_routes.py:32, 96, 99, 104, 110, 113, 177, 182
Description: Limites `3` e `200` do título, prioridade padrão `3`, faixa `1`..`5`, e strings de status `'done'`, `'cancelled'`, `['pending', 'in_progress', 'done', 'cancelled']` inline.
Impact: Regras sem nome, espalhadas e fáceis de divergir.
Recommendation: P-14 — constantes `TASK_STATUSES`, `MIN_TITLE_LENGTH`, `MAX_TITLE_LENGTH`, `MIN_PRIORITY`, `MAX_PRIORITY`, `DEFAULT_PRIORITY` em `src/models/task_model.py`.

### [LOW] Magic numbers and strings (AP-19)
File: routes/user_routes.py:52, 64, 71, 115, 120
Description: Role padrão `'user'`, tamanho mínimo de senha `4`, lista `['user', 'admin', 'manager']` inline.
Impact: Regras sem nome e duplicadas.
Recommendation: P-14 — `USER_ROLES`, `DEFAULT_ROLE`, `MIN_PASSWORD_LENGTH` em `src/models/user_model.py`.

### [LOW] Magic numbers and strings (AP-19)
File: routes/report_routes.py:24-28, 45, 129, 180
Description: Prioridades `1`..`5` mapeadas inline para `critical`..`minimal`, janela `timedelta(days=7)`, `t.priority <= 2` como "alta prioridade", cor `'#000000'`.
Impact: Significado das prioridades implícito no código do relatório.
Recommendation: P-14 — `PRIORITY_LABELS`, `HIGH_PRIORITY_MAX`, `RECENT_ACTIVITY_DAYS` em `src/models/task_model.py` / `src/services/report_service.py`.

### [LOW] Magic numbers and strings (AP-19)
File: models/task.py:39, 46
Description: Lista de status e limites `1`/`5` literais em `validate_status` / `validate_priority`.
Impact: Mais uma cópia das mesmas regras.
Recommendation: P-14 — constantes de módulo em `src/models/task_model.py`.

### [LOW] Magic numbers and strings (AP-19)
File: models/category.py:10
Description: `default='#000000'` literal.
Impact: Mesma cor padrão repetida em `report_routes.py:180` e `helpers.py:116`.
Recommendation: P-14 — `DEFAULT_COLOR` em `src/models/category_model.py`.

### [LOW] Poor naming (AP-20)
File: routes/task_routes.py:16, 51, 268, 283
Description: Variáveis de domínio de uma letra ou abreviadas: `t` (task), `cat`.
Impact: Leitura mais difícil em loops longos.
Recommendation: P-14 — renomear internamente para `task`, `category` (contrato inalterado).

### [LOW] Poor naming (AP-20)
File: routes/user_routes.py:14, 37, 161
Description: `u` e `t` para usuário e task.
Impact: Leitura mais difícil.
Recommendation: P-14 — `user`, `task`.

### [LOW] Poor naming (AP-20)
File: routes/report_routes.py:24-28, 33, 55, 59, 119, 161, 192
Description: `p1`..`p5`, `t`, `u`, `c`, `cat`.
Impact: `p1`..`p5` escondem o significado (contagem por prioridade).
Recommendation: P-14 — nomes descritivos em `src/services/report_service.py`.

### [LOW] Poor naming (AP-20)
File: models/task.py:45
Description: Parâmetro `p` em `validate_priority(self, p)`.
Impact: Leitura.
Recommendation: P-14 — `priority`.

### [LOW] Poor naming (AP-20)
File: models/category.py:14
Description: Variável `d` em `to_dict`.
Impact: Leitura.
Recommendation: P-14 — retornar o dicionário diretamente.

### [LOW] Poor naming (AP-20)
File: utils/helpers.py:25, 83
Description: `s` em `sanitize_string(s)` e `p` em `process_task_data`.
Impact: Leitura (módulo morto, ver AP-21).
Recommendation: P-14 — removido junto com o módulo.

### [LOW] Poor naming (AP-20)
File: seed.py:16, 23, 30, 39, 45, 51, 57, 78, 79
Description: `u1`..`u3`, `c1`..`c4`, `td`, `t`.
Impact: Leitura do seed.
Recommendation: P-14 — nomes descritivos (`joao`, `backend`, `task_data`, `task`).

### [LOW] Unused imports and dead code (AP-21)
File: app.py:7
Description: `import os, sys, json, datetime` — `os`, `sys` e `json` nunca são usados.
Impact: Ruído.
Recommendation: Remover.

### [LOW] Unused imports and dead code (AP-21)
File: models/task.py:3, 38-48
Description: `import json` sem uso; `validate_status` e `validate_priority` nunca são chamados (as rotas reimplementam as regras).
Impact: Código morto que diverge das regras reais.
Recommendation: Remover ou transformar em fonte única via P-12.

### [LOW] Unused imports and dead code (AP-21)
File: models/user.py:34-38
Description: `is_admin()` nunca é chamado.
Impact: Código morto.
Recommendation: Reaproveitar na guarda de autorização (P-05) ou remover.

### [LOW] Unused imports and dead code (AP-21)
File: routes/task_routes.py:7
Description: `import json, os, sys, time` — nenhum é usado.
Impact: Ruído.
Recommendation: Remover.

### [LOW] Unused imports and dead code (AP-21)
File: routes/user_routes.py:6
Description: `hashlib` e `json` importados e não usados.
Impact: Ruído (`hashlib` sugere hashing nas rotas).
Recommendation: Remover.

### [LOW] Unused imports and dead code (AP-21)
File: routes/report_routes.py:7, 8
Description: `format_date`, `calculate_percentage` e `json` importados e não usados.
Impact: Ruído.
Recommendation: Remover.

### [LOW] Unused imports and dead code (AP-21)
File: utils/helpers.py:2-7, 9-116
Description: `os`, `json`, `sys`, `math`, `hashlib` sem uso; nenhuma função do módulo (`process_task_data`, `validate_email`, `parse_date`, `is_valid_color`, `log_action`, ...) nem as constantes `VALID_STATUSES` etc. são chamadas pela aplicação.
Impact: Um segundo conjunto de regras, divergente, que ninguém executa.
Recommendation: Aproveitar as constantes nos models (P-14) e apagar `utils/helpers.py`.

### [LOW] Print-debugging instead of logging (AP-22)
File: routes/task_routes.py:149, 153, 219, 234
Description: `print(f"Task criada: ...")`, `print(f"Erro ao criar task: {str(e)}")` etc.
Impact: Sem nível nem timestamp; erros não aparecem como erros.
Recommendation: P-15 — `logging.getLogger(__name__)` nos controllers.

### [LOW] Print-debugging instead of logging (AP-22)
File: routes/user_routes.py:83, 89, 147
Description: `print(f"Usuário criado: ...")`, `print(f"ERRO: {str(e)}")`, `print(f"Usuário deletado: ...")`.
Impact: Idem.
Recommendation: P-15.

### [LOW] Print-debugging instead of logging (AP-22)
File: services/notification_service.py:21, 24
Description: `print(f"Email enviado para {to}")` e `print(f"Erro ao enviar email: ...")`.
Impact: Idem.
Recommendation: P-15 — `logger.info` / `logger.warning` no serviço.

### [LOW] Print-debugging instead of logging (AP-22)
File: utils/helpers.py:39, 41
Description: `log_action` implementa "log" com `print`.
Impact: Idem (função morta).
Recommendation: P-15 — removida; usar `logging`.

### [LOW] Verbose control flow (AP-23)
File: models/task.py:39-43, 46-48, 50-60
Description: `if ...: return True else: return False` em `validate_status`/`validate_priority`, e pirâmide de três `if` aninhados em `is_overdue`.
Impact: Leitura.
Recommendation: P-14 — `return self.due_date is not None and self.due_date < utcnow() and self.status not in CLOSED_STATUSES`.

### [LOW] Verbose control flow (AP-23)
File: models/user.py:35-38
Description: `is_admin` com `if self.role == 'admin': return True else: return False`.
Impact: Leitura.
Recommendation: P-14 — `return self.role == ROLE_ADMIN`.

### [LOW] Verbose control flow (AP-23)
File: routes/task_routes.py:30-39, 71-80, 141, 210, 283-287
Description: Pirâmides de `if` para o booleano `overdue`, `type(tags) == list` em vez de `isinstance`, `overdue_count = overdue_count + 1`.
Impact: Leitura.
Recommendation: P-14 — `task.is_overdue()`, `isinstance`, contagem agrupada.

### [LOW] Verbose control flow (AP-23)
File: routes/user_routes.py:171-180
Description: Pirâmide de `if` para `overdue`.
Impact: Leitura.
Recommendation: P-14 — `task.is_overdue()`.

### [LOW] Verbose control flow (AP-23)
File: routes/report_routes.py:33-37, 57-61, 119-135
Description: `if` aninhados para atraso e contadores manuais `x = x + 1` por status.
Impact: Leitura.
Recommendation: P-14 — `sum(...)`/`Counter` e `task.is_overdue()` no `report_service`.

### [LOW] Verbose control flow (AP-23)
File: utils/helpers.py:21-23, 53-55, 103
Description: `if ...: return True / return False` e `type(tags) == list`.
Impact: Leitura (módulo morto).
Recommendation: P-14 — removido com o módulo.

================================
Total: 68 findings
================================

## Decisions requiring approval
1. Campo `password` removido das respostas de GET /users/<id>, POST /users, PUT /users/<id> e de `user` em POST /login — expõe o hash da senha (AP-06) — default: remover o campo; demais chaves inalteradas.
2. Formato do hash de senha muda de MD5 para `werkzeug.security` (pbkdf2/scrypt) — MD5 sem salt é inseguro (AP-05) — default: novos hashes no formato werkzeug; hashes MD5 já gravados continuam aceitos no login e são regravados no novo formato ao logar com sucesso.
3. POST /users passa a ignorar `role` do corpo e grava sempre `user` — auto-cadastro como admin (AP-11) — default: ignorar `role` no cadastro; troca de role continua possível via PUT /users/<id>.
4. Token de login e autenticação — `fake-jwt-token-<id>` é adivinhável (AP-11) — default: `token` passa a ser um token assinado com `SECRET_KEY` (mesma chave `token`, valor diferente); uma guarda `require_auth` é adicionada às rotas de escrita (POST/PUT/DELETE de tasks, users e categories, exceto POST /users e POST /login), controlada por `AUTH_REQUIRED`, que vem **desligado** por padrão para preservar o contrato atual.
5. Servidor sobe com `debug` desligado e host `127.0.0.1` por padrão (antes `debug=True`, `0.0.0.0`) — debugger do Werkzeug permite RCE (AP-12) — default: `FLASK_DEBUG=0`, `HOST=127.0.0.1`, `PORT=5000`, todos configuráveis por ambiente.
6. Erros normalizados em JSON `{"error": "..."}` — hoje entradas de tipo inválido (ex.: `priority: "alta"`, `?priority=x`, PUT /categories sem corpo) e 404/405 do Flask respondem 500/404 em HTML (AP-15, AP-16) — default: tipos inválidos passam a responder 400 com `{"error": ...}`, 404/405 do Flask em JSON, 500 inesperado com `{"error": "Erro interno"}`; mensagens existentes mantidas.
7. DELETE /categories/<id> passa a anular `category_id` das tasks dessa categoria — hoje ficam órfãs (AP-10) — default: anular na mesma transação.
8. `NotificationService` passa a ser usado: ao criar/atribuir uma task a um usuário é disparada notificação — serviço morto (AP-08) — default: sem `SMTP_HOST` configurado o serviço apenas registra em log (nenhum e-mail é enviado); resposta HTTP inalterada.

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
