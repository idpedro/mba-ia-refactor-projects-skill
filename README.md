# Refatoração Arquitetural Automatizada — skill `refactor-arch`

Skill do Claude Code que analisa, audita e refatora projetos backend para o padrão MVC, independente da stack. Foi aplicada aos 3 projetos legados deste repositório: dois em Python/Flask e um em Node.js/Express.

- Skill: `<projeto>/.claude/skills/refactor-arch/` (cópia idêntica nos 3 projetos)
- Relatórios da Fase 2: [`reports/audit-project-1.md`](reports/audit-project-1.md), [`reports/audit-project-2.md`](reports/audit-project-2.md), [`reports/audit-project-3.md`](reports/audit-project-3.md)
- Enunciado original do desafio: no fim deste arquivo

---

## A) Análise Manual

Problemas encontrados lendo o código original (commit `6d1ce62`) antes de escrever a skill. As linhas citadas são do código original.

### Projeto 1 — code-smells-project (Python/Flask, API de E-commerce)

| # | Severidade | Problema | Local | Por que importa |
|---|---|---|---|---|
| 1 | CRITICAL | SQL Injection: queries montadas por concatenação de strings | `models.py:28, 49, 58-60, 68, 92, 110, 128, 280, 295-297` | O login (`models.py:110`) pode ser burlado com `' OR '1'='1`, e qualquer tabela pode ser lida ou apagada. |
| 2 | CRITICAL | Endpoint que executa SQL arbitrário e endpoint que apaga o banco, sem autenticação | `app.py:59-69` (`/admin/query`), `app.py:47` (`/admin/reset-db`) | Qualquer pessoa na rede tem controle total do banco. |
| 3 | CRITICAL | Credenciais hardcoded e senhas em texto puro | `app.py:7` (`SECRET_KEY`), `database.py:76` (seed com `admin123`), `models.py:110` (compara a senha em texto puro) | Um vazamento do código ou do banco expõe todas as senhas e a chave de sessão. |
| 4 | CRITICAL | Senha devolvida nas respostas da API | `models.py:83, 99` (`"senha": row["senha"]`) | `GET /usuarios` lista a senha de todos os usuários. |
| 5 | HIGH | Debug ligado e servidor exposto em todas as interfaces | `app.py:8`, `app.py:88` (`debug=True`, `host="0.0.0.0"`) | O debugger do Werkzeug permite execução remota de código. |
| 6 | HIGH | Estado global mutável: conexão única compartilhada entre threads | `database.py:8` (`global db_connection`, `check_same_thread=False`) | Concorrência não controlada e acoplamento de todos os módulos ao mesmo objeto. |
| 7 | MEDIUM | Queries N+1 na listagem de pedidos | `models.py:188, 192, 220, 224` | São 1 + N + N×M queries por request; a resposta degrada conforme os pedidos crescem. |
| 8 | MEDIUM | Tratamento de erro espalhado que vaza detalhes internos | `controllers.py:12, 22, 62, 96, 109, …` (`jsonify({"erro": str(e)})`) | Expõe mensagens internas ao cliente e repete o mesmo `try/except` em todo handler. |
| 9 | LOW | Lista mágica de categorias dentro do handler | `controllers.py:52` | A regra de negócio fica escondida no controller e precisa ser duplicada em cada lugar que a usa. |
| 10 | LOW | `print` usado como log e como "envio" de notificação | `controllers.py:8, 208-210` | Não há níveis de log nem destino configurável, e a notificação é falsa. |

### Projeto 2 — ecommerce-api-legacy (Node.js/Express, LMS com checkout)

| # | Severidade | Problema | Local | Por que importa |
|---|---|---|---|---|
| 1 | CRITICAL | Segredos de produção hardcoded | `src/utils.js:3-4` (`dbPass`, `paymentGatewayKey: "pk_live_..."`) | A chave do gateway de pagamento vaza junto com o repositório. |
| 2 | CRITICAL | God class: `AppManager` cria o banco, define o schema, faz o seed, registra as rotas e contém toda a regra de negócio | `src/AppManager.js:4-141` | Nada pode ser testado nem alterado de forma isolada. |
| 3 | CRITICAL | Hash de senha caseiro e reversível (`badCrypto`: base64 truncado) | `src/utils.js:17-23` | Na prática, as senhas ficam em texto puro. |
| 4 | CRITICAL | Número do cartão e chave do gateway impressos no log | `src/AppManager.js:45` | Viola PCI-DSS: dados de cartão ficam gravados em log. |
| 5 | HIGH | Checkout não atômico (matrícula → pagamento → auditoria em callbacks aninhados, sem transação) | `src/AppManager.js:50-61` | Uma falha no meio do fluxo deixa matrícula sem pagamento. |
| 6 | HIGH | Estado global mutável | `src/utils.js:9-10` (`globalCache`, `totalRevenue`) | Dados compartilhados entre requests, sem dono e sem limite. |
| 7 | MEDIUM | N+1 no relatório financeiro (2 queries por matrícula, por curso) | `src/AppManager.js:92, 104, 106` | O custo cresce de forma quadrática com cursos × alunos. |
| 8 | MEDIUM | Exclusão deixa dados órfãos | `src/AppManager.js:133-135` | A própria resposta admite "matrículas e pagamentos ficaram sujos no banco". |
| 9 | LOW | Nomes crípticos | `src/AppManager.js:29-33` (`u`, `e`, `p`, `cid`, `cc`) | Dificulta a leitura do fluxo mais crítico do sistema. |
| 10 | LOW | Regra mágica de aprovação de pagamento e import morto | `src/AppManager.js:46` (`cc.startsWith("4")`), `src/AppManager.js:2` (`totalRevenue` nunca usado) | Regra de negócio implícita e código morto. |

### Projeto 3 — task-manager-api (Python/Flask, Task Manager)

