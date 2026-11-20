================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python + Flask 3.0.0 (SQLite via Flask-SQLAlchemy 3.1.1)
Files:   12 analyzed | ~1155 lines of code

## Summary
CRITICAL: 8 | HIGH: 11 | MEDIUM: 28 | LOW: 36

## Findings

### [CRITICAL] Hardcoded credentials and secrets (AP-01)
File: app.py:13
Description: `app.config['SECRET_KEY'] = 'super-secret-key-123'` fixa a chave de assinatura no código-fonte; hoje nada a usa, mas qualquer token ou sessão assinado com ela seria forjável por quem lê o repositório.
Impact: Quem tem acesso ao código pode assinar tokens válidos e se passar por qualquer usuário assim que a chave for usada para autenticação.
Recommendation: P-01 — `SECRET_KEY` lido do ambiente em `src/config/settings.py`; se ausente, `secrets.token_hex(32)` gerado no boot; a chave passa a assinar os tokens de P-16.
Verification: `GREP "super-secret-key" .` → sem ocorrências; boot `python app.py` sem variáveis → sobe sem erro; um token assinado com itsdangerous usando 'super-secret-key-123' e payload {"uid":1} em `GET /tasks` → 401; um token emitido por `POST /login`, reaproveitado após reiniciar o servidor sem variáveis → 401.

### [CRITICAL] Hardcoded credentials and secrets (AP-01)
File: services/notification_service.py:7-10
Description: `NotificationService.__init__` grava `email_user = 'taskmanager@gmail.com'` e `email_password = 'senha123'` (credencial SMTP) como literais.
Impact: A senha da conta de e-mail fica exposta a quem lê o repositório e permite enviar e-mails em nome do sistema.
Recommendation: P-01 — `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` lidos do ambiente em `src/config/settings.py` e injetados em `src/services/notification_service.py`; sem eles, só a notificação falha fechada (registra no log e não envia).
Verification: `GREP "senha123|taskmanager@gmail" .` → sem ocorrências; boot sem variáveis, `POST /tasks` como admin com `user_id: 2` → 201 e o log registra a notificação como não enviada por SMTP não configurado, sem tentativa de conexão.

### [CRITICAL] Hardcoded credentials and secrets (AP-01)
File: seed.py:19, 26, 33
Description: `u1.set_password('1234')`, `u2.set_password('abcd')` e `u3.set_password('pass')` semeiam as contas admin, user e manager com senhas literais conhecidas.
Impact: Qualquer pessoa que leu o repositório entra como admin (`joao@email.com` / `1234`) em qualquer instalação semeada.
Recommendation: P-16 — senhas de `SEED_ADMIN_PASSWORD` / `SEED_USER_PASSWORD` (listadas em `.env.example`); quando ausentes, `seed.py` gera senhas aleatórias e as imprime uma única vez. No boot, `src/services/credential_service.py` substitui essas senhas padrão em bancos já existentes.
Verification: `GREP "'(1234|abcd|pass)'" .` → sem ocorrências; banco novo + `python seed.py` sem variáveis, `POST /login` com joao/1234, maria/abcd e pedro/pass → 401 cada; com as senhas impressas pelo seed → 200. Upgrade: banco criado pelo `seed.py` original e boot do app refatorado sem variáveis → as mesmas três combinações dão 401 e as senhas impressas no boot dão 200.

### [CRITICAL] God class / God module (AP-03)
File: routes/task_routes.py:1-299
Description: Num arquivo de 299 linhas, o módulo registra as 7 rotas de tasks, executa as queries (`Task.query.all()` :14, `User.query.get` :42, contagens :275-281), aplica regras (atraso :30-39, validações :92-144, taxa de conclusão :296) e monta as respostas à mão (:17-28).
Impact: Rotas, persistência e regras não podem ser testadas nem alteradas separadamente; qualquer mudança no domínio de tasks mexe no arquivo de rotas.
Recommendation: P-03 — dividir em `src/views/task_routes.py` (só HTTP), `src/controllers/task_controller.py` (caso de uso) e `src/models/task_model.py` (dados e regras da entidade).
Verification: routes/task_routes.py não existe mais; `grep -nE "db\.session|\.query\b|select\(" src/views/task_routes.py` → sem ocorrências; os 7 endpoints de tasks retornam o status e as chaves do baseline.

### [CRITICAL] God class / God module (AP-03)
File: routes/user_routes.py:1-211
Description: O módulo registra 7 rotas, consulta e grava usuários (:12, :67, :140-146), implementa a autenticação (`login` :185-211, emitindo o token falso) e serializa usuários e tasks à mão (:15-22, :162-169).
Impact: Autenticação, CRUD de usuários e serialização de tasks ficam acoplados ao Flask e entre si; não há como testar o login sem HTTP.
Recommendation: P-03 — `src/views/user_routes.py`, `src/controllers/user_controller.py` (cadastro, atualização, login) e `src/models/user_model.py`.
Verification: routes/user_routes.py não existe mais; `grep -nE "db\.session|\.query\b|select\(|check_password" src/views/user_routes.py` → sem ocorrências; os 7 endpoints de usuários retornam o status e as chaves do baseline.

### [CRITICAL] God class / God module (AP-03)
File: routes/report_routes.py:1-223
Description: Um único blueprint `report_bp` mistura dois domínios: relatórios (`summary_report` :12-101, `user_report` :103-155, com agregações) e o CRUD completo de categorias (:157-223), cada um com suas queries e respostas.
Impact: Mudanças em categorias e em relatórios colidem no mesmo arquivo; não há model nem controller de categoria, e as regras de relatório não podem ser reutilizadas.
Recommendation: P-03 — `src/views/report_routes.py` + `src/services/report_service.py` para relatórios; `src/views/category_routes.py` + `src/controllers/category_controller.py` para categorias.
Verification: routes/report_routes.py não existe mais; `grep -nE "db\.session|\.query\b|select\(" src/views/report_routes.py src/views/category_routes.py` → sem ocorrências; `grep -n "categories" src/views/report_routes.py` → sem ocorrências; os 6 endpoints retornam o status e as chaves do baseline.

### [CRITICAL] Plaintext or weak password storage (AP-05)
File: models/user.py:27-32
Description: `set_password` grava `hashlib.md5(pwd.encode()).hexdigest()` sem salt, e `check_password` compara o mesmo MD5; o seed (seed.py:19-33) grava as senhas dessa forma.
Impact: Quem obtém o banco recupera as senhas por tabela de MD5 em segundos; senhas iguais produzem hashes iguais.
Recommendation: P-04 — `werkzeug.security.generate_password_hash`/`check_password_hash` (scrypt) em `src/models/user_model.py`. No boot, hashes MD5 legados são envoltos em scrypt (`md5+scrypt:`) e convertidos para scrypt puro no próximo login. Senhas padrão conhecidas são substituídas (ver AP-01 seed.py).
Verification: banco novo semeado e `POST /users` de um usuário novo → `SELECT count(*) FROM users WHERE password NOT LIKE 'scrypt:%'` → 0; login com a senha certa → 200, com a errada → 401. Upgrade: banco do código original com um usuário extra criado por `POST /users` (senha `segredo1`) e boot do refatorado → `SELECT count(*) FROM users WHERE length(password) = 32` → 0; login desse usuário com `segredo1` → 200 e, depois, o hash dele começa com `scrypt:`.

### [CRITICAL] Sensitive data exposure (AP-06)
File: models/user.py:16-25
Description: `User.to_dict()` inclui `'password': self.password` (o hash MD5); é devolvido por `GET /users/<id>` (routes/user_routes.py:33), `POST /users` (:85), `PUT /users/<id>` (:129) e `POST /login` (:209).
Impact: Qualquer cliente lê o hash de qualquer usuário e, com MD5 sem salt, a senha em claro.
Recommendation: P-05 — retirar `password` de `to_dict()` em `src/models/user_model.py`.
Verification: as respostas de `GET /users/1` (admin), `POST /users` (anônimo), `PUT /users/2` (usuário A) e `POST /login` (admin) não têm a chave `password` em nenhum nível (`"password"` ausente do corpo); `GET /users` continua sem ela.

