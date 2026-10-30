================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python + Flask 3.0.0 (SQLite via Flask-SQLAlchemy 3.1.1)
Files:   12 analyzed | ~1155 lines of code

## Summary
CRITICAL: 5 | HIGH: 11 | MEDIUM: 24 | LOW: 27

## Findings

### [CRITICAL] Hardcoded credentials and secrets (AP-01)
File: app.py:13
Description: `app.config['SECRET_KEY'] = 'super-secret-key-123'` é um literal no código-fonte versionado.
Impact: Qualquer pessoa com acesso ao repositório conhece a chave usada para assinar sessões/tokens e pode forjá-los assim que a autenticação real existir.
Recommendation: P-01 — ler `SECRET_KEY` do ambiente em `src/config/settings.py` (fallback `secrets.token_hex(32)`), documentar em `.env.example`.

### [CRITICAL] Hardcoded credentials and secrets (AP-01)
File: services/notification_service.py:7-10
Description: `NotificationService.__init__` fixa `email_user = 'taskmanager@gmail.com'` e `email_password = 'senha123'`; `email_host = 'smtp.gmail.com'` e `email_port = 587` também são literais (AP-18 no mesmo trecho).
Impact: Credencial SMTP vazada no repositório; impossível trocar servidor/conta por ambiente.
Recommendation: P-01 — `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` em `src/config/settings.py`, injetados em `src/services/notification_service.py`.

### [CRITICAL] Plaintext or weak password storage (AP-05)
File: models/user.py:29, 32
Description: `set_password` grava `hashlib.md5(pwd.encode()).hexdigest()` e `check_password` compara o mesmo MD5 sem salt; `seed.py:19, 26, 33` persiste as senhas `'1234'`, `'abcd'`, `'pass'` por esse caminho.
Impact: MD5 sem salt é revertido por rainbow tables em segundos; um vazamento do banco expõe todas as senhas.
Recommendation: P-04 — `werkzeug.security.generate_password_hash` / `check_password_hash` em `src/models/user_model.py`; re-seed.

### [CRITICAL] Sensitive data exposure (AP-06)
File: models/user.py:21
Description: `User.to_dict()` inclui `'password': self.password` (o hash).
Impact: Todo endpoint que serializa um usuário entrega o hash da senha ao cliente.
Recommendation: P-05 — remover `password` de `to_dict()` em `src/models/user_model.py`.

### [CRITICAL] Sensitive data exposure (AP-06)
File: routes/user_routes.py:33, 85, 129, 209
Description: `get_user`, `create_user`, `update_user` e `login` respondem com `user.to_dict()`, que contém o hash MD5; o `login` o devolve dentro de `'user'`.
Impact: Um GET anônimo em `/users/<id>` entrega o hash de qualquer usuário, inclusive do admin, pronto para ser quebrado (ver AP-05).
Recommendation: P-05 — as views em `src/views/user_routes.py` usam o serializer sem senha.

### [HIGH] Business logic in the controller / route (fat controller) (AP-07)
File: routes/task_routes.py:12-63, 86-154, 157-223, 274-299
Description: `get_tasks` (52 linhas) calcula `overdue`, resolve `user_name`/`category_name` e monta o dict; `create_task` e `update_task` validam, verificam FKs, parseiam data e normalizam `tags`; `task_stats` agrega contagens e `completion_rate`.
Impact: As regras não podem ser testadas sem HTTP e se espalham por várias rotas.
Recommendation: P-06 — `src/controllers/task_controller.py` com as regras; as views em `src/views/task_routes.py` ficam com uma linha por handler.

### [HIGH] Business logic in the controller / route (fat controller) (AP-07)
File: routes/report_routes.py:13-101, 104-155
Description: `summary_report` (89 linhas) e `user_report` fazem toda a agregação do relatório (status, prioridades, atrasadas, `days_overdue`, produtividade por usuário) dentro da rota; o CRUD de categorias também mora neste blueprint de relatórios.
Impact: A lógica de relatório não é reutilizável nem testável, e o domínio de categorias está misturado com o de relatórios.
Recommendation: P-06 — `src/services/report_service.py` + `src/controllers/category_controller.py`; views `src/views/report_routes.py` e `src/views/category_routes.py`.