| # | Severidade | Problema | Local | Por que importa |
|---|---|---|---|---|
| 1 | CRITICAL | Segredos hardcoded | `app.py:13` (`SECRET_KEY`), `services/notification_service.py:9-10` (usuário e senha SMTP) | Credenciais reais versionadas no código. |
| 2 | CRITICAL | Senhas com MD5 sem salt, e hash devolvido na API | `models/user.py:29, 32`, `models/user.py:21` (`'password': self.password` no `to_dict`) | MD5 se quebra com rainbow table, e o hash sai em `GET /users/<id>`. |
| 3 | HIGH | Regra de negócio nas rotas: a lógica de "atrasada" é reimplementada inline e os handlers têm validação, queries e serialização misturadas | `routes/task_routes.py:31, 72, 285`, `routes/report_routes.py` | Mesmo já tendo `models/` e `routes/`, as camadas vazam e a regra fica duplicada. |
| 4 | HIGH | Debug ligado e bind em `0.0.0.0` | `app.py:34` | Debugger exposto com risco de RCE. |
| 5 | MEDIUM | N+1: `User.query.get` / `Category.query.get` por task, `len(u.tasks)` por usuário e uma query de tasks por usuário no relatório | `routes/task_routes.py:42, 51`, `routes/user_routes.py:22`, `routes/report_routes.py:56` | O número de queries cresce linearmente com os registros. |
| 6 | MEDIUM | APIs deprecated: `Model.query.get()` (legado no SQLAlchemy 2.0) e `datetime.utcnow()` (deprecated no Python 3.12) | `routes/task_routes.py:42, 51`, `routes/task_routes.py:31, 72, 285` | Geram warnings hoje e vão quebrar em versões futuras. A troca é por `db.session.get(Model, id)` e `datetime.now(timezone.utc)`. |
| 7 | MEDIUM | `except:` genérico engolindo erros | `routes/task_routes.py:62, 137, 204, 236` | Esconde bugs reais e devolve 500 sem causa. |
| 8 | LOW | Imports não usados | `app.py:7` (`os, sys, json`), `routes/task_routes.py:7` (`json, os, sys, time`), `utils/helpers.py:2-7` | Ruído e falsa impressão de dependência. |
| 9 | LOW | Números mágicos e listas repetidas | `routes/user_routes.py:64` (`< 4`), `routes/user_routes.py:71` (roles inline), `routes/report_routes.py:24-28` (`p1`…`p5`) | `utils/helpers.py` já define `VALID_ROLES`/`MIN_PASSWORD_LENGTH`, mas as rotas não usam. |

---

## B) Construção da Skill

### Estrutura

```
.claude/skills/refactor-arch/
├── SKILL.md                         # passos das 3 fases + critério de "pronto" de cada uma
└── references/
    ├── project-analysis.md          # Fase 1: heurísticas de stack, banco, arquitetura, inventário de endpoints, como subir a app
    ├── anti-patterns.md             # Fase 2: catálogo de 23 anti-patterns com sinais de detecção e severidade
    ├── report-template.md           # Fase 2: formato do relatório + seção "Decisions requiring approval"
    ├── mvc-guidelines.md            # Fase 3: camadas, responsabilidades, layout alvo por stack, bloco final
    └── refactoring-playbook.md      # Fase 3: 15 padrões de transformação com código antes/depois (Python e JS)
```

| Área de conhecimento exigida | Arquivo |
|---|---|
| Análise de projeto | `project-analysis.md` |
| Catálogo de anti-patterns | `anti-patterns.md` |
| Template de relatório | `report-template.md` |
| Guidelines de arquitetura | `mvc-guidelines.md` |
| Playbook de refatoração | `refactoring-playbook.md` |

### Decisões de design

- **O `SKILL.md` contém só passos, e o conhecimento fica nos arquivos de referência.** Cada fase manda ler apenas os arquivos de que precisa no momento em que começa. Assim o agente não carrega o playbook enquanto ainda está auditando.
- **Cada fase termina num critério verificável.** Exemplos:
  - Fase 1: "a contagem de endpoints bate com um grep das chamadas de registro de rota".
  - Fase 2: "todo item do catálogo foi aplicado a todo arquivo".
  - Fase 3: três checagens de validação.

  Isso evita que o agente encerre a fase antes da hora.
- **As fases 1 e 2 só leem.** O primeiro arquivo é escrito na Fase 3, depois do `y`. A Fase 2 termina obrigatoriamente com a pergunta de confirmação.
- **O relatório tem uma seção "Decisions requiring approval".** Toda refatoração que muda comportamento observável aparece ali com um default, para o humano aprovar explicitamente. Exemplos: remover `senha` da resposta, bloquear `/admin/query`, trocar o formato de hash.
- **Contrato antes de mexer no código.** Antes de refatorar, a Fase 3 sobe a app original e faz uma request por endpoint, gravando status e chaves da resposta como baseline. A validação compara a app nova contra esse baseline, e não contra "parece funcionar".
- **Evidência obrigatória.** Todo finding cita um `file:line` conferido com `grep -n`. Toda linha de validação cita uma request realmente feita, e uma checagem que falhou aparece como `✗`, nunca como `✓`.

### Catálogo de anti-patterns (23)

| Severidade | Anti-patterns |
|---|---|
| CRITICAL | AP-01 Credenciais hardcoded · AP-02 SQL Injection · AP-03 God class/module · AP-04 Endpoint destrutivo ou de execução arbitrária sem proteção · AP-05 Senha em texto puro ou hash fraco · AP-06 Exposição de dados sensíveis |
| HIGH | AP-07 Regra de negócio no controller/rota · AP-08 Acoplamento sem injeção de dependência · AP-09 Estado global mutável · AP-10 Escritas não atômicas / dados órfãos · AP-11 Falta de autenticação/autorização · AP-12 Debug e defaults inseguros |
| MEDIUM | AP-13 N+1 · AP-14 Lógica duplicada · AP-15 Validação ausente ou inconsistente · AP-16 Tratamento de erro espalhado ou vazando · AP-17 APIs deprecated · AP-18 Config no código em vez de módulo de config |
| LOW | AP-19 Números/strings mágicos · AP-20 Nomes ruins · AP-21 Imports não usados / código morto · AP-22 `print` como log · AP-23 Fluxo de controle verboso |

Por que esses:
- **Os CRITICAL e HIGH** saíram da análise manual: são os problemas que apareceram em pelo menos um dos 3 projetos e que tornam o sistema inseguro ou impossível de testar.
- **Os MEDIUM e LOW** cobrem o que o enunciado pede explicitamente (N+1, validação, magic numbers, naming).
- **AP-17 (APIs deprecated)** traz uma tabela de APIs obsoletas com o equivalente moderno, para Python/Flask/SQLAlchemy e Node/Express. Exemplos: `Query.get` → `db.session.get`, `datetime.utcnow` → `datetime.now(timezone.utc)`, `new Buffer` → `Buffer.from`, `body-parser` → `express.json()`.
- **Cada entrada lista sinais concretos de detecção,** como "query SQL dentro de loop `for`" ou "`cursor.execute` com `+ str(`", e não descrições genéricas.

### Como a skill ficou agnóstica de tecnologia