### [HIGH] Business logic in the controller / route (fat controller) (AP-07)
File: routes/task_routes.py:11-63, 85-154, 156-223, 273-299
Description: `get_tasks` (53 linhas) calcula `overdue` e busca nomes; `create_task` (70 linhas) e `update_task` (68 linhas) validam título, status, prioridade, datas e tags inline; `task_stats` agrega contagens, atraso e `completion_rate`.
Impact: As regras (atraso, validação, estatística) só existem dentro dos handlers HTTP, duplicadas entre eles e testáveis apenas por requisição.
Recommendation: P-06 — regras em `src/controllers/task_controller.py` e `src/models/task_model.py` (`is_overdue`); cada handler de `src/views/task_routes.py` delega ao controller.
Verification: `grep -nE "utcnow|now\(|due_date|completion_rate|round\(|len\(" src/views/task_routes.py` → sem ocorrências; nenhum handler em src/views/task_routes.py tem mais de 15 linhas; `GET /tasks`, `GET /tasks/<id>` e `GET /tasks/stats` (admin) retornam os mesmos valores de `overdue` e as mesmas contagens do baseline.

### [HIGH] Business logic in the controller / route (fat controller) (AP-07)
File: routes/user_routes.py:42-90, 92-132, 153-183, 185-211
Description: `create_user` e `update_user` validam e-mail, senha, role e unicidade inline; `get_user_tasks` recalcula o atraso; `login` faz a verificação de credenciais e a emissão do token no handler.
Impact: Regras de cadastro e autenticação ficam presas à camada HTTP, e cada correção precisa ser repetida em vários handlers.
Recommendation: P-06 — `src/controllers/user_controller.py` (create/update/login) e `src/controllers/validators.py`; views só traduzem HTTP.
Verification: `grep -nE "re\.match|set_password|check_password|utcnow|len\(" src/views/user_routes.py` → sem ocorrências; nenhum handler em src/views/user_routes.py tem mais de 15 linhas; `POST /users`, `PUT /users/<id>`, `GET /users/<id>/tasks` e `POST /login` retornam o status e as chaves do baseline.

### [HIGH] Business logic in the controller / route (fat controller) (AP-07)
File: routes/report_routes.py:12-101, 103-155
Description: `summary_report` (90 linhas) e `user_report` (53 linhas) agregam status, prioridades, atraso, atividade recente e produtividade dentro dos handlers.
Impact: A lógica de relatório não pode ser reutilizada nem testada sem HTTP e repete regras que já existem em outros lugares.
Recommendation: P-06 — `src/services/report_service.py`; `src/views/report_routes.py` chama o serviço em uma linha.
Verification: `grep -nE "utcnow|now\(|timedelta|count\(|round\(" src/views/report_routes.py` → sem ocorrências; `GET /reports/summary` e `GET /reports/user/1` (admin) retornam as chaves e as contagens do baseline.

### [HIGH] Tight coupling / no dependency injection (AP-08)
File: app.py:9-31
Description: Não existe `create_app()`: o `app` é criado em nível de módulo com configuração literal, CORS, blueprints e `db.create_all()` executados no import; `seed.py:2` faz `from app import app, db`, e as rotas importam o singleton `db` de `database.py:3`.
Impact: Importar o módulo já cria o banco; não é possível instanciar o app com outra configuração (testes, outro banco) nem injetar serviços.
Recommendation: P-07 — composition root `create_app(settings)` em `src/app.py`, que monta config, `db.init_app`, migrações, serviços, controllers e blueprints; `app.py` e `seed.py` chamam `create_app()`.
Verification: `grep -nE "Flask\(|create_all" app.py seed.py` → sem ocorrências; `python -c "from src.app import create_app; from src.config.settings import Settings; a=create_app(); b=create_app(type('T',(Settings,),{'SQLALCHEMY_DATABASE_URI':'sqlite://'})); assert a is not b"` → sai com código 0; `python app.py` responde `GET /health` → 200.

### [HIGH] Tight coupling / no dependency injection (AP-08)
File: services/notification_service.py:4-10
Description: `NotificationService` é definida, mas nunca instanciada nem chamada (nenhum import no projeto), e monta sozinha a própria configuração SMTP.
Impact: A notificação de atribuição de task nunca acontece, e o serviço não pode ser configurado nem substituído.
Recommendation: P-07 — instanciar em `src/app.py` com as configurações SMTP e injetar no `TaskController`, que chama `notify_task_assigned` ao criar ou reatribuir uma task.
Verification: `grep -rn "NotificationService(" src app.py seed.py` → exatamente uma ocorrência, em src/app.py; `POST /tasks` (admin, `user_id: 2`) → 201 e o log mostra a chamada de notificação para o usuário 2.

### [HIGH] Mutable global state (AP-09)
File: services/notification_service.py:6, 31-36, 43-48
Description: `self.notifications = []` acumula um dict por notificação em `notify_task_assigned` e é lido apenas por `get_notifications`, que nenhuma rota chama.
Impact: Com o serviço instanciado uma vez no processo, a lista cresce sem limite, some no restart e diverge entre workers.
Recommendation: P-08 — ninguém lê o estado: remover a lista e `get_notifications`, mantendo o envio e uma linha de log.
Verification: `GREP "self\.[a-z_]+ *= *(\[\]|\{\}|set\(\)|dict\(\)|list\(\))|^\s*global " .` → sem ocorrências; `GREP "get_notifications|\.notifications\b" .` → sem ocorrências.

### [HIGH] Non-atomic multi-step writes and orphaned data (AP-10)
File: routes/report_routes.py:211-223
Description: `delete_category` apaga a categoria e deixa as tasks com `category_id` apontando para um id inexistente (o SQLite não aplica a FK).
Impact: Ficam tasks órfãs com `category_id` inválido, e um id reaproveitado depois associa essas tasks à categoria errada.
Recommendation: P-11 — em `src/controllers/category_controller.py`, numa única transação, `UPDATE tasks SET category_id = NULL` para a categoria e depois o delete; no boot, a mesma limpeza idempotente para órfãos já existentes.
Verification: admin `DELETE /categories/1` (tem tasks) → 200; `SELECT count(*) FROM tasks WHERE category_id IS NOT NULL AND category_id NOT IN (SELECT id FROM categories)` → 0; admin `DELETE /users/3` → `SELECT count(*) FROM tasks WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT id FROM users)` → 0. Upgrade: banco do código original no qual a categoria 1 foi apagada pelo endpoint original e boot do refatorado → a primeira query → 0.

### [HIGH] Missing authentication / authorization (AP-11)
File: routes/task_routes.py:11, 65, 85, 105, 131, 156, 186-191, 225, 240, 263-264, 273
Description: As 7 rotas de tasks são anônimas; o dono vem do corpo (`user_id = data.get('user_id')` :105 na criação, :186-191 na atualização), e qualquer cliente lê, altera, reatribui ou apaga a task de qualquer usuário.
Impact: Qualquer pessoa na rede lê, altera, reatribui e apaga tasks alheias e cria tasks em nome de outro usuário.
Recommendation: P-16 — `src/middlewares/auth.py` (`require_auth`), com o dono vindo do token em `src/controllers/task_controller.py`: um não-admin só vê e altera as próprias tasks, e o admin acessa tudo.
Verification: anônimo `GET /tasks` e `POST /tasks` → 401; usuário A: `GET /tasks/3` → 403, `PUT /tasks/3` → 403, `DELETE /tasks/3` → 403, `POST /tasks` com `user_id: 3` → 403, `PUT /tasks/2` com `user_id: 3` → 403, `GET /tasks/search?user_id=3` → 403, `GET /tasks` → só tasks com `user_id` 2; usuário A em `GET /tasks/2` e `PUT /tasks/2` → 200, `POST /tasks` sem `user_id` → 201 com `user_id` 2, `DELETE /tasks/8` → 200; admin `POST /tasks` com `user_id: 3` → 201.