### [HIGH] Business logic in the controller / route (fat controller) (AP-07)
File: routes/user_routes.py:43-90, 93-132, 154-183
Description: `create_user` (48 linhas) e `update_user` aplicam validação de email, unicidade, regra de role e hashing; `get_user_tasks` calcula `overdue` e serializa manualmente.
Impact: As regras de cadastro ficam acopladas ao Flask e duplicadas entre create e update.
Recommendation: P-06 — `src/controllers/user_controller.py`; views finas em `src/views/user_routes.py`.

### [HIGH] Tight coupling / no dependency injection (AP-08)
File: app.py:9-31
Description: `app = Flask(__name__)` em nível de módulo, sem `create_app()`; `db.create_all()` roda no import (linhas 30-31); as rotas importam o singleton `db` diretamente (`routes/task_routes.py:2`, `routes/user_routes.py:2`, `routes/report_routes.py:2`), e `seed.py:2` importa `app` pronto.
Impact: Não dá para criar uma app com outra configuração/banco para testes, e importar `app` já toca o disco.
Recommendation: P-07 — `src/app.py` com `create_app(settings)` como composition root; `app.py` vira entrypoint fino.

### [HIGH] Tight coupling / no dependency injection (AP-08)
File: services/notification_service.py:4-48
Description: `NotificationService` está definido e nunca é importado nem instanciado; dentro dele `smtplib.SMTP(...)` está fixo (linha 15).
Impact: Código morto que finge ter um recurso de notificação; não pode ser substituído por um fake em testes.
Recommendation: P-07 — instanciar em `create_app()` e injetar em `TaskController`; transporte configurável.

### [HIGH] Mutable global state (AP-09)
File: services/notification_service.py:6, 31
Description: `self.notifications = []` serve de armazenamento, e `notify_task_assigned` faz append nele.
Impact: Dados perdidos a cada reinício, sem limite de crescimento e não compartilhados entre workers.
Recommendation: P-08 — uma única instância, criada na composition root e injetada (persistência fora de escopo), com o estado no objeto injetado.

### [HIGH] Non-atomic multi-step writes and orphaned data (AP-10)
File: routes/report_routes.py:218-219
Description: `delete_category` apaga a categoria e deixa as tasks com `category_id` apontando para uma linha inexistente (o SQLite roda sem `PRAGMA foreign_keys`).
Impact: Tasks órfãs: `category_id` aponta para uma categoria que não existe mais, e os relatórios ficam inconsistentes.
Recommendation: P-11 — em `src/controllers/category_controller.py`, zerar `category_id` das tasks e apagar a categoria na mesma transação.

### [HIGH] Missing authentication / authorization (AP-11)
File: routes/user_routes.py:10, 27, 52, 71-78, 92-125, 134, 153, 210
Description: Listagem, leitura, alteração e exclusão de usuários são anônimas; `create_user` aceita `role` do corpo (qualquer um se cadastra como `admin`); `update_user` deixa qualquer cliente trocar `role`/`active`/senha de qualquer usuário; `login` devolve `'fake-jwt-token-' + str(user.id)`.
Impact: Escalada de privilégio trivial e takeover de contas; o token é adivinhável e não é verificado em lugar nenhum.
Recommendation: P-16 — tokens assinados (itsdangerous) em `src/middlewares/auth.py`, com guards `require_auth`/`require_admin`/`require_self_or_admin` aplicados em `src/views/user_routes.py`.

### [HIGH] Missing authentication / authorization (AP-11)
File: routes/task_routes.py:11, 65, 85, 156, 225, 240, 273
Description: Todas as rotas de tasks, inclusive `PUT` e `DELETE /tasks/<id>`, respondem sem autenticação e sem checar se a task pertence ao chamador (`task.user_id`).
Impact: Qualquer cliente anônimo altera ou apaga tasks de qualquer usuário.
Recommendation: P-16 — `require_auth` nas leituras; dono-ou-admin em PUT/DELETE, no controller `src/controllers/task_controller.py`.