- **Heurísticas por stack:** `project-analysis.md` detecta a linguagem pelo manifesto (`requirements.txt`, `package.json`, `go.mod`, …), o framework pelos imports e o banco pelo driver/ORM, e lista como achar rotas em Flask, Express e FastAPI.
- **Sinais em duas linguagens:** os sinais do catálogo são escritos de forma genérica e trazem exemplos em Python e em JavaScript.
- **Layout alvo por stack:** `mvc-guidelines.md` define as responsabilidades de cada camada de forma abstrata e dá um layout alvo para Python e outro para Node.
- **Projetos já organizados:** a skill mantém as pastas que já cumprem seu papel e move apenas o que viola as regras.
- **Playbook nas duas linguagens:** os padrões trazem exemplos antes/depois em Python e em JavaScript.
- **Comando de boot preservado:** a validação usa o comando de boot original do projeto (`python app.py`, `npm start`), então não depende de ferramenta específica.

### Desafios e como foram resolvidos

- **Refatorar sem quebrar a API.** A app original é chamada antes de qualquer mudança para gravar o baseline, e a validação final compara rota por rota.
- **Correções de segurança que mudam o contrato** (bloquear `/admin/query`, remover `senha`, exigir token no relatório financeiro). Elas ficaram como decisões explícitas no relatório, com default, em vez de mudanças silenciosas. As rotas continuam existindo e respondem `403` quando desligadas ou sem credencial, e podem ser ligadas por variável de ambiente.
- **Senhas antigas após trocar o hash.** O login aceita o formato legado e regrava a senha no formato novo no primeiro login bem-sucedido, então os bancos e seeds existentes continuam funcionando.
- **Projeto parcialmente organizado (task-manager).** Ter `models/` e `routes/` não garante camadas corretas. O guideline orienta a manter as pastas que já cumprem seu papel e a tirar a regra de negócio das rotas para controllers novos.

---

## C) Resultados

### Resumo das auditorias

| Projeto | Stack detectada | Arquivos | CRITICAL | HIGH | MEDIUM | LOW | Total |
|---|---|---|---|---|---|---|---|
| 1 — code-smells-project | Python + Flask 3.1.1 (sqlite3) | 4 / ~780 linhas | 9 | 8 | 6 | 10 | 33 |
| 2 — ecommerce-api-legacy | JavaScript + Express 4 (sqlite3 em memória) | 3 / ~180 linhas | 5 | 5 | 6 | 8 | 24 |
| 3 — task-manager-api | Python + Flask 3.0.0 (Flask-SQLAlchemy) | 12 / ~1155 linhas | 5 | 10 | 24 | 29 | 68 |

### Estrutura antes / depois

**Projeto 1 — code-smells-project**

```
ANTES                         DEPOIS
app.py                        app.py                      (entry point fino: create_app(Settings))
controllers.py                .env.example
database.py                   src/
models.py                     ├── app.py                  (composition root)
requirements.txt              ├── config/settings.py
                              ├── database.py
                              ├── errors.py
                              ├── models/        produto_model, usuario_model, pedido_model
                              ├── controllers/   produto, usuario, pedido, sistema, validators
                              ├── views/         produto_routes, usuario_routes, pedido_routes, sistema_routes
                              ├── services/      notification_service, relatorio_service
                              └── middlewares/error_handler.py
```

**Projeto 2 — ecommerce-api-legacy**

```
ANTES                         DEPOIS
src/app.js                    src/app.js                  (composition root)
src/AppManager.js             src/config/index.js
src/utils.js                  src/database/   connection, schema, seed
                              src/models/     user, course, enrollment, payment, auditLog
                              src/controllers/ checkout, report, user
                              src/routes/     checkout, admin, user
                              src/services/   payment, password, report, cache
                              src/middlewares/ adminAuth, asyncHandler, errorHandler
                              src/validators/checkout.validator.js
                              src/utils/logger.js, src/errors.js, .env.example
```

**Projeto 3 — task-manager-api**

```
ANTES                         DEPOIS
app.py                        app.py                      (entry point fino)
database.py                   seed.py
seed.py                       .env.example
models/   task, user,         src/
          category            ├── app.py                  (composition root)
routes/   task, user,         ├── config/settings.py
          report              ├── database.py
services/ notification        ├── models/       task_model, user_model, category_model
utils/    helpers             ├── controllers/  task, user, category, validators
                              ├── views/        task, user, category, report, index routes
                              ├── services/     auth, notification, report
                              └── middlewares/  auth, error_handler
```

### Checklist de validação

| Item | P1 | P2 | P3 |
|---|---|---|---|
| **Fase 1:** linguagem detectada corretamente | ✓ | ✓ | ✓ |
| **Fase 1:** framework detectado corretamente | ✓ | ✓ | ✓ |
| **Fase 1:** domínio descrito corretamente | ✓ | ✓ | ✓ |
| **Fase 1:** número de arquivos condiz com a realidade | ✓ | ✓ | ✓ |
| **Fase 2:** relatório segue o template | ✓ | ✓ | ✓ |
| **Fase 2:** cada finding tem arquivo e linhas exatos | ✓ | ✓ | ✓ |
| **Fase 2:** findings ordenados CRITICAL → LOW | ✓ | ✓ | ✓ |
| **Fase 2:** mínimo de 5 findings | ✓ (33) | ✓ (24) | ✓ (68) |
| **Fase 2:** APIs deprecated detectadas | n/a¹ | ✓¹ | ✓ (9 findings AP-17) |
| **Fase 2:** pausa e pede confirmação antes da Fase 3 | ✓ | ✓ | ✓ |
| **Fase 3:** estrutura de diretórios segue MVC | ✓ | ✓ | ✓ |
| **Fase 3:** configuração extraída (sem hardcoded) | ✓ | ✓ | ✓ |
| **Fase 3:** models abstraem os dados | ✓ | ✓ | ✓ |
| **Fase 3:** views/routes separadas | ✓ | ✓ | ✓ |
| **Fase 3:** controllers concentram o fluxo | ✓ | ✓ | ✓ |
| **Fase 3:** error handling centralizado | ✓ | ✓ | ✓ |
| **Fase 3:** entry point claro | ✓ | ✓ | ✓ |
| **Fase 3:** aplicação inicia sem erros | ✓ | ✓ | ✓ |
| **Fase 3:** endpoints originais respondem corretamente | ✓ | ✓² | ✓ |

¹ O projeto 1 não usa nenhuma API da tabela de deprecated. No projeto 2, a skill marcou o estilo de callbacks aninhados do `sqlite3` como AP-17: no relatório commitado isso aparece dentro do finding AP-10, e na reexecução (veja a Fase 1 abaixo) virou um finding AP-17 próprio.
² As rotas administrativas do projeto 2 exigem `Authorization: Bearer <ADMIN_TOKEN>` (decisão 2 do relatório). Com o token, o relatório financeiro responde igual ao original. O `DELETE /api/users/:id` responde 200, mas agora apaga também matrículas e pagamentos, e o texto mudou de "Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco." para "Usuário deletado." (decisão 3).