### [HIGH] Missing authentication / authorization (AP-11)
File: routes/user_routes.py:10, 27, 42, 52, 71-78, 92, 119-125, 134, 153, 207-211
Description: Listar, ler, alterar e apagar usuários é anônimo; `role = data.get('role', 'user')` permite se cadastrar como admin; `PUT` altera role, senha e `active` de qualquer um; o login devolve `'fake-jwt-token-' + str(user.id)`, um token previsível que nada verifica.
Impact: Qualquer pessoa vira admin, troca a senha de outro usuário, desativa ou apaga contas e enumera todos os usuários.
Recommendation: P-16 — token assinado (itsdangerous) emitido no login; `GET /users` e `DELETE /users/<id>` só para admin; `GET`/`PUT /users/<id>` e `/users/<id>/tasks` para o próprio usuário ou admin; role e `active` só alteráveis por admin; cadastro anônimo sempre com role `user`.
Verification: anônimo `GET /users` → 401; header `Authorization: Bearer fake-jwt-token-1` em `GET /users` → 401; usuário A: `GET /users` → 403, `GET /users/3` → 403, `PUT /users/3` → 403, `DELETE /users/3` → 403, `GET /users/3/tasks` → 403, `PUT /users/2` com `{"role":"admin"}` → 403, `PUT /users/2` com `{"active":false}` → 403; anônimo `POST /users` com `"role":"admin"` → 201 com `role` = `user`; usuário A em `GET /users/2`, `PUT /users/2` com `{"name":"Maria S."}` e `GET /users/2/tasks` → 200; admin em todos → status do baseline.

### [HIGH] Missing authentication / authorization (AP-11)
File: routes/report_routes.py:12, 103, 157, 167, 190, 211
Description: Relatórios globais e por usuário e o CRUD de categorias são anônimos; `user_report` expõe nome e e-mail de qualquer usuário.
Impact: Qualquer pessoa lê estatísticas e e-mails de todos os usuários e cria, altera ou apaga categorias compartilhadas.
Recommendation: P-16 — `/reports/summary` e escrita em categorias só para admin; `/reports/user/<id>` para o próprio usuário ou admin; `GET /categories` para autenticados.
Verification: anônimo `GET /reports/summary` e `GET /categories` → 401; usuário A: `GET /reports/summary` → 403, `GET /reports/user/3` → 403, `POST /categories` → 403, `PUT /categories/1` → 403, `DELETE /categories/1` → 403; usuário A `GET /reports/user/2` e `GET /categories` → 200; admin em todos → status do baseline.

### [HIGH] Debug mode and unsafe defaults in the entry point (AP-12)
File: app.py:15, 34
Description: `CORS(app)` libera qualquer origem e `app.run(debug=True, host='0.0.0.0', port=5000)` expõe o debugger do Werkzeug em todas as interfaces.
Impact: Qualquer máquina na rede alcança o debugger interativo (execução remota de código), e qualquer site consegue chamar a API pelo navegador da vítima.
Recommendation: P-01 — `DEBUG` (padrão off), `HOST` (padrão `127.0.0.1`), `PORT` e `CORS_ORIGINS` (padrão lista vazia) em `src/config/settings.py`, usados em `app.py`/`src/app.py`.
Verification: boot sem variáveis → `ss -ltnp | grep 5000` mostra `127.0.0.1:5000` e não `0.0.0.0:5000`; o log de boot não contém "Debugger is active"; `curl -si -X OPTIONS -H 'Origin: http://evil.example' -H 'Access-Control-Request-Method: GET' localhost:5000/tasks` → sem `Access-Control-Allow-Origin`.

### [MEDIUM] N+1 queries (AP-13)
File: routes/task_routes.py:41-57, 275-281
Description: `get_tasks` faz `User.query.get(t.user_id)` e `Category.query.get(t.category_id)` para cada task; `task_stats` faz 5 `count()` separados e ainda carrega todas as tasks.
Impact: O número de queries de `GET /tasks` cresce com 2 por task; a listagem degrada linearmente com o volume.
Recommendation: P-09 — `joinedload(Task.user)`/`joinedload(Task.category)` em `src/models/task_model.py` e `GROUP BY status` para as contagens.
Verification: com o evento `before_cursor_execute` contando statements, admin `GET /tasks` com 10 tasks e com 20 tasks → mesma contagem; `GET /tasks/stats` com 10 e com 20 tasks → mesma contagem.

### [MEDIUM] N+1 queries (AP-13)
File: routes/user_routes.py:14, 22
Description: `get_users` acessa `len(u.tasks)` (relação lazy) para cada usuário, ou seja, uma query por usuário.
Impact: A listagem de usuários faz 1 + N queries.
Recommendation: P-09 — contagem com `GROUP BY user_id` em `src/models/user_model.py`.
Verification: contando statements, admin `GET /users` com 3 e com 6 usuários → mesma contagem; o `task_count` de cada usuário igual ao baseline.

### [MEDIUM] N+1 queries (AP-13)
File: routes/report_routes.py:15-28, 53-61, 161-163
Description: `summary_report` faz 12 `count()` separados e um `Task.query.filter_by(user_id=u.id).all()` por usuário; `get_categories` faz um `count()` por categoria.
Impact: O relatório e a listagem de categorias fazem queries proporcionais a usuários e categorias.
Recommendation: P-09 — `GROUP BY status`, `GROUP BY priority`, `GROUP BY user_id, status` e `GROUP BY category_id` em `src/services/report_service.py` e `src/models/category_model.py`.
Verification: contando statements, admin `GET /reports/summary` com 3 e com 6 usuários (e 10 e 20 tasks) → mesma contagem; `GET /categories` com 4 e com 8 categorias → mesma contagem.

### [MEDIUM] Duplicated logic (AP-14)
File: routes/task_routes.py:17-28, 30-39, 71-80, 92-144, 110, 166-213, 177, 283-287, 296
Description: Serializador de task montado à mão (:17-28) em vez de `Task.to_dict()`; regra de atraso copiada três vezes (:30-39, :71-80, :283-287), ignorando `Task.is_overdue`; validação de criação (:92-144) reescrita na atualização (:166-213); lista de status literal em :110 e :177; taxa de conclusão em :296.
Impact: Corrigir uma regra (o atraso, por exemplo) exige alterar várias cópias; elas já divergem (a mensagem de data difere entre :138 e :205).
Recommendation: P-12 — `Task.to_dict(include_overdue=...)` e `Task.is_overdue()` em `src/models/task_model.py`; `validate_task(data, partial)` em `src/controllers/validators.py`; constantes em `src/constants.py`.
Verification: `GREP "'pending', 'in_progress'" .` → exatamente uma ocorrência (src/constants.py); `GREP "due_date < " .` → exatamente uma ocorrência (src/models/task_model.py); `grep -nE "\['(title|due_date)'\] *=" src/views/task_routes.py src/controllers/task_controller.py` → sem ocorrências; `overdue` de `GET /tasks`, `GET /tasks/<id>` e `GET /users/<id>/tasks` igual ao baseline.

### [MEDIUM] Duplicated logic (AP-14)
File: routes/user_routes.py:15-22, 61, 64, 71, 106, 115, 120, 162-180
Description: Dict de usuário montado à mão em `get_users`; regex de e-mail (:61, :106), tamanho mínimo de senha (:64, :115) e lista de roles (:71, :120) duplicados entre create e update; serializador de task e regra de atraso copiados em `get_user_tasks`.
Impact: Uma regra de validação alterada em create continua antiga em update, e a serialização diverge do model.
Recommendation: P-12 — `validate_user(data, partial)` em `src/controllers/validators.py`, `User.to_dict()` como serializador único, `Task.to_dict(fields=...)` para o formato reduzido.
Verification: `GREP "a-zA-Z0-9\+_\.-\]\+@" .` → exatamente uma ocorrência (src/controllers/validators.py); `GREP "'user', 'admin', 'manager'" .` → exatamente uma ocorrência (src/constants.py); `POST /users` e `PUT /users/2` com e-mail `x` → 400 "Email inválido" nos dois.