### [HIGH] Missing authentication / authorization (AP-11)
File: routes/report_routes.py:12, 103, 157, 167, 190, 211
Description: `/reports/summary` (com nome e produtividade de todos os usuários), `/reports/user/<id>` (com email) e o CRUD de categorias são públicos.
Impact: Vazamento de dados de usuários e alteração/remoção anônima de categorias.
Recommendation: P-16 — admin em summary e nas escritas de categorias; dono-ou-admin em `/reports/user/<id>`.

### [HIGH] Debug mode and unsafe defaults in the entry point (AP-12)
File: app.py:15, 34
Description: `CORS(app)` sem lista de origens; `app.run(debug=True, host='0.0.0.0', port=5000)`.
Impact: O debugger do Werkzeug exposto em todas as interfaces permite execução remota de código; qualquer origem chama a API.
Recommendation: P-01 — `DEBUG` falso, `HOST=127.0.0.1` e `CORS_ORIGINS` explícito por padrão, em `src/config/settings.py`.

### [MEDIUM] N+1 queries (AP-13)
File: routes/task_routes.py:41-57, 275-287
Description: `get_tasks` chama `User.query.get` e `Category.query.get` para cada task; `task_stats` faz 5 `count()` separados e mais um `Task.query.all()`.
Impact: 2N+1 queries por listagem; a latência cresce linearmente.
Recommendation: P-09 — `joinedload(Task.user, Task.category)` e um `GROUP BY status` em `src/models/task_model.py`.

### [MEDIUM] N+1 queries (AP-13)
File: routes/user_routes.py:22
Description: `len(u.tasks)` dispara um lazy load por usuário em `get_users`.
Impact: N+1 queries na listagem de usuários.
Recommendation: P-09 — contagem com `GROUP BY user_id` em `src/models/user_model.py`.

### [MEDIUM] N+1 queries (AP-13)
File: routes/report_routes.py:15-28, 53-56, 163
Description: `summary_report` executa 12 `count()` separados e um `Task.query.filter_by(user_id=u.id)` por usuário; `get_categories` faz um `count()` por categoria.
Impact: Dezenas de queries por relatório.
Recommendation: P-09 — agregações `GROUP BY` em `src/services/report_service.py` / `src/models/category_model.py`.

### [MEDIUM] Duplicated logic (AP-14)
File: routes/task_routes.py:17-39, 71-80, 110, 177, 284-287
Description: A regra de atraso está escrita três vezes mesmo existindo `Task.is_overdue()`; `get_tasks` monta à mão o mesmo dict que `Task.to_dict()`; a lista de status está repetida (110, 177) apesar de `VALID_STATUSES`/`process_task_data` em `utils/helpers.py`.
Impact: Uma mudança de regra exige editar vários lugares; as cópias já divergem (o create aceita `'%Y-%m-%d'`, o helper aceita dois formatos).
Recommendation: P-12 — `to_dict(include_overdue=True)` em `src/models/task_model.py` e um único validador em `src/controllers/validators.py`.

### [MEDIUM] Duplicated logic (AP-14)
File: routes/user_routes.py:15-23, 61, 71, 106, 120, 162-180
Description: Serializers montados à mão (usuário e task), regex de email (61, 106) e lista de roles (71, 120) duplicados; a regra de atraso foi copiada de novo em `get_user_tasks`.
Impact: Divergência garantida entre create/update e entre rotas.
Recommendation: P-12 — `validar_usuario` único e serializers do model.

### [MEDIUM] Duplicated logic (AP-14)
File: routes/report_routes.py:34-36, 67, 132-135, 151
Description: A regra de atraso aparece mais duas vezes; o cálculo de `completion_rate` repete `calculate_percentage`, que é importado e nunca usado.
Impact: Mesma regra em 6 lugares no projeto.
Recommendation: P-12 — usar `Task.is_overdue()` e um único helper de percentual em `src/services/report_service.py`.

### [MEDIUM] Missing or inconsistent input validation (AP-15)
File: routes/task_routes.py:93-113, 167, 182, 261, 264
Description: `priority < 1` com string ou `len(title)` com valor não-string geram `TypeError` → 500; `update_task` não checa título vazio nem `None`; `int(priority)`/`int(user_id)` em `/tasks/search` estouram 500 com entrada inválida.
Impact: Entrada inválida vira 500 em vez de 400.
Recommendation: P-12 — validador único com checagem de tipo em `src/controllers/validators.py`.