**Pontos em aberto:** no projeto 1, a autenticação completa das rotas de usuários, pedidos e relatórios (AP-11) ficou fora do escopo de propósito. Ela mudaria o contrato de todas essas rotas e está registrada como não resolvida na decisão 7 do relatório. No projeto 3, a guarda de autenticação existe mas vem desligada por padrão (`AUTH_REQUIRED=0`, decisão 4), para preservar o contrato. Ligue com `AUTH_REQUIRED=1`.

### Saída da Fase 1 e pausa da Fase 2

A skill imprime a saída da Fase 1 no terminal, sem salvar em arquivo. Os blocos abaixo vêm de uma reexecução do `/refactor-arch` sobre o código original (commit `6d1ce62`), com `claude -p` e só ferramentas de leitura liberadas. Nos 3 projetos a execução parou em `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]` sem criar nem alterar nenhum arquivo.

**Projeto 1**
```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python (versão não fixada)
Framework:     Flask 3.1.1
Dependencies:  flask-cors==5.0.1, sqlite3 (stdlib)
Domain:        API de e-commerce (produtos, usuários, pedidos, itens de pedido, relatórios de vendas)
Architecture:  Monolithic. Os arquivos `controllers.py`/`models.py` existem, mas `app.py` registra rotas e roda SQL direto, `models.py` mistura 4 domínios com regras de negócio, e tudo depende de um singleton global `get_db()`
Source files:  4 files analyzed (~780 lines)
DB tables:     produtos, usuarios, pedidos, itens_pedido
Endpoints:     19 routes
Start command: python app.py (porta 5000)
================================
```

**Projeto 2**
```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      JavaScript (Node.js; no engine pinned — local runtime v24.22.1)
Framework:     Express ^4.18.2
Dependencies:  sqlite3 ^5.1.6
Domain:        LMS API com checkout (users, courses, enrollments, payments, audit_logs)
Architecture:  Monolithic — a single class (AppManager) opens the DB, creates the schema, seeds, registers routes and runs SQL + business rules
Source files:  3 files analyzed (~180 lines)
DB tables:     users, courses, enrollments, payments, audit_logs (SQLite ':memory:')
Endpoints:     3 routes
Start command: npm start  (node src/app.js, port 3000)
================================
```

**Projeto 3**
```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python (versão não fixada no manifesto)
Framework:     Flask 3.0.0 (flask==3.0.0)
Dependencies:  flask-sqlalchemy==3.1.1, flask-cors==4.0.0, marshmallow==3.20.1, requests==2.31.0, python-dotenv==1.0.0 (as três últimas não são importadas por nenhum arquivo)
Domain:        Task Manager API (tasks, users, categories, reports)
Architecture:  Partially layered — models/, routes/, services/, utils/ existem, mas as rotas fazem queries, calculam atraso e agregam relatórios; services/ e utils/ nunca são chamados
Source files:  12 files analyzed (~1155 lines)
DB tables:     users, tasks, categories
Endpoints:     22 routes
Start command: python seed.py && python app.py
================================
```

Nessa reexecução, a contagem de findings variou um pouco em relação aos relatórios commitados: P1 com 35 em vez de 33, P2 com 26 em vez de 24, P3 com 55 em vez de 68. A variação vem de como o agente agrupa ocorrências do mesmo anti-pattern por arquivo. Todos os critérios continuam atendidos: ≥5 findings e ≥1 CRITICAL/HIGH em cada projeto.

### Logs das aplicações após a refatoração

Log de acesso dos servidores refatorados, iniciados com o comando original de cada projeto, com o banco em `/tmp`.

**Projeto 1** (`python app.py`)
```
 * Serving Flask app 'src.app'
 * Debug mode: off
 * Running on http://127.0.0.1:5000
[30/Oct/2026 03:44:55] "GET / HTTP/1.1" 200 -
[30/Oct/2026 03:44:55] "GET /health HTTP/1.1" 200 -
[30/Oct/2026 03:44:55] "GET /produtos HTTP/1.1" 200 -
[30/Oct/2026 03:44:55] "GET /produtos/1 HTTP/1.1" 200 -
[30/Oct/2026 03:44:55] "GET /produtos/busca?q=mouse HTTP/1.1" 200 -
[30/Oct/2026 03:44:55] "GET /produtos/999 HTTP/1.1" 404 -
INFO src.controllers.produto_controller: Produto criado id=11
[30/Oct/2026 03:44:55] "POST /produtos HTTP/1.1" 201 -
[30/Oct/2026 03:44:55] "PUT /produtos/2 HTTP/1.1" 200 -
INFO src.controllers.produto_controller: Produto deletado id=3
[30/Oct/2026 03:44:55] "DELETE /produtos/3 HTTP/1.1" 200 -
[30/Oct/2026 03:44:55] "GET /usuarios HTTP/1.1" 200 -
[30/Oct/2026 03:44:55] "GET /usuarios/1 HTTP/1.1" 200 -
INFO src.controllers.usuario_controller: Usuario criado id=4
[30/Oct/2026 03:44:55] "POST /usuarios HTTP/1.1" 201 -
INFO src.controllers.usuario_controller: Login bem-sucedido id=1
[30/Oct/2026 03:44:56] "POST /login HTTP/1.1" 200 -
INFO src.controllers.usuario_controller: Login falhou
[30/Oct/2026 03:44:56] "POST /login HTTP/1.1" 401 -
INFO src.services.notification_service: EMAIL: pedido 1 criado para usuario 2
INFO src.services.notification_service: SMS: seu pedido foi recebido (pedido 1)
INFO src.services.notification_service: PUSH: novo pedido 1 recebido pelo sistema
[30/Oct/2026 03:44:56] "POST /pedidos HTTP/1.1" 201 -
[30/Oct/2026 03:44:56] "GET /pedidos HTTP/1.1" 200 -
[30/Oct/2026 03:44:56] "GET /pedidos/usuario/2 HTTP/1.1" 200 -
INFO src.services.notification_service: NOTIFICACAO: pedido 1 aprovado, preparar envio
[30/Oct/2026 03:44:56] "PUT /pedidos/1/status HTTP/1.1" 200 -
[30/Oct/2026 03:44:56] "GET /relatorios/vendas HTTP/1.1" 200 -
[30/Oct/2026 03:44:56] "POST /admin/query HTTP/1.1" 403 -
```