### [MEDIUM] Duplicated logic (AP-14)
File: routes/report_routes.py:7, 33-36, 67, 132-135, 151
Description: A regra de atraso é reescrita duas vezes (:33-36, :132-135), e `round((x / total) * 100, 2) if total > 0 else 0` aparece em :67 e :151, embora `calculate_percentage` seja importado em :7 e nunca usado.
Impact: O relatório pode divergir de `GET /tasks` sobre o que é uma task atrasada, e o cálculo de percentual tem três cópias.
Recommendation: P-12 — `Task.is_overdue()`/expressão SQL equivalente no model e uma única função `completion_rate` em `src/services/report_service.py`.
Verification: `GREP "\* 100" .` → exatamente uma ocorrência (src/services/report_service.py); `GREP "due_date < " .` → exatamente uma ocorrência; `overdue.count` de `/reports/summary` igual ao `overdue` de `/tasks/stats` (admin).

### [MEDIUM] Duplicated logic (AP-14)
File: models/task.py:38-48
Description: `validate_status` repete a lista literal de status (:39) e `validate_priority` repete os limites 1..5 já copiados nas rotas e em helpers; nenhum dos dois é chamado.
Impact: Uma quarta cópia das mesmas regras, que ninguém usa, diverge silenciosamente das que valem.
Recommendation: P-12 — remover os métodos; as regras ficam só em `src/controllers/validators.py` com as constantes de `src/constants.py`.
Verification: `grep -snE "validate_status|validate_priority|'pending', 'in_progress'" models/task.py src/models/task_model.py` → sem ocorrências.

### [MEDIUM] Duplicated logic (AP-14)
File: utils/helpers.py:21, 57-108, 75, 110-116
Description: `process_task_data` reimplementa a validação das rotas de task; a lista de status aparece em :75 e :110; o regex de e-mail em :21 repete o das rotas; as constantes `VALID_STATUSES`, `VALID_ROLES` e `MIN_*` nunca são usadas.
Impact: Uma terceira implementação das regras, ignorada pelas rotas, dá a falsa impressão de uma fonte única.
Recommendation: P-12 — apagar `utils/helpers.py`; validação única em `src/controllers/validators.py` e constantes em `src/constants.py`.
Verification: utils/helpers.py não existe mais; `GREP "process_task_data|VALID_STATUSES|VALID_ROLES" .` → sem ocorrências.

### [MEDIUM] Missing or inconsistent input validation (AP-15)
File: routes/task_routes.py:87, 96-100, 102, 113, 140-144, 162, 166-171, 173, 182, 186-198, 209-213, 261, 264
Description: `len(title)` e `priority < 1` sem checar o tipo (título numérico ou prioridade `"3"` → TypeError 500; `NaN` e `true` passam); o update faz `len(data['title'])` com `None`; tags com itens não-string quebram o `join`; `int(priority)`/`int(user_id)` na busca dão ValueError 500; corpo não-JSON → 415 HTML de `get_json()`.
Impact: Entradas inválidas comuns derrubam a requisição com 500 ou gravam valores inválidos (prioridade NaN/booleana) no banco.
Recommendation: P-12 — `validate_task` em `src/controllers/validators.py` (tipos, `math.isfinite`, bool rejeitado, faixas) usado por create e update; busca valida os inteiros; `get_json(silent=True)`.
Verification: como admin, cada um → 400 com `error`: `POST /tasks` com `title: 123`; com `priority: "3"`; com `priority: NaN`; com `priority: true`; com `tags: [1,2]`; `PUT /tasks/1` com `title: null`, com `priority: "x"` e com `priority: NaN`; `GET /tasks/search?priority=abc` e `?user_id=abc`; `POST /tasks` com corpo `texto` e Content-Type `text/plain` → 400 JSON "Dados inválidos".

### [MEDIUM] Missing or inconsistent input validation (AP-15)
File: routes/user_routes.py:61, 64, 67-69, 102-103, 109-111, 115, 124-125, 191-201
Description: `re.match` e `len()` sem checar o tipo (e-mail ou senha numéricos → 500); unicidade por `SELECT` antes do `INSERT`, sensível a maiúsculas (models/user.py:10 só garante igualdade exata), e envios concorrentes caem em IntegrityError 500; `name` no update aceita `null`/`""`; `active` aceita qualquer tipo; `login` com senha não-string → 500.
Impact: Duas contas com o mesmo e-mail em caixa diferente, 500 em entradas triviais e nomes vazios gravados.
Recommendation: P-12 — `validate_user` em `src/controllers/validators.py`; índice único `lower(email)` criado de forma idempotente no boot (`CREATE UNIQUE INDEX IF NOT EXISTS`) com IntegrityError mapeado para 409.
Verification: `POST /users` com `email: 123` → 400; com `password: 1234` (número) → 400; `PUT /users/2` (usuário A) com `name: ""` → 400; admin `PUT /users/2` com `active: "sim"` → 400; `POST /login` com `password: 123` → 400; `POST /users` com `JOAO@EMAIL.COM` → 409; 20 `POST /users` concorrentes com `novo@x.com`/`NOVO@x.com` alternados → exatamente 1 × 201 e 19 × 409, e `SELECT count(*) FROM users WHERE lower(email)='novo@x.com'` → 1. Upgrade: no banco criado pelo código original, as mesmas duas checagens de unicidade → mesmos resultados.

### [MEDIUM] Missing or inconsistent input validation (AP-15)
File: routes/report_routes.py:173-180, 196-202
Description: `update_category` faz `'name' in data` sem checar se o corpo existe (TypeError 500 com corpo vazio) e aceita `name` `null`/`""`; `create_category` e `update_category` não validam tipo nem formato de `color` (`is_valid_color` existe e não é usado).
Impact: Um PUT sem corpo dá 500; cores inválidas e nomes vazios ou nulos são gravados (nulo → 500 por NOT NULL).
Recommendation: P-12 — `validate_category(data, partial)` em `src/controllers/validators.py` (nome string não vazia, cor `#RRGGBB`).
Verification: como admin, cada um → 400 com `error`: `PUT /categories/1` sem corpo; `PUT /categories/1` com `name: null`; `PUT /categories/1` com `color: "red"`; `POST /categories` com `color: "red"`; `POST /categories` com `name: 5`.

### [MEDIUM] Scattered or leaky error handling (AP-16)
File: routes/task_routes.py:13, 62-63, 137, 151-154, 204, 221-223, 236-238
Description: `get_tasks` inteiro está dentro de `try`/`except:` puro; `except:` puros na conversão de datas; `except Exception as e` com `print(str(e))` em create, update e delete.
Impact: Erros reais são engolidos sem log, e o mesmo tratamento é repetido em cada handler.
Recommendation: P-10 — `src/middlewares/error_handler.py` com `AppError`/`ValidationError`/`NotFoundError`/`ForbiddenError`/`UnauthorizedError`; handlers sem `try/except`.
Verification: `grep -snE "except( Exception)?( as [a-z]+)?:" routes/task_routes.py src/views/task_routes.py src/controllers/task_controller.py` → sem ocorrências; com `TaskController.list` forçado a lançar `RuntimeError('detalhe-interno')` via test client, `GET /tasks` (admin) → 500 `{"error": "Erro interno"}` sem "detalhe-interno" no corpo e com o traceback no log.

### [MEDIUM] Scattered or leaky error handling (AP-16)
File: routes/user_routes.py:87-90, 130-132, 149-151
Description: `except Exception as e` com `print(f"ERRO: {str(e)}")` em `create_user` e `except:` puros em update e delete devolvem 500 genérico e escondem a causa (por exemplo, uma violação de unicidade vira 500).
Impact: Conflitos esperados viram 500 e a causa não chega a nenhum log estruturado.
Recommendation: P-10 — handler central; o controller converte `IntegrityError` em `ConflictError` (409).
Verification: `grep -snE "except( Exception)?( as [a-z]+)?:" routes/user_routes.py src/views/user_routes.py src/controllers/user_controller.py` → sem ocorrências; 20 `POST /users` concorrentes com o mesmo e-mail → nenhum 500.