### [MEDIUM] Missing or inconsistent input validation (AP-15)
File: routes/user_routes.py:102-103, 115, 124-125
Description: `update_user` aceita `name` vazio, `len(data['password'])` quebra com não-string, e `active` aceita qualquer tipo.
Impact: Dados inválidos persistidos ou 500.
Recommendation: P-12 — mesmas regras do create aplicadas no update.

### [MEDIUM] Missing or inconsistent input validation (AP-15)
File: routes/report_routes.py:180, 196-202
Description: `update_category` faz `'name' in data` sem checar `None` (corpo ausente → 500); `color` nunca é validada (o `is_valid_color` existe e não é usado).
Impact: 500 com corpo vazio; cores inválidas gravadas.
Recommendation: P-12 — `validar_categoria` em `src/controllers/validators.py`.

### [MEDIUM] Scattered or leaky error handling (AP-16)
File: routes/task_routes.py:13, 62, 137, 151-154, 204, 221-223, 236
Description: Um `try/except:` genérico envolve `get_tasks` inteiro; há `except:` sem tipo em vários handlers e nenhum error handler central (`app.py` não registra `errorhandler`).
Impact: Bugs reais são engolidos como "Erro interno" sem log; o tratamento varia por rota.
Recommendation: P-10 — `src/middlewares/error_handler.py` com `AppError`/`HTTPException`/catch-all, mantendo a chave `error`.

### [MEDIUM] Scattered or leaky error handling (AP-16)
File: routes/user_routes.py:87-90, 130, 149
Description: `except Exception` com `print(str(e))` e dois `except:` sem tipo.
Impact: Erros sem log estruturado e com tratamento inconsistente.
Recommendation: P-10.

### [MEDIUM] Scattered or leaky error handling (AP-16)
File: routes/report_routes.py:186, 207, 221
Description: `except:` sem tipo em create, update e delete de categoria.
Impact: Engole qualquer exceção, inclusive erros de programação.
Recommendation: P-10.

### [MEDIUM] Scattered or leaky error handling (AP-16)
File: utils/helpers.py:46, 49, 88
Description: `parse_date` e `process_task_data` usam `except:` sem tipo.
Impact: Captura até `KeyboardInterrupt`/`SystemExit`.
Recommendation: P-10 — `except ValueError` / `(TypeError, ValueError)`.

### [MEDIUM] Deprecated APIs (AP-17)
File: models/task.py:15, 16, 52
Description: `default=datetime.utcnow`, `onupdate=datetime.utcnow` e `datetime.utcnow()` em `is_overdue`.
Impact: Deprecado no Python 3.12, com warnings que vão virar erro.
Recommendation: P-13 — helper `utcnow()` com `datetime.now(timezone.utc).replace(tzinfo=None)`.

### [MEDIUM] Deprecated APIs (AP-17)
File: models/user.py:14
Description: `default=datetime.utcnow`.
Impact: Deprecado no Python 3.12.
Recommendation: P-13 — `datetime.now(timezone.utc)` (naive).

### [MEDIUM] Deprecated APIs (AP-17)
File: models/category.py:11
Description: `default=datetime.utcnow`.
Impact: Deprecado no Python 3.12.
Recommendation: P-13 — `datetime.now(timezone.utc)` (naive).

### [MEDIUM] Deprecated APIs (AP-17)
File: services/notification_service.py:35
Description: `datetime.utcnow()` no timestamp da notificação.
Impact: Deprecado no Python 3.12.
Recommendation: P-13 — `datetime.now(timezone.utc)`.

### [MEDIUM] Deprecated APIs (AP-17)
File: utils/helpers.py:38
Description: `datetime.utcnow()` em `log_action`.
Impact: Deprecado no Python 3.12.
Recommendation: P-13 — `datetime.now(timezone.utc)` (ou remover, ver AP-21).