**Projeto 2** (`ADMIN_TOKEN=meu-token npm start`): requests com `curl`, seguidas do log do servidor
```
$ POST /api/checkout (cartão 4…)
{"msg":"Sucesso","enrollment_id":2} -> 200
$ POST /api/checkout (cartão 5…)
Pagamento recusado -> 400
$ GET /api/admin/financial-report (Bearer)
[{"course":"Clean Architecture","revenue":997,"students":[{"student":"Leonan","paid":997}]},{"course":"Docker","revenue":497,"students":[{"student":"Guilherme","paid":497}]}] -> 200
$ GET /api/admin/financial-report (sem token)
{"error":"Forbidden"} -> 403
$ DELETE /api/users/1 (Bearer)
Usuário deletado. -> 200
--- log do servidor
2026-10-30T06:45:06.869Z INFO Frankenstein LMS rodando na porta 3000...
2026-10-30T06:45:08.808Z INFO Processing card ending 4444 amount=497
2026-10-30T06:45:08.842Z INFO Processing card ending 4444 amount=997
```
O número do cartão aparece mascarado e a chave do gateway não aparece mais no log.

**Projeto 3** (`python seed.py && python app.py`)
```
 * Debug mode: off
 * Running on http://127.0.0.1:5000
[30/Oct/2026 03:45:12] "GET / HTTP/1.1" 200 -
[30/Oct/2026 03:45:12] "GET /health HTTP/1.1" 200 -
[30/Oct/2026 03:45:12] "GET /tasks HTTP/1.1" 200 -
[30/Oct/2026 03:45:12] "GET /tasks/1 HTTP/1.1" 200 -
[30/Oct/2026 03:45:12] "GET /tasks/search?q=a HTTP/1.1" 200 -
[30/Oct/2026 03:45:12] "GET /tasks/stats HTTP/1.1" 200 -
[30/Oct/2026 03:45:12] "POST /tasks HTTP/1.1" 201 -
[30/Oct/2026 03:45:12] "PUT /tasks/1 HTTP/1.1" 200 -
[30/Oct/2026 03:45:12] "DELETE /tasks/2 HTTP/1.1" 200 -
[30/Oct/2026 03:45:12] "GET /users HTTP/1.1" 200 -
[30/Oct/2026 03:45:12] "GET /users/1 HTTP/1.1" 200 -
[30/Oct/2026 03:45:12] "GET /users/1/tasks HTTP/1.1" 200 -
[30/Oct/2026 03:45:12] "POST /users HTTP/1.1" 201 -
[30/Oct/2026 03:45:12] "PUT /users/2 HTTP/1.1" 200 -
[30/Oct/2026 03:45:12] "DELETE /users/3 HTTP/1.1" 200 -
[30/Oct/2026 03:45:12] "POST /login HTTP/1.1" 200 -
[30/Oct/2026 03:45:12] "GET /reports/summary HTTP/1.1" 200 -
[30/Oct/2026 03:45:12] "GET /reports/user/1 HTTP/1.1" 200 -
[30/Oct/2026 03:45:12] "GET /categories HTTP/1.1" 200 -
[30/Oct/2026 03:45:12] "POST /categories HTTP/1.1" 201 -
[30/Oct/2026 03:45:12] "PUT /categories/1 HTTP/1.1" 200 -
[30/Oct/2026 03:45:12] "DELETE /categories/4 HTTP/1.1" 200 -
```
As 20 rotas originais e mais `GET /` e `GET /health` responderam sem erro, e o campo `password` não aparece em nenhuma resposta.

### Comportamento da skill em stacks diferentes

- **Projeto 1, monólito Python:** a skill criou o layout MVC completo do zero. É onde a análise mais rende: SQL injection e N+1 aparecem por todo o código.
- **Projeto 2, Express com callbacks:** o padrão "atomic writes and flattened callbacks" do playbook converteu a pirâmide de callbacks em `async/await`, e o checkout passou a rodar numa transação `BEGIN`/`COMMIT`/`ROLLBACK`. Foi preciso manter as respostas em texto puro (`"Bad Request"`, `"Pagamento recusado"`), porque elas fazem parte do contrato.
- **Projeto 3, parcialmente organizado:** gerou o maior número de findings, porque a skill audita cada arquivo e o código está espalhado em mais arquivos com problemas repetidos. A estrutura existente (`models/`, `routes/`) foi aproveitada e reorganizada em `src/`, com controllers novos recebendo a regra de negócio. Foi o projeto com mais APIs deprecated (`Query.get`, `datetime.utcnow`).

---

## D) Como Executar

### Pré-requisitos

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) instalado e autenticado
- Python 3.10+ (projetos 1 e 3) e Node.js 18+ (projeto 2)

### Rodar a skill

A skill lê o projeto do diretório atual. Ela está copiada dentro de cada projeto, então basta entrar na pasta:

```bash
# Projeto 1
cd code-smells-project
claude "/refactor-arch"

# Projeto 2
cd ../ecommerce-api-legacy
claude "/refactor-arch"

# Projeto 3
cd ../task-manager-api
claude "/refactor-arch"
```

A skill imprime a análise (Fase 1) e o relatório (Fase 2), e para em `Proceed with refactoring (Phase 3)? [y/n]`. Responda `y` para refatorar. A Fase 3 salva o relatório em `reports/audit-project-{1,2,3}.md`, na raiz do repositório.

### Validar a refatoração

```bash
# Projeto 1
cd code-smells-project
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python app.py                       # http://localhost:5000
curl localhost:5000/produtos

# Projeto 2
cd ecommerce-api-legacy
npm install
ADMIN_TOKEN=meu-token npm start               # http://localhost:3000
# use api.http, com @adminToken = meu-token, para as rotas administrativas

# Projeto 3
cd task-manager-api
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python seed.py
.venv/bin/python app.py                       # http://localhost:5000
curl localhost:5000/tasks
```

As variáveis de ambiente de cada projeto estão documentadas no `.env.example` dele (`SECRET_KEY`, `PORT`, `ADMIN_ENABLED`, `ADMIN_TOKEN`, `AUTH_REQUIRED`, …). Os defaults permitem rodar localmente sem configurar nada.

---

## Enunciado original do desafio


Ao longo do curso você aprendeu o que são Skills e como elas permitem que um agente de IA atue como um especialista em tarefas específicas. Agora imagine o seguinte cenário: você herdou 3 projetos legados com problemas de arquitetura, segurança e qualidade de código. Revisar e corrigir tudo manualmente levaria dias.

Neste desafio, você vai criar uma Skill que automatiza esse processo — analisando, auditando e refatorando qualquer projeto para o padrão MVC, independente da tecnologia.