### [MEDIUM] Scattered or leaky error handling (AP-16)
File: routes/report_routes.py:186-188, 207-209, 221-223
Description: `except:` puros em create, update e delete de categoria fazem rollback e devolvem 500 sem registrar a causa.
Impact: Falhas de banco ficam invisíveis para quem opera o sistema.
Recommendation: P-10 — handler central; `src/controllers/category_controller.py` sem `try/except`.
Verification: `grep -snE "except( Exception)?( as [a-z]+)?:" routes/report_routes.py src/views/category_routes.py src/views/report_routes.py src/controllers/category_controller.py src/services/report_service.py` → sem ocorrências.

### [MEDIUM] Scattered or leaky error handling (AP-16)
File: app.py:9-20
Description: Nenhum `errorhandler` é registrado: rota inexistente (404), método errado (405), corpo não-JSON (415) e exceções não tratadas devolvem páginas HTML do Flask numa API JSON.
Impact: Os clientes recebem HTML em vez de `{"error": ...}`, e os formatos de erro variam entre rotas.
Recommendation: P-10 — `register_error_handlers(app)` em `src/middlewares/error_handler.py`, incluindo `HTTPException`, chamado por `create_app`.
Verification: `GET /nao-existe` → 404 com JSON `{"error": ...}`; `PATCH /tasks` → 405 com JSON `{"error": ...}`; uma exceção forçada (ver o primeiro AP-16) → 500 JSON `{"error": "Erro interno"}`.

### [MEDIUM] Scattered or leaky error handling (AP-16)
File: utils/helpers.py:46, 49, 88
Description: `parse_date` e `process_task_data` usam `except:` puros, que capturam até `KeyboardInterrupt`/`SystemExit`.
Impact: Erros de programação viram "Data inválida"/"Prioridade inválida" silenciosamente.
Recommendation: P-10 — o arquivo é removido (AP-21); a validação nova captura só `ValueError`.
Verification: utils/helpers.py não existe mais; `GREP "except:" .` → sem ocorrências.

### [MEDIUM] Scattered or leaky error handling (AP-16)
File: services/notification_service.py:13, 23-25
Description: `send_email` envolve tudo em `except Exception as e` e faz `print(f"Erro ao enviar email: {str(e)}")`.
Impact: Qualquer bug do serviço é engolido e só aparece no stdout.
Recommendation: P-10 — capturar apenas `smtplib.SMTPException`/`OSError` e registrar com `logger.exception`.
Verification: `grep -snE "except( Exception)?( as [a-z]+)?:" services/notification_service.py src/services/notification_service.py` → sem ocorrências.

### [MEDIUM] Deprecated APIs (AP-17)
File: models/category.py:11
Description: `default=datetime.utcnow`, depreciado no Python 3.12+.
Impact: Gera DeprecationWarning e quebra numa versão futura do Python.
Recommendation: P-13 — `utcnow()` = `datetime.now(timezone.utc).replace(tzinfo=None)` em `src/models/base.py`, usado em `src/models/category_model.py`.
Verification: `grep -snE "datetime\.utcnow|\.query\.get\(" models/category.py src/models/category_model.py` → sem ocorrências; todos os endpoints via test client com `warnings.simplefilter('always')` → zero DeprecationWarning/LegacyAPIWarning cujo arquivo esteja no projeto.

### [MEDIUM] Deprecated APIs (AP-17)
File: models/task.py:15, 16, 52
Description: `default=datetime.utcnow`, `onupdate=datetime.utcnow` e `datetime.utcnow()` em `is_overdue`.
Impact: DeprecationWarning no Python 3.12+ e remoção futura.
Recommendation: P-13 — `utcnow()` de `src/models/base.py` em `src/models/task_model.py`.
Verification: `grep -snE "datetime\.utcnow|\.query\.get\(" models/task.py src/models/task_model.py` → sem ocorrências; mesma checagem de warnings do primeiro AP-17.

### [MEDIUM] Deprecated APIs (AP-17)
File: models/user.py:14
Description: `default=datetime.utcnow`.
Impact: DeprecationWarning no Python 3.12+.
Recommendation: P-13 — `utcnow()` em `src/models/user_model.py`.
Verification: `grep -snE "datetime\.utcnow|\.query\.get\(" models/user.py src/models/user_model.py` → sem ocorrências.

### [MEDIUM] Deprecated APIs (AP-17)
File: routes/report_routes.py:35, 42, 45, 71, 105, 133, 192, 213
Description: `datetime.utcnow()` (:35, 42, 45, 71, 133) e `Model.query.get(id)` (:105, 192, 213), legado no SQLAlchemy 2.0.
Impact: DeprecationWarning e LegacyAPIWarning; `Query.get` vai ser removido.
Recommendation: P-13 — `utcnow()` e `db.session.get(Model, id)` em `src/services/report_service.py` e `src/controllers/category_controller.py`.
Verification: `grep -snE "datetime\.utcnow|\.query\.get\(" routes/report_routes.py src/services/report_service.py src/controllers/category_controller.py src/views/report_routes.py src/views/category_routes.py` → sem ocorrências.

### [MEDIUM] Deprecated APIs (AP-17)
File: routes/task_routes.py:31, 42, 51, 67, 72, 117, 122, 158, 188, 195, 215, 227, 285
Description: `datetime.utcnow()` (:31, 72, 215, 285) e `Task/User/Category.query.get(...)` (:42, 51, 67, 117, 122, 158, 188, 195, 227).
Impact: DeprecationWarning e LegacyAPIWarning.
Recommendation: P-13 — `db.session.get` e `utcnow()` em `src/controllers/task_controller.py`/`src/models/task_model.py`.
Verification: `grep -snE "datetime\.utcnow|\.query\.get\(" routes/task_routes.py src/views/task_routes.py src/controllers/task_controller.py` → sem ocorrências.

### [MEDIUM] Deprecated APIs (AP-17)
File: routes/user_routes.py:29, 94, 136, 155, 172
Description: `User.query.get(user_id)` (:29, 94, 136, 155) e `datetime.utcnow()` (:172).
Impact: LegacyAPIWarning e DeprecationWarning.
Recommendation: P-13 — `db.session.get(User, id)` em `src/models/user_model.py`.
Verification: `grep -snE "datetime\.utcnow|\.query\.get\(" routes/user_routes.py src/views/user_routes.py src/controllers/user_controller.py` → sem ocorrências.

### [MEDIUM] Deprecated APIs (AP-17)
File: seed.py:66, 67, 69, 70, 74
Description: `datetime.utcnow()` para calcular os `due_date` do seed.
Impact: DeprecationWarning ao rodar o seed no Python 3.12+.
Recommendation: P-13 — `utcnow()` de `src/models/base.py`.
Verification: `grep -nE "datetime\.utcnow" seed.py` → sem ocorrências; `python -W error::DeprecationWarning seed.py` → sai com código 0.

### [MEDIUM] Deprecated APIs (AP-17)
File: services/notification_service.py:35
Description: `datetime.utcnow()` no registro da notificação.
Impact: DeprecationWarning.
Recommendation: P-13 — o registro em memória é removido (AP-09); nenhuma chamada a `utcnow` depreciada.
Verification: `grep -snE "datetime\.utcnow" services/notification_service.py src/services/notification_service.py` → sem ocorrências.

### [MEDIUM] Deprecated APIs (AP-17)
File: utils/helpers.py:38
Description: `datetime.utcnow()` em `log_action`.
Impact: DeprecationWarning.
Recommendation: P-13 — o arquivo é removido (função nunca usada, AP-21).
Verification: `GREP "datetime\.utcnow" .` → sem ocorrências.