### [MEDIUM] Deprecated APIs (AP-17)
File: seed.py:66, 67, 69, 70, 74
Description: `datetime.utcnow()` ao calcular os `due_date` do seed.
Impact: Deprecado no Python 3.12.
Recommendation: P-13 — helper `utcnow()` compartilhado.

### [MEDIUM] Deprecated APIs (AP-17)
File: routes/task_routes.py:31, 42, 51, 67, 72, 117, 122, 158, 188, 195, 215, 227, 285
Description: `Model.query.get(id)` (legado no SQLAlchemy 2.0) e `datetime.utcnow()`.
Impact: Warnings no Flask-SQLAlchemy 3.1; a API será removida.
Recommendation: P-13 — `db.session.get(Model, id)` e `utcnow()`.

### [MEDIUM] Deprecated APIs (AP-17)
File: routes/user_routes.py:29, 94, 136, 155, 172
Description: `User.query.get(...)` e `datetime.utcnow()`.
Impact: APIs legadas/deprecadas.
Recommendation: P-13 — `db.session.get(User, id)` e `utcnow()`.

### [MEDIUM] Deprecated APIs (AP-17)
File: routes/report_routes.py:35, 42, 45, 71, 105, 133, 192, 213
Description: `datetime.utcnow()`, `User.query.get` e `Category.query.get`.
Impact: APIs legadas/deprecadas.
Recommendation: P-13 — `db.session.get(...)` e `utcnow()`.

### [MEDIUM] Configuration in code instead of a config module (AP-18)
File: app.py:11, 34
Description: `'sqlite:///tasks.db'` e `port=5000` são literais no entrypoint.
Impact: Não dá para trocar banco/porta por ambiente.
Recommendation: P-01 — `DATABASE_URL` e `PORT` em `src/config/settings.py`.

### [LOW] Magic numbers and strings (AP-19)
File: routes/task_routes.py:96, 99, 104, 110, 113, 177, 182
Description: Limites `3`/`200` do título, prioridade padrão `3`, faixa `1..5` e literais de status inline.
Impact: Regras sem nome, duplicadas entre rotas.
Recommendation: P-14 — constantes nomeadas em `src/models/task_model.py`.

### [LOW] Magic numbers and strings (AP-19)
File: routes/user_routes.py:52, 64, 71, 115, 120
Description: `'user'` padrão, tamanho mínimo de senha `4` e lista de roles literal.
Impact: Regras implícitas e repetidas.
Recommendation: P-14 — `MIN_PASSWORD_LENGTH`, `VALID_ROLES`, `ROLE_USER`.

### [LOW] Magic numbers and strings (AP-19)
File: routes/report_routes.py:24-28, 45, 129, 180
Description: Prioridades `1..5` mapeadas para nomes inline, janela de `7` dias, `priority <= 2` como "alta" e `'#000000'`.
Impact: O significado das regras não fica explícito.
Recommendation: P-14 — constantes em `src/services/report_service.py`.

### [LOW] Magic numbers and strings (AP-19)
File: models/task.py:11, 12, 39, 46, 53
Description: `'pending'`, `3`, lista de status e `1`/`5` como literais.
Impact: Fonte de verdade implícita.
Recommendation: P-14 — `VALID_STATUSES`, `DEFAULT_PRIORITY`, `PRIORITY_RANGE`.

### [LOW] Magic numbers and strings (AP-19)
File: models/category.py:10
Description: `default='#000000'`.
Impact: Literal repetido em `report_routes.py:180` e `utils/helpers.py:116`.
Recommendation: P-14 — `DEFAULT_COLOR` único.

### [LOW] Poor naming (AP-20)
File: routes/task_routes.py:16, 51, 268, 283
Description: `t`, `cat` para tasks e categorias.
Impact: Leitura mais difícil.
Recommendation: P-14 — `task`, `category`.

### [LOW] Poor naming (AP-20)
File: routes/user_routes.py:14, 37, 141, 161
Description: `u`, `t`.
Impact: Leitura mais difícil.
Recommendation: P-14.

### [LOW] Poor naming (AP-20)
File: routes/report_routes.py:24-28, 33, 55, 59, 119, 160, 192
Description: `p1`..`p5`, `u`, `t`, `c`, `cat`.
Impact: Leitura mais difícil.
Recommendation: P-14.