### Objetivo

Você deve entregar uma Skill capaz de:

- Analisar uma codebase detectando linguagem, framework e arquitetura atual
- Identificar anti-patterns e code smells, classificando por severidade com arquivo e linha exatos
- Gerar um relatório de auditoria estruturado com todos os achados
- Refatorar o projeto para o padrão MVC (Model-View-Controller), eliminando os problemas encontrados
- Validar o resultado garantindo que a aplicação continua funcionando após as mudanças

A skill deve ser agnóstica de tecnologia, funcionando com diferentes linguagens e frameworks.

### Contexto

#### Definição de Severidades

Para padronizar a sua auditoria e os relatórios gerados pela IA, utilize a seguinte escala de classificação baseada em problemas de MVC e SOLID:

- **CRITICAL:** Falhas graves de arquitetura ou segurança que impedem o funcionamento correto, expõem dados sensíveis (ex: credenciais hardcoded, SQL Injection) ou violam completamente a separação de responsabilidades (ex: "God Class" contendo banco de dados, lógicas complexas e roteamento no mesmo arquivo).
- **HIGH:** Fortes violações do padrão MVC ou princípios SOLID que dificultam muito a manutenção e testes (ex: lógicas de negócio pesadas presas dentro de Controllers, forte acoplamento sem Injeção de Dependência, ou uso de estado global mutável em toda a aplicação).
- **MEDIUM:** Problemas de padronização, duplicação de código ou gargalos de performance moderada (ex: Queries N+1 no banco de dados, uso inadequado de middlewares, validações ausentes nas rotas).
- **LOW:** Melhorias de legibilidade, nomenclatura de variáveis ruins, ou "magic numbers" soltos pelo código.

#### Exemplo de Uso no CLI

```bash
# Executar a skill no projeto com problemas
cd code-smells-project
claude "/refactor-arch"
```

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python
Framework:      Flask 3.1.1
Dependencies:  flask-cors
Domain:        E-commerce API (produtos, pedidos, usuários)
Architecture:  Monolítica — tudo em 4 arquivos, sem separação de camadas
Source files:  4 files analyzed
DB tables:     produtos, usuarios, pedidos, itens_pedido
================================
```

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask
Files:   4 analyzed | ~800 lines of code

### Summary
CRITICAL: 4 | HIGH: 5 | MEDIUM: 2 | LOW: 3

### Findings

#### [CRITICAL] God Class / God Method
File: models.py:1-350
Description: Arquivo único contém toda lógica de negócio, queries SQL, validação e formatação para 4 domínios diferentes.
Impact: Impossível testar em isolamento, qualquer mudança afeta tudo.
Recommendation: Separar em models e controllers por domínio.

#### [CRITICAL] Hardcoded Credentials
File: app.py:8
Description: SECRET_KEY hardcoded como 'minha-chave-super-secreta-123'
...

================================
Total: 14 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
> y
```

```
[... refatoração executada ...]

================================
PHASE 3: REFACTORING COMPLETE
================================
### New Project Structure
src/
├── config/settings.py
├── models/
│   ├── produto_model.py
│   └── usuario_model.py
├── views/
│   └── routes.py
├── controllers/
│   ├── produto_controller.py
│   └── pedido_controller.py
├── middlewares/error_handler.py
└── app.py (composition root)

### Validation
  ✓ Application boots without errors
  ✓ All endpoints respond correctly
  ✓ Zero anti-patterns remaining
================================
```

### Tecnologias obrigatórias

- **Ferramenta:** uma das três opções abaixo (não são aceitas outras ferramentas):
  - Claude Code
  - Gemini CLI
  - OpenAI Codex
- **Recurso:** Custom Skills (ou o equivalente na ferramenta escolhida)
- **Formato dos arquivos de referência:** Markdown
- **Projetos-alvo:** Python/Flask (2 projetos) e Node.js/Express (1 projeto) (fornecidos no repositório base)

> **Nota sobre a ferramenta:** Os exemplos deste documento usam o Claude Code (`.claude/skills/`) como referência, pois é a ferramenta utilizada no curso. Se você optar por Gemini CLI ou Codex, adapte o nome da pasta e o comando de invocação conforme a convenção dela — o conceito de skill e a estrutura interna (SKILL.md + arquivos de referência) permanecem os mesmos.

### Requisitos

#### 1. Análise Manual dos Projetos

Antes de criar a skill, você deve entender os problemas que ela vai resolver.

**Tarefas:**

- Analisar o projeto `code-smells-project/` (Python/Flask — API de E-commerce)
- Analisar o projeto `ecommerce-api-legacy/` (Node.js/Express — LMS API com fluxo de checkout)
- Analisar o projeto `task-manager-api/` (Python/Flask — API de Task Manager)

Para cada projeto, identificar e documentar no mínimo 5 problemas, incluindo pelo menos:

- 1 de severidade CRITICAL ou HIGH
- 2 de severidade MEDIUM
- 2 de severidade LOW

Documentar os achados na seção "Análise Manual" do seu `README.md`

> **Dica:** Não precisa encontrar todos os problemas — foque nos que têm maior impacto arquitetural. Use os projetos como insumo para entender quais padrões sua skill precisa detectar.

> **Por que 3 projetos?** Dois são Python/Flask (com níveis de organização diferentes) e um é Node.js/Express. Sua skill precisa funcionar nos 3 para provar que é verdadeiramente agnóstica de tecnologia — lidando tanto com código completamente desestruturado quanto com projetos que já possuem alguma separação de camadas.

#### 2. Criação da Skill

Agora que você conhece os problemas, crie uma skill que os detecte, gere um relatório de auditoria e corrija automaticamente.

**Tarefas:**

Criar a skill dentro do projeto `code-smells-project/` e implementar o SKILL.md com 3 fases sequenciais:

- **Fase 1 — Análise:** Detectar stack, mapear arquitetura atual, imprimir resumo
- **Fase 2 — Auditoria:** Cruzar código contra catálogo de anti-patterns, gerar relatório, pedir confirmação
- **Fase 3 — Refatoração:** Reestruturar para o padrão MVC, validar que funciona

Criar arquivos de referência em Markdown que forneçam à skill o conhecimento necessário para executar as 3 fases. Os arquivos devem cobrir **obrigatoriamente** as seguintes áreas de conhecimento:

| Área de conhecimento | O que deve conter |
|---|---|
| Análise de projeto | Heurísticas para detecção de linguagem, framework, banco de dados e mapeamento de arquitetura |
| Catálogo de anti-patterns | Anti-patterns com sinais de detecção e classificação de severidade |
| Template de relatório | Formato padronizado do relatório de auditoria (Fase 2) |
| Guidelines de arquitetura | Regras do padrão MVC alvo (camadas Models, Views/Routes e Controllers, responsabilidades de cada uma) |
| Playbook de refatoração | Padrões concretos de transformação para cada anti-pattern (com exemplos de código) |