### [MEDIUM] Configuration in code instead of a config module (AP-18)
File: app.py:11, 34
Description: `'sqlite:///tasks.db'` e `port=5000` escritos como literais no ponto de entrada.
Impact: Não dá para apontar outro banco ou outra porta por ambiente sem editar o código.
Recommendation: P-01 — `DATABASE_URL` e `PORT` em `src/config/settings.py`, com esses valores como padrão.
Verification: `GREP "tasks\.db|port=5000|5000" . | grep -v src/config/settings.py` → sem ocorrências; `grep -nE "os\.environ" src/config/settings.py` lista `DATABASE_URL` e `PORT`.

### [MEDIUM] Configuration in code instead of a config module (AP-18)
File: services/notification_service.py:7-8
Description: `email_host = 'smtp.gmail.com'` e `email_port = 587` como literais dentro do serviço.
Impact: O servidor SMTP não pode ser trocado por ambiente.
Recommendation: P-01 — `SMTP_HOST`/`SMTP_PORT` em `src/config/settings.py`, injetados no serviço.
Verification: `GREP "smtp\.gmail|587" . | grep -v src/config/settings.py` → sem ocorrências.

### [LOW] Magic numbers and strings (AP-19)
File: routes/task_routes.py:32, 73, 96, 99, 103, 104, 110, 113, 167, 169, 177, 182, 276-279, 286
Description: Limites de título `3`/`200`, prioridade `1`/`5`/`3`, status `'pending'`, `'done'`, `'cancelled'` comparados inline.
Impact: Mudar um limite exige caçar literais espalhados.
Recommendation: P-14 — constantes em `src/constants.py`.
Verification: `grep -snE "== '(done|pending|in_progress|cancelled|admin)'|!= '(done|cancelled)'|< 3\b|> 200\b|< 1 or|status='(pending|in_progress|done|cancelled)'|'pending'\)" routes/task_routes.py src/views/task_routes.py src/controllers/task_controller.py` → sem ocorrências.

### [LOW] Magic numbers and strings (AP-19)
File: routes/user_routes.py:52, 64, 71, 115, 120, 173
Description: Role padrão `'user'`, senha mínima `4`, lista de roles e status inline.
Impact: Regras de cadastro espalhadas como literais.
Recommendation: P-14 — `ROLE_USER`, `MIN_PASSWORD_LENGTH`, `USER_ROLES` em `src/constants.py`.
Verification: `grep -snE "'(user|admin)'\)|< 4\b|'user', 'admin'|!= '(done|cancelled)'" routes/user_routes.py src/views/user_routes.py src/controllers/user_controller.py` → sem ocorrências.

### [LOW] Magic numbers and strings (AP-19)
File: routes/report_routes.py:19-28, 36, 45, 49, 60, 120-129, 134, 180
Description: Prioridades `1`..`5` mapeadas para nomes inline, janela `days=7`, `priority <= 2` como "alta", status e `'#000000'` literais.
Impact: O significado das faixas de prioridade e da janela de atividade fica implícito e duplicado.
Recommendation: P-14 — `PRIORITY_LABELS`, `RECENT_ACTIVITY_DAYS`, `HIGH_PRIORITY_MAX`, `DEFAULT_COLOR` em `src/constants.py`.
Verification: `grep -snE "days=7|<= 2\b|'#000000'|priority=[1-5]\b|== '(done|pending|in_progress|cancelled)'|status='(pending|in_progress|done|cancelled)'" routes/report_routes.py src/services/report_service.py src/controllers/category_controller.py` → sem ocorrências.

### [LOW] Magic numbers and strings (AP-19)
File: models/task.py:11, 12, 39, 46, 53
Description: `default='pending'`, `default=3`, lista de status, faixa `1..5` e status finais inline.
Impact: Os padrões do model divergem facilmente das validações.
Recommendation: P-14 — constantes de `src/constants.py` em `src/models/task_model.py`.
Verification: `grep -snE "default='pending'|default=3\b|>= 1 and|<= 5\b|!= '(done|cancelled)'" models/task.py src/models/task_model.py` → sem ocorrências.

### [LOW] Magic numbers and strings (AP-19)
File: models/user.py:12, 35
Description: `default='user'` e `self.role == 'admin'` literais.
Impact: Os nomes de role ficam repetidos no código.
Recommendation: P-14 — `ROLE_USER`/`ROLE_ADMIN`.
Verification: `grep -snE "default='user'|== 'admin'" models/user.py src/models/user_model.py` → sem ocorrências.

### [LOW] Magic numbers and strings (AP-19)
File: models/category.py:10
Description: `default='#000000'` literal (repetido em routes/report_routes.py:180 e utils/helpers.py:116).
Impact: A cor padrão tem três fontes.
Recommendation: P-14 — `DEFAULT_COLOR` em `src/constants.py`.
Verification: `GREP "'#000000'" . | grep -v src/constants.py` → sem ocorrências.

### [LOW] Magic numbers and strings (AP-19)
File: utils/helpers.py:64, 75, 84
Description: `len(title) >= 3 and len(title) <= 200`, lista de status e `p >= 1 and p <= 5` inline, embora o mesmo arquivo defina `MIN_TITLE_LENGTH` e companhia em :110-116.
Impact: As constantes declaradas no próprio arquivo são ignoradas.
Recommendation: P-14 — o arquivo é removido; os limites vivem em `src/constants.py`.
Verification: utils/helpers.py não existe mais; `GREP ">= 1 and|<= 5\b|>= 3 and" . | grep -v src/constants.py` → sem ocorrências.

### [LOW] Poor naming (AP-20)
File: routes/task_routes.py:16, 51, 122, 195, 268, 283
Description: `for t in tasks`, `cat = Category.query.get(...)` como nomes de valores de domínio.
Impact: Leitura mais difícil em handlers longos.
Recommendation: P-14 — `task`, `category`.
Verification: `grep -snE "\bfor (u|t|c|cat|td|n) in\b|^\s*(cat|t|c|u|p|d|s) = " routes/task_routes.py src/views/task_routes.py src/controllers/task_controller.py` → sem ocorrências.

### [LOW] Poor naming (AP-20)
File: routes/user_routes.py:14, 37, 141, 161
Description: `for u in users`, `for t in tasks`.
Impact: Nomes de uma letra para entidades.
Recommendation: P-14 — `user`, `task`.
Verification: `grep -snE "\bfor (u|t|c|cat|td|n) in\b|^\s*(cat|t|c|u|p|d|s) = " routes/user_routes.py src/views/user_routes.py src/controllers/user_controller.py` → sem ocorrências.

### [LOW] Poor naming (AP-20)
File: routes/report_routes.py:24-28, 33, 55, 59, 119, 161, 192, 213
Description: `p1`..`p5` para contagens por prioridade, `t`, `u`, `c`, `cat`.
Impact: `p1` não diz que é a contagem de prioridade crítica.
Recommendation: P-14 — `by_priority[...]`, `task`, `user`, `category`.
Verification: `grep -snE "\bfor (u|t|c|cat|td|n) in\b|^\s*(cat|t|c|u|p[0-9]?|d|s) = " routes/report_routes.py src/services/report_service.py src/controllers/category_controller.py src/views/report_routes.py src/views/category_routes.py` → sem ocorrências.

### [LOW] Poor naming (AP-20)
File: models/task.py:45-46
Description: `validate_priority(self, p)`.
Impact: Parâmetro de uma letra.
Recommendation: P-14 — o método é removido (AP-21); onde existir, `priority`.
Verification: `grep -snE "def [a-z_]+\((self, )?(p|s|pwd)\)" models/task.py src/models/task_model.py` → sem ocorrências.

### [LOW] Poor naming (AP-20)
File: models/category.py:14
Description: `d = {...}` em `to_dict`.
Impact: Nome sem significado.
Recommendation: P-14 — retornar o dict diretamente.
Verification: `grep -snE "^\s*d = " models/category.py src/models/category_model.py` → sem ocorrências.

### [LOW] Poor naming (AP-20)
File: models/user.py:27, 31
Description: `set_password(self, pwd)` e `check_password(self, pwd)`.
Impact: Abreviação em API pública do model.
Recommendation: P-14 — `raw_password`.
Verification: `grep -snE "def [a-z_]+\((self, )?(p|s|pwd)\)" models/user.py src/models/user_model.py` → sem ocorrências.