### [LOW] Poor naming (AP-20)
File: models/user.py:27, 31
Description: Parâmetro `pwd`.
Impact: Nome críptico.
Recommendation: P-14 — `raw_password`.

### [LOW] Poor naming (AP-20)
File: models/task.py:45
Description: Parâmetro `p`.
Impact: Nome críptico.
Recommendation: P-14 — `priority`.

### [LOW] Poor naming (AP-20)
File: models/category.py:14
Description: Variável `d` em `to_dict`.
Impact: Nome críptico.
Recommendation: P-14 — retornar o dict direto.

### [LOW] Poor naming (AP-20)
File: utils/helpers.py:25, 83
Description: `s`, `p`.
Impact: Nome críptico.
Recommendation: P-14.

### [LOW] Unused imports and dead code (AP-21)
File: app.py:7
Description: `os`, `sys`, `json` importados e nunca usados.
Impact: Ruído.
Recommendation: Remover.

### [LOW] Unused imports and dead code (AP-21)
File: routes/task_routes.py:7
Description: `json`, `os`, `sys`, `time` não usados.
Impact: Ruído.
Recommendation: Remover.

### [LOW] Unused imports and dead code (AP-21)
File: routes/user_routes.py:6
Description: `hashlib`, `json` não usados.
Impact: Ruído.
Recommendation: Remover.

### [LOW] Unused imports and dead code (AP-21)
File: routes/report_routes.py:7-8
Description: `format_date`, `calculate_percentage` e `json` importados e não usados.
Impact: Ruído e uma falsa impressão de reuso.
Recommendation: Remover (ou usar o helper, ver AP-14).

### [LOW] Unused imports and dead code (AP-21)
File: models/task.py:3, 38-48
Description: `json` não usado; `validate_status` e `validate_priority` nunca chamados.
Impact: Código morto que diverge das validações reais.
Recommendation: Remover ou tornar a fonte única de validação (P-12).

### [LOW] Unused imports and dead code (AP-21)
File: models/user.py:34-38
Description: `is_admin()` nunca é chamado; também é verboso (AP-23: `if ... return True else return False`).
Impact: Código morto.
Recommendation: Reescrever como `return self.role == ROLE_ADMIN` e usar no guard de admin (P-16).

### [LOW] Unused imports and dead code (AP-21)
File: utils/helpers.py:3-7, 9-108, 110-116
Description: `os`, `json`, `sys`, `math`, `hashlib` não usados; `validate_email`, `sanitize_string`, `generate_id`, `log_action`, `parse_date`, `is_valid_color`, `process_task_data` e todas as constantes nunca são referenciados fora do módulo.
Impact: Módulo inteiro morto, duplicando regras que as rotas reimplementam.
Recommendation: Mover o que for útil para `src/controllers/validators.py` e apagar o resto.

### [LOW] Print-debugging instead of logging (AP-22)
File: routes/task_routes.py:149, 153, 219, 234
Description: `print(f"Task criada: ...")` etc.
Impact: Sem nível nem destino configurável.
Recommendation: P-15 — `logging.getLogger(__name__)`.

### [LOW] Print-debugging instead of logging (AP-22)
File: routes/user_routes.py:83, 89, 147
Description: `print` de criação, erro e exclusão de usuário.
Impact: Sem nível nem destino configurável.
Recommendation: P-15.

### [LOW] Print-debugging instead of logging (AP-22)
File: services/notification_service.py:21, 24
Description: `print` do resultado do envio de email.
Impact: Sem nível nem destino configurável.
Recommendation: P-15.

### [LOW] Print-debugging instead of logging (AP-22)
File: utils/helpers.py:39, 41
Description: `log_action` implementado com `print`.
Impact: Sem nível nem destino configurável.
Recommendation: P-15.

### [LOW] Verbose control flow (AP-23)
File: models/task.py:50-60
Description: `is_overdue` em pirâmide de três `if` aninhados para um único booleano.
Impact: Leitura difícil.
Recommendation: P-14 — uma expressão booleana.