> **Nota:** Você tem liberdade para organizar os arquivos de referência como preferir — pode usar os nomes e a quantidade de arquivos que fizer sentido para sua skill. O importante é que todas as 5 áreas de conhecimento estejam cobertas. O nome da skill (`refactor-arch`) e o arquivo `SKILL.md` são obrigatórios e não devem ser alterados. O path da skill segue a convenção da ferramenta escolhida (no Claude Code, por exemplo, é `.claude/skills/refactor-arch/`).

**Requisitos da skill:**

- Deve ser agnóstica de tecnologia — deve funcionar corretamente nos 3 projetos fornecidos, independente da stack ou nível de organização
- O catálogo de anti-patterns deve conter no mínimo 8 anti-patterns com severidade distribuída (CRITICAL, HIGH, MEDIUM, LOW)
- O catálogo deve incluir detecção de APIs deprecated — identificar uso de APIs obsoletas e recomendar o equivalente moderno
- O playbook deve ter no mínimo 8 padrões de transformação com exemplos de código antes/depois
- A Fase 2 deve pausar e pedir confirmação antes de modificar qualquer arquivo
- A Fase 3 deve validar o resultado (boot da aplicação + endpoints funcionando)

#### 3. Execução da Skill

Execute sua skill nos 3 projetos e valide que ela funciona em todas as stacks.

##### Projeto 1 — code-smells-project (Python/Flask)

Invocar a skill no Claude Code:

```bash
claude "/refactor-arch"
```

> **Nota:** O comando acima é o exemplo com Claude Code. Se você estiver usando Gemini CLI ou Codex, utilize o comando equivalente para invocar uma skill na sua ferramenta.

- Verificar que a Fase 1 detecta corretamente a stack e imprime o resumo
- Verificar que a Fase 2 encontra no mínimo 5 dos problemas documentados na sua análise manual
- Confirmar a execução da Fase 3
- Verificar que a Fase 3:
  - Cria a estrutura de diretórios baseada em MVC
  - A aplicação inicia sem erros
  - Os endpoints originais continuam respondendo
- Salvar o relatório de auditoria (output da Fase 2) em `reports/audit-project-1.md`
- Commitar o código refatorado do projeto no repositório

##### Projeto 2 — ecommerce-api-legacy (Node.js/Express)

Prove que sua skill é reutilizável em outro projeto de backend, mas com stack diferente.

- Copiar a pasta `.claude/skills/refactor-arch/` para dentro de `ecommerce-api-legacy/`
- Invocar a skill:

```bash
cd ../ecommerce-api-legacy
claude "/refactor-arch"
```

- Verificar que as 3 fases executam corretamente neste projeto
- Salvar o relatório em `reports/audit-project-2.md`
- Commitar o código refatorado do projeto no repositório

##### Projeto 3 — task-manager-api (Python/Flask)

Agora o teste com um projeto Python/Flask que já possui alguma organização de camadas (models, routes, services, utils).

- Copiar a pasta `.claude/skills/refactor-arch/` para dentro de `task-manager-api/`
- Invocar a skill:

```bash
cd ../task-manager-api
claude "/refactor-arch"
```

- Verificar que:
  - A Fase 1 detecta corretamente Python/Flask como stack e identifica o domínio de Task Manager
  - A Fase 2 identifica problemas mesmo em um projeto parcialmente organizado
  - A Fase 3 melhora a estrutura sem quebrar a aplicação (todos os endpoints devem continuar respondendo)
- Salvar o relatório em `reports/audit-project-3.md`
- Commitar o código refatorado do projeto no repositório

> **Nota:** Este projeto já possui alguma separação de camadas, mas isso não significa que a arquitetura está adequada. A skill deve identificar tanto problemas de código (segurança, performance, qualidade) quanto oportunidades de melhoria arquitetural. Se houver mudanças estruturais necessárias, a skill deve propô-las e executá-las.

##### Validação

Para cada projeto refatorado, valide o seguinte checklist:

```markdown
### Checklist de Validação

#### Fase 1 — Análise
- [ ] Linguagem detectada corretamente
- [ ] Framework detectado corretamente
- [ ] Domínio da aplicação descrito corretamente
- [ ] Número de arquivos analisados condiz com a realidade

#### Fase 2 — Auditoria
- [ ] Relatório segue o template definido nos arquivos de referência
- [ ] Cada finding tem arquivo e linhas exatos
- [ ] Findings ordenados por severidade (CRITICAL → LOW)
- [ ] Mínimo de 5 findings identificados
- [ ] Detecção de APIs deprecated incluída (se aplicável)
- [ ] Skill pausa e pede confirmação antes da Fase 3

#### Fase 3 — Refatoração
- [ ] Estrutura de diretórios segue padrão MVC
- [ ] Configuração extraída para módulo de config (sem hardcoded)
- [ ] Models criados para abstrair dados
- [ ] Views/Routes separadas para visualização ou roteamento
- [ ] Controllers concentram o fluxo da aplicação
- [ ] Error handling centralizado
- [ ] Entry point claro
- [ ] Aplicação inicia sem erros
- [ ] Endpoints originais respondem corretamente
```

> **Dica:** Se a skill não detectou problemas suficientes ou a refatoração falhou, ajuste os arquivos de referência e execute novamente. É normal precisar de 2-4 iterações.

### Entregável

Repositório público no GitHub (fork do repositório base) contendo:

- Skill completa em `.claude/skills/refactor-arch/` (dentro dos 3 projetos)
- Código refatorado dos 3 projetos (resultado da execução da Fase 3, commitado no repositório)
- Relatórios de auditoria em `reports/` (3 arquivos)
- `README.md` atualizado

#### Estrutura do repositório

Faça um fork do repositório base contendo os três projetos com code smells.

> **Nota:** A estrutura abaixo usa Claude Code como exemplo (`.claude/skills/`). Se estiver usando outra ferramenta, adapte os caminhos conforme a convenção dela.