### [LOW] Poor naming (AP-20)
File: seed.py:16, 23, 30, 39, 45, 51, 57, 78, 79
Description: `u1`..`u3`, `c1`..`c4`, `td`, `t`.
Impact: Não dá para saber qual usuário ou categoria cada variável é.
Recommendation: P-14 — `admin`, `maria`, `pedro`, `backend`, `frontend`, ..., `task_data`, `task`.
Verification: `grep -nE "\bfor (u|t|c|cat|td|n) in\b|^\s*(u[0-9]|c[0-9]|td|t|c|u) = " seed.py` → sem ocorrências.

### [LOW] Poor naming (AP-20)
File: utils/helpers.py:25, 83
Description: `sanitize_string(s)` e `p = int(...)`.
Impact: Nomes de uma letra.
Recommendation: P-14 — o arquivo é removido (AP-21).
Verification: utils/helpers.py não existe mais; `grep -rnE "def [a-z_]+\((self, )?(p|s|pwd)\)" src` → sem ocorrências.

### [LOW] Poor naming (AP-20)
File: services/notification_service.py:45
Description: `for n in self.notifications`.
Impact: Nome de uma letra.
Recommendation: P-14 — o laço é removido com `get_notifications` (AP-09).
Verification: `grep -snE "\bfor (u|t|c|n) in\b" services/notification_service.py src/services/notification_service.py` → sem ocorrências.

### [LOW] Unused imports and dead code (AP-21)
File: app.py:7
Description: `import os, sys, json, datetime`: `os`, `sys` e `json` nunca são usados.
Impact: Ruído e dependências aparentes falsas.
Recommendation: remover.
Verification: `grep -nE "^import .*\b(sys|json)\b" app.py src/app.py` → sem ocorrências; `grep -nE "^import os" app.py` → sem ocorrências.

### [LOW] Unused imports and dead code (AP-21)
File: routes/task_routes.py:7
Description: `import json, os, sys, time`: nenhum é usado.
Impact: Imports mortos.
Recommendation: remover.
Verification: `grep -snE "^import .*\b(json|os|sys|time)\b" routes/task_routes.py src/views/task_routes.py src/controllers/task_controller.py` → sem ocorrências.

### [LOW] Unused imports and dead code (AP-21)
File: routes/user_routes.py:6
Description: `import hashlib, json, re`: `hashlib` e `json` nunca são usados.
Impact: Imports mortos (e `hashlib` sugere hashing na rota).
Recommendation: remover.
Verification: `grep -snE "^import .*\b(hashlib|json)\b" routes/user_routes.py src/views/user_routes.py src/controllers/user_controller.py` → sem ocorrências.

### [LOW] Unused imports and dead code (AP-21)
File: routes/report_routes.py:7, 8
Description: `from utils.helpers import format_date, calculate_percentage` e `import json` sem uso.
Impact: Imports mortos.
Recommendation: remover.
Verification: `GREP "format_date|calculate_percentage|^import json" .` → sem ocorrências.

### [LOW] Unused imports and dead code (AP-21)
File: models/task.py:3, 38-48
Description: `import json` sem uso; `validate_status` e `validate_priority` nunca são chamados.
Impact: Código morto que parece regra ativa.
Recommendation: remover.
Verification: `GREP "validate_status|validate_priority" .` → sem ocorrências; `grep -snE "^import json" models/task.py src/models/task_model.py` → sem ocorrências.

### [LOW] Unused imports and dead code (AP-21)
File: models/user.py:3, 34-38
Description: `import hashlib` (usado só para MD5, removido por AP-05) e `is_admin()`, que nunca é chamado.
Impact: Código morto.
Recommendation: `is_admin` passa a ser usado pelo guard de autenticação; `hashlib` só fica para o fallback legado em `src/models/user_model.py`.
Verification: `grep -rn "is_admin" src` → ocorrências em src/middlewares/auth.py ou nos controllers, além da definição; `grep -snE "hexdigest\(\) *$" models/user.py src/models/user_model.py` → sem ocorrências em `set_password`.

### [LOW] Unused imports and dead code (AP-21)
File: utils/helpers.py:1-116
Description: `os`, `json`, `sys`, `math` e `hashlib` importados sem uso; `format_date`, `calculate_percentage`, `validate_email`, `sanitize_string`, `generate_id`, `log_action`, `parse_date`, `is_valid_color`, `process_task_data` e todas as constantes nunca são chamados.
Impact: Um módulo inteiro morto que duplica regras.
Recommendation: apagar o arquivo e o pacote `utils/`.
Verification: utils/ não existe mais; `GREP "utils\.helpers|sanitize_string|generate_id|log_action" .` → sem ocorrências.

### [LOW] Unused imports and dead code (AP-21)
File: services/notification_service.py:38-48
Description: `notify_task_overdue` e `get_notifications` nunca são chamados.
Impact: Métodos mortos.
Recommendation: remover; `notify_task_assigned` passa a ser chamado (AP-08).
Verification: `GREP "notify_task_overdue|get_notifications" .` → sem ocorrências.

### [LOW] Print-debugging instead of logging (AP-22)
File: routes/task_routes.py:149, 153, 219, 234
Description: `print(f"Task criada: ...")`, `print(f"Erro ao criar task: ...")` etc.
Impact: Sem nível, sem timestamp e sem como desligar.
Recommendation: P-15 — `logging.getLogger(__name__)`.
Verification: `grep -snE "\bprint\(" routes/task_routes.py src/views/task_routes.py src/controllers/task_controller.py` → sem ocorrências.

### [LOW] Print-debugging instead of logging (AP-22)
File: routes/user_routes.py:83, 89, 147
Description: `print(f"Usuário criado: ...")`, `print(f"ERRO: ...")`, `print(f"Usuário deletado: ...")`.
Impact: Igual ao anterior.
Recommendation: P-15.
Verification: `grep -snE "\bprint\(" routes/user_routes.py src/views/user_routes.py src/controllers/user_controller.py` → sem ocorrências.

### [LOW] Print-debugging instead of logging (AP-22)
File: services/notification_service.py:21, 24
Description: `print(f"Email enviado para {to}")` e `print(f"Erro ao enviar email: ...")`.
Impact: Falhas de envio somem no stdout.
Recommendation: P-15.
Verification: `grep -snE "\bprint\(" services/notification_service.py src/services/notification_service.py` → sem ocorrências.

### [LOW] Print-debugging instead of logging (AP-22)
File: utils/helpers.py:39, 41
Description: `log_action` faz `print` de banner.
Impact: Igual ao anterior.
Recommendation: P-15 — arquivo removido.
Verification: `grep -rnE "\bprint\(" src` → sem ocorrências.

### [LOW] Print-debugging instead of logging (AP-22)
File: seed.py:93-96
Description: O resumo do seed é feito com `print`.
Impact: Saída sem nível nem formato consistente com o app.
Recommendation: P-15 — `logging` configurado no seed; senhas geradas registradas uma vez via logger.
Verification: `grep -nE "\bprint\(" seed.py` → sem ocorrências; `python seed.py` ainda mostra as contagens e as senhas geradas.

### [LOW] Verbose control flow (AP-23)
File: models/task.py:38-60
Description: `if ...: return True else: return False` em `validate_status`/`validate_priority` e uma pirâmide de 3 níveis em `is_overdue`.
Impact: 23 linhas para três expressões booleanas.
Recommendation: P-14 — `return bool(self.due_date) and self.due_date < utcnow() and self.status not in FINAL_STATUSES`.
Verification: `grep -snE "^\s*return (True|False)$" models/task.py src/models/task_model.py` → sem ocorrências.

### [LOW] Verbose control flow (AP-23)
File: models/user.py:34-38
Description: `is_admin` com `if/else` devolvendo `True`/`False`.
Impact: Verbosidade.
Recommendation: P-14 — `return self.role == ROLE_ADMIN`.
Verification: `grep -snE "^\s*return (True|False)$" models/user.py src/models/user_model.py` → sem ocorrências.