### [LOW] Verbose control flow (AP-23)
File: routes/task_routes.py:141, 210, 287
Description: `type(tags) == list` em vez de `isinstance`; `overdue_count = overdue_count + 1` em loop de contagem.
Impact: Idioma não-pythônico.
Recommendation: P-14 — `isinstance`, `sum(...)`.

### [LOW] Verbose control flow (AP-23)
File: routes/report_routes.py:37, 61, 119-127
Description: Contadores manuais com `x = x + 1` e uma cadeia `if/elif` por status.
Impact: Verboso.
Recommendation: P-14 — `Counter`/`sum`.

### [LOW] Verbose control flow (AP-23)
File: utils/helpers.py:21-23, 53-55, 103
Description: `if ...: return True / return False` e `type(tags) == list`.
Impact: Verboso.
Recommendation: P-14.

================================
Total: 67 findings
================================

## Decisions requiring approval
1. `password` removido de todas as respostas de usuário (`GET /users/<id>`, `POST /users`, `PUT /users/<id>` e `user` do `POST /login`) — AP-06 — default: o campo deixa de existir; as demais chaves ficam iguais.
2. Formato do hash de senha passa de MD5 para `werkzeug.security` — AP-05 — default: sem fallback MD5; hashes MD5 já gravados deixam de bater, e o `tasks.db` precisa de `python seed.py` (que já é passo obrigatório do README).
3. Autenticação obrigatória por padrão (P-16) — AP-11 — default: `POST /login` mantém as chaves e devolve em `token` um token assinado (itsdangerous, `SECRET_KEY`, validade de 24h); clientes enviam `Authorization: Bearer <token>`; `401` sem token ou com token inválido, `403` sem permissão. Política:
   - Público: `GET /`, `GET /health`, `POST /login`, `POST /users` (cadastro).
   - Autenticado: `GET /tasks`, `GET /tasks/<id>`, `GET /tasks/search`, `GET /tasks/stats`, `POST /tasks`, `GET /categories`.
   - Dono ou admin: `PUT`/`DELETE /tasks/<id>` (via `task.user_id`; tasks sem dono só admin), `GET`/`PUT /users/<id>`, `GET /users/<id>/tasks`, `GET /reports/user/<id>`. Quem não é admin só cria ou reatribui tasks para si mesmo (`user_id` nulo ou o próprio id), senão recebe `403`.
   - Admin: `GET /users`, `DELETE /users/<id>`, `GET /reports/summary`, `POST`/`PUT`/`DELETE /categories`. `manager` não ganha privilégios (o código original não dá nenhum).
   - Admin documentado no README: `joao@email.com` / `1234` (vem do seed).
4. `role` no cadastro público — AP-11 — default: em `POST /users`, `role` só é respeitado quando o chamador é admin autenticado; nos demais casos o usuário é criado como `user` (role inválido continua `400`). Em `PUT /users/<id>`, alterar `role` ou `active` exige admin (`403` caso contrário).
5. `DELETE /categories/<id>` desvincula as tasks — AP-10 — default: as tasks da categoria ficam com `category_id = null` na mesma transação.
6. Erros de entrada passam de 500 para 400 — AP-15/AP-16 — default: corpo `{"error": ...}` mantido; `priority`/`title` com tipo errado, `?priority=abc`/`?user_id=abc` em `/tasks/search` e `PUT /categories` sem corpo passam a responder `400`; 500 inesperado responde `{"error": "Erro interno"}` e é logado.
7. Defaults do servidor — AP-01/AP-12/AP-18 — default: `SECRET_KEY` vem do ambiente (sem ela, uma chave aleatória por boot, o que invalida os tokens a cada restart); `debug` desligado; bind em `127.0.0.1` (`HOST=0.0.0.0` é opt-in); CORS restrito a `CORS_ORIGINS`, padrão `http://localhost:5000,http://127.0.0.1:5000`; `DATABASE_URL` padrão `sqlite:///tasks.db`; SMTP via `SMTP_*`; `.env.example` adicionado.
8. NotificationService ligado — AP-08/AP-09 — default: instância única criada em `create_app()` e injetada no `TaskController`, chamada ao atribuir uma task a um usuário; sem `SMTP_HOST` configurado, o envio só é logado (nenhuma conexão de rede), e as respostas HTTP não mudam.

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