```
desafio-skills/
├── README.md                              # Sua documentação
│
├── code-smells-project/                   # Projeto 1 — Python/Flask (API de E-commerce)
│   ├── .claude/
│   │   └── skills/
│   │       └── refactor-arch/             # ← SUA SKILL AQUI
│   │           ├── SKILL.md
│   │           └── (arquivos de referência)
│   ├── app.py
│   ├── controllers.py
│   ├── models.py
│   ├── database.py
│   └── requirements.txt
│
├── ecommerce-api-legacy/                  # Projeto 2 — Node.js/Express (LMS API com checkout)
│   ├── .claude/
│   │   └── skills/
│   │       └── refactor-arch/             # ← CÓPIA DA SKILL
│   │           └── ...
│   ├── src/
│   │   ├── app.js
│   │   ├── AppManager.js
│   │   └── utils.js
│   ├── api.http
│   └── package.json
│
├── task-manager-api/                      # Projeto 3 — Python/Flask (API de Task Manager)
│   ├── .claude/
│   │   └── skills/
│   │       └── refactor-arch/             # ← CÓPIA DA SKILL
│   │           └── ...
│   ├── app.py
│   ├── database.py
│   ├── seed.py
│   ├── requirements.txt
│   ├── models/
│   ├── routes/
│   ├── services/
│   └── utils/
│
└── reports/                               # Relatórios gerados
    ├── audit-project-1.md                 # Saída da Fase 2 no projeto 1
    ├── audit-project-2.md                 # Saída da Fase 2 no projeto 2
    └── audit-project-3.md                 # Saída da Fase 2 no projeto 3
```

**O que você vai criar:**

- `.claude/skills/refactor-arch/` — A skill completa (SKILL.md + arquivos de referência)
- Código refatorado dos 3 projetos — resultado da execução da Fase 3, commitado no repositório
- `reports/audit-project-{1,2,3}.md` — Relatório de auditoria de cada projeto
- `README.md` — Documentação do seu processo

**O que já vem pronto:**

- `code-smells-project/` — API de E-commerce Python/Flask com code smells intencionais
- `ecommerce-api-legacy/` — LMS API Node.js/Express (com fluxo de checkout) e problemas de implementação
- `task-manager-api/` — API de Task Manager Python/Flask com organização parcial e problemas de segurança/qualidade

> **Dica:** Cada projeto contém problemas intencionais de diferentes severidades (CRITICAL, HIGH, MEDIUM, LOW), incluindo falhas de segurança, violações arquiteturais e problemas de qualidade de código. Parte do desafio é identificá-los por conta própria através da análise manual do código.

#### README.md deve conter

**A) Seção "Análise Manual":**

- Lista dos problemas identificados manualmente em cada projeto
- Classificação por severidade
- Justificativa de por que cada problema é relevante

**B) Seção "Construção da Skill":**

- Decisões de design: como estruturou o SKILL.md e os arquivos de referência
- Quais anti-patterns incluiu no catálogo e por quê
- Como garantiu que a skill é agnóstica de tecnologia
- Desafios encontrados e como resolveu

**C) Seção "Resultados":**

- Resumo dos relatórios de auditoria dos 3 projetos (quantos findings por severidade em cada)
- Comparação antes/depois da estrutura de cada projeto
- Checklist de validação preenchido para cada projeto
- Screenshots ou logs mostrando as aplicações rodando após refatoração
- Observações sobre como a skill se comportou em stacks diferentes

**D) Seção "Como Executar":**

- Pré-requisitos (a ferramenta escolhida — Claude Code, Gemini CLI ou Codex — instalada e configurada)
- Comandos para executar a skill em cada projeto
- Como validar que a refatoração funcionou

#### Ordem de execução sugerida

**1. Analisar os projetos manualmente**

Leia o código dos três projetos e documente os problemas encontrados.

**2. Criar a skill**

Escreva o SKILL.md e os arquivos de referência.

**3. Executar nos 3 projetos**

```bash
# Projeto 1
cd code-smells-project
claude "/refactor-arch"

# Projeto 2
cd ../ecommerce-api-legacy
claude "/refactor-arch"

# Projeto 3
cd ../task-manager-api
claude "/refactor-arch"
```

Salve a saída da Fase 2 de cada projeto em `reports/audit-project-{1,2,3}.md`.

**4. Iterar**

Se a skill não detectou problemas suficientes ou a refatoração falhou, ajuste os arquivos de referência e execute novamente. É normal precisar de 2-4 iterações.

### Critérios de Aceite

A skill deve atingir os seguintes mínimos em **todos os 3 projetos**:

| Critério | Requisito |
|---|---|
| Fase 1 detecta stack corretamente | OBRIGATÓRIO (3/3 projetos) |
| Fase 2 encontra >= 5 findings | OBRIGATÓRIO (3/3 projetos) |
| Fase 2 inclui pelo menos 1 CRITICAL ou HIGH | OBRIGATÓRIO (3/3 projetos) |
| Fase 3 aplicação funciona após refatoração | OBRIGATÓRIO (3/3 projetos) |

**IMPORTANTE:** Todos os critérios devem ser atingidos nos 3 projetos, não apenas em um!

> **Sobre o projeto 3 (task-manager-api):** Este projeto já possui alguma organização. "aplicação funciona" significa que a API inicia sem erros e todos os endpoints continuam respondendo corretamente.

### Referências

- [Claude Code: Skills](https://docs.anthropic.com/en/docs/claude-code/skills) — Documentação oficial sobre como criar e estruturar Skills
- [Claude Code: Overview](https://docs.anthropic.com/en/docs/claude-code/overview) — Visão geral do Claude Code e suas capacidades
- [The Complete Guide to Building Skills for Claude (PDF)](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf) — Guia completo da Anthropic sobre construção de Skills
- [Equipping Agents for the Real World with Agent Skills](https://claude.com/blog/equipping-agents-for-the-real-world-with-agent-skills) — Blog oficial da Anthropic sobre Agent Skills

---

### Dicas Finais

- **Comece pela análise manual** — entender os problemas profundamente é essencial para criar uma skill que os detecte.
- **O SKILL.md é um prompt** — ele instrui o agente sobre o que fazer, enquanto os arquivos de referência fornecem o conhecimento de domínio.
- **Seja específico nos sinais de detecção** — "código ruim" não ajuda; "query SQL dentro de loop for" é acionável.
- **Teste incrementalmente** — não tente criar a skill perfeita de primeira.
- **A skill deve ser copiável** — se ela só funciona em um projeto específico, está acoplada demais. Teste nos 3 projetos para validar.
- **Projetos diferentes exigem adaptação** — a Fase 3 de um projeto já parcialmente organizado não vai ter as mesmas transformações de um monolito. Sua skill deve se adaptar ao contexto.
- **Pedir confirmação na Fase 2 é obrigatório** — o humano deve revisar o relatório antes de qualquer modificação.
- **Consulte as referências do curso** — revise a documentação oficial da ferramenta escolhida e os materiais das aulas para relembrar a estrutura e anatomia de uma skill.