### [LOW] Verbose control flow (AP-23)
File: routes/task_routes.py:30-39, 71-80, 141, 210, 283-287
Description: Pirâmides de `if` para `overdue`, `type(tags) == list` e `overdue_count = overdue_count + 1`.
Impact: Verbosidade e checagem de tipo frágil.
Recommendation: P-14 — `is_overdue()`, `isinstance`, agregação SQL.
Verification: `grep -snE "type\(.*\) == list|^\s*return (True|False)$|\b([a-z_]+) = \2 \+ 1" routes/task_routes.py src/views/task_routes.py src/controllers/task_controller.py src/controllers/validators.py` → sem ocorrências.

### [LOW] Verbose control flow (AP-23)
File: routes/user_routes.py:171-180
Description: Pirâmide de 3 níveis de `if` para `overdue`.
Impact: Verbosidade e cópia de regra.
Recommendation: P-14 — `task.is_overdue()`.
Verification: `grep -snE "^\s+if .*due_date" routes/user_routes.py src/views/user_routes.py src/controllers/user_controller.py` → sem ocorrências.

### [LOW] Verbose control flow (AP-23)
File: routes/report_routes.py:33-37, 58-61, 119-135
Description: Contadores manuais `x = x + 1` em laços e `if/elif` por status.
Impact: 30 linhas que um `GROUP BY` resolve.
Recommendation: P-14 + P-09 — contagens agregadas.
Verification: `grep -snE "\b([a-z_]+) = \1 \+ 1" routes/report_routes.py src/services/report_service.py` → sem ocorrências.

### [LOW] Verbose control flow (AP-23)
File: utils/helpers.py:21-23, 53-55, 103
Description: `if re.match(...): return True / return False`, o mesmo em `is_valid_color`, e `type(tags) == list`.
Impact: Verbosidade.
Recommendation: P-14 — arquivo removido; validators usam expressões.
Verification: `GREP "type\(.*\) == list|^\s*return (True|False)$" .` → sem ocorrências.

### [LOW] Verbose control flow (AP-23)
File: services/notification_service.py:22, 25, 44-48
Description: `return True`/`return False` em `send_email` e um laço manual de filtro em `get_notifications`.
Impact: Verbosidade.
Recommendation: P-14 — `send_email` sem valor de retorno; `get_notifications` removido.
Verification: `grep -snE "^\s*return (True|False)$|result\.append" services/notification_service.py src/services/notification_service.py` → sem ocorrências.

================================
Total: 83 findings
================================

## Decisions requiring approval
1. Autenticação real (P-16) — o token falso `fake-jwt-token-<id>` permite se passar por qualquer usuário — default: `POST /login` mantém as chaves `message`, `user`, `token`, mas `token` passa a ser assinado (itsdangerous, `SECRET_KEY`), válido por 24 h (`TOKEN_MAX_AGE`), enviado como `Authorization: Bearer <token>`. Sem `SECRET_KEY` no ambiente, a chave é gerada no boot e os tokens deixam de valer após um restart. Token ausente ou inválido → 401; token de usuário inativo → 403.
2. Política de rotas (P-16) — hoje tudo é anônimo — default: públicas `GET /`, `GET /health`, `POST /login`, `POST /users` (cadastro). Qualquer autenticado: `GET /categories`, `GET /tasks`, `GET /tasks/search`, `GET /tasks/stats`, `POST /tasks`. Dono ou admin: `GET/PUT/DELETE /tasks/<id>`, `GET/PUT /users/<id>`, `GET /users/<id>/tasks`, `GET /reports/user/<id>`. Só admin: `GET /users`, `DELETE /users/<id>`, `GET /reports/summary`, `POST/PUT/DELETE /categories`. Todas as 22 rotas continuam existindo.
3. Escopo das tasks para não-admin — senão `/users/<id>/tasks` seria contornável via `GET /tasks` — default: `GET /tasks`, `/tasks/search` e `/tasks/stats` devolvem só as tasks do chamador (mesmas chaves; admin vê todas); `?user_id=` de outro usuário → 403; tasks sem dono (`user_id` nulo) só são visíveis para o admin. O role `manager` continua sem privilégios extras (como hoje, já que nada o usava).
4. Dono das tasks vem do token — default: não-admin que cria sem `user_id` passa a ter a task com `user_id` = ele mesmo (hoje fica `null`); com `user_id` de outro → 403; não-admin não pode mudar `user_id` de uma task para outro usuário (403). Admin define qualquer dono.
5. Role e `active` no cadastro e na atualização — default: em `POST /users` sem token de admin, o campo `role` é ignorado e o usuário nasce `user` (um valor inválido continua 400); com token de admin, o `role` enviado é respeitado. Em `PUT /users/<id>`, só o admin altera `role` e `active` (não-admin → 403).
6. Campo `password` removido de todas as respostas de usuário (`GET /users/<id>`, `POST /users`, `PUT /users/<id>`, `POST /login`).
7. Formato do hash de senha — default: scrypt do Werkzeug (`scrypt:...`). No boot, hashes MD5 existentes são envoltos em scrypt (`md5+scrypt:...`), sem precisar da senha original, e convertidos para scrypt puro no próximo login bem-sucedido; os usuários mantêm suas senhas.
8. Contas semeadas e senhas padrão — default: `seed.py` usa `SEED_ADMIN_PASSWORD` (admin) e `SEED_USER_PASSWORD` (demais), listadas em `.env.example`; sem elas, gera uma senha aleatória por conta e a imprime uma única vez. No boot, contas cujo hash corresponde às senhas literais antigas (`1234`, `abcd`, `pass`) recebem a senha do ambiente ou uma gerada e impressa uma vez no log; o README deixa de citar senhas.
9. Padrões de execução — default: debug desligado (`FLASK_DEBUG=1` para ligar), escuta em `127.0.0.1` (`HOST=0.0.0.0` é opt-in explícito), porta 5000 (`PORT`), banco `sqlite:///tasks.db` (`DATABASE_URL`), CORS sem nenhuma origem liberada (`CORS_ORIGINS` = lista separada por vírgula).
10. Erros centralizados — default: o formato `{"error": "<mensagem>"}` e as mensagens atuais são mantidos. Mudam: rota inexistente, método não permitido e exceções passam a responder JSON (hoje HTML do Flask); corpo ausente, não-JSON ou malformado → 400 `{"error": "Dados inválidos"}` (hoje 415/400 em HTML); entradas com tipo errado → 400 com mensagem (hoje 500); erros inesperados → 500 `{"error": "Erro interno"}`, com o detalhe só no log.
11. Unicidade de e-mail sem diferenciar maiúsculas — default: índice único em `lower(email)` criado no boot (`CREATE UNIQUE INDEX IF NOT EXISTS`); `POST/PUT /users` com um e-mail que só difere na caixa → 409 "Email já cadastrado" (hoje 201); o login aceita o e-mail em qualquer caixa. O e-mail é armazenado como enviado.
12. Exclusão de categoria — default: `DELETE /categories/<id>` continua 200 e, na mesma transação, as tasks dessa categoria ficam com `category_id = null` (hoje ficam com um id inexistente); no boot, órfãos já existentes recebem o mesmo tratamento.
13. Notificação de atribuição — default: `NotificationService` é ligado ao `TaskController`. Ao criar uma task com dono ou trocar o dono, envia o e-mail de atribuição se `SMTP_HOST`, `SMTP_USER` e `SMTP_PASSWORD` estiverem definidos; sem eles, só registra no log que não enviou. A resposta da API não muda.
14. Novos validadores — default: título string de 3 a 200 caracteres, prioridade inteira finita de 1 a 5 (`true`, `"3"`, `NaN` → 400), tags lista de strings ou string, `user_id`/`category_id` inteiros, cor `#RRGGBB`, nome não vazio em usuário e categoria, `active` booleano; `?priority=`/`?user_id=` não inteiros na busca → 400. Hoje esses casos dão 500 ou são gravados.

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
