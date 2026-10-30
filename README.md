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
    └── refactoring-playbook.md      # Fase 3: 16 padrões de transformação com código antes/depois (Python e JS)
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
- **O relatório tem uma seção "Decisions requiring approval".** Toda refatoração que muda comportamento observável aparece ali com um default, para o humano aprovar explicitamente. Exemplos: remover `senha` da resposta, exigir token, restringir `/admin/query` a admin e a `SELECT`, trocar o formato de hash.
- **Decisão escolhe *como* corrigir, nunca *se* corrige.** Todo finding CRITICAL ou HIGH precisa de uma correção ativa na configuração padrão, sem nenhuma variável de ambiente ligada. "Adiado", "não implementado" e "desligado salvo flag" não são defaults aceitos, e a Fase 3 só termina com todos eles resolvidos. Rotas perigosas são protegidas ou restringidas, nunca removidas.
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
- **Correções de segurança que mudam o contrato** (exigir token, remover `senha` das respostas, restringir `/admin/query`). Elas aparecem como decisões explícitas no relatório, com o default que a Fase 3 aplica, em vez de mudanças silenciosas.
- **Feedback da revisão: autenticação deixada em aberto.** Na primeira entrega, a skill permitia que uma decisão da Fase 2 adiasse um HIGH: no projeto 1 a autenticação ficou "fora do escopo", e no projeto 3 o guard vinha desligado (`AUTH_REQUIRED=0`). A causa estava no catálogo, onde a AP-11 dizia que autenticação completa era "uma decisão". A correção teve três partes:
  - o `SKILL.md` passou a proibir decisões que deixem CRITICAL ou HIGH sem correção ativa;
  - o playbook ganhou o **P-16, "Authentication enforced by default"**, com tokens assinados, política de rotas públicas / autenticadas / dono-ou-admin / só-admin, e fail-closed quando falta segredo;
  - a validação da Fase 3 passou a testar cada rota protegida sem token (`401`/`403`) e com token (status original).

  Depois disso a skill foi rodada de novo nos 3 projetos, a partir do código original.
- **Lacunas encontradas na validação manual.** Rodando o projeto 3 de novo, um usuário comum ainda conseguia apagar task de outro usuário, e o servidor subia em `0.0.0.0`. As duas falhas viraram regras da skill: escrita em registro de outro usuário só para dono ou admin (P-16), e o AP-12 só é considerado resolvido com bind em `127.0.0.1`. O projeto 3 foi rodado mais uma vez com essas regras.
- **Senhas antigas após trocar o hash.** O login aceita o formato legado e regrava a senha no formato novo no primeiro login bem-sucedido, então os bancos e seeds existentes continuam funcionando.
- **Projeto parcialmente organizado (task-manager).** Ter `models/` e `routes/` não garante camadas corretas. O guideline orienta a manter as pastas que já cumprem seu papel e a tirar a regra de negócio das rotas para controllers novos.

---

## C) Resultados

### Resumo das auditorias

| Projeto | Stack detectada | Arquivos | CRITICAL | HIGH | MEDIUM | LOW | Total |
|---|---|---|---|---|---|---|---|
| 1 — code-smells-project | Python + Flask 3.1.1 (sqlite3) | 4 / ~780 linhas | 11 | 9 | 7 | 10 | 37 |
| 2 — ecommerce-api-legacy | JavaScript + Express 4 (sqlite3 em memória) | 3 / ~180 linhas | 5 | 5 | 6 | 4 | 20 |
| 3 — task-manager-api | Python + Flask 3.0.0 (Flask-SQLAlchemy) | 12 / ~1155 linhas | 5 | 11 | 24 | 27 | 67 |

Na Fase 3, os 3 projetos terminaram com todos os findings resolvidos: 37/37, 20/20 e 67/67, sem nenhum CRITICAL ou HIGH em aberto.

### Estrutura antes / depois

**Projeto 1 — code-smells-project**

```
ANTES                         DEPOIS
app.py                        app.py                      (entry point fino: create_app + app.run)
controllers.py                .env.example
database.py                   src/
models.py                     ├── app.py                  (composition root)
requirements.txt              ├── config/settings.py
                              ├── database.py, errors.py
                              ├── models/        produto, usuario, pedido, sistema
                              ├── controllers/   produto, usuario, pedido, sistema, validators
                              ├── views/         produto_routes, usuario_routes, pedido_routes, sistema_routes
                              ├── services/      notification_service, relatorio_service
                              └── middlewares/   auth, error_handler
```

**Projeto 2 — ecommerce-api-legacy**

```
ANTES                         DEPOIS
src/app.js                    src/app.js                  (composition root)
src/AppManager.js             src/config/index.js
src/utils.js                  src/database/    connection, schema, seed
                              src/models/      user, course, enrollment, payment, auditLog
                              src/controllers/ checkout, report, user
                              src/routes/      checkout, admin, user
                              src/services/    payment, password, report, cache
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
          report              ├── database.py, errors.py
services/ notification        ├── models/       task_model, user_model, category_model
utils/    helpers             ├── controllers/  task, user, category, validators
                              ├── views/        task, user, category, report, index routes
                              ├── services/     notification, report
                              └── middlewares/  auth, error_handler
```

### Checklist de validação

| Item | P1 | P2 | P3 |
|---|---|---|---|
| **Fase 1:** linguagem detectada corretamente | ✓ | ✓ | ✓ |
| **Fase 1:** framework detectado corretamente | ✓ | ✓ | ✓ |
| **Fase 1:** domínio descrito corretamente | ✓ | ✓ | ✓ |
| **Fase 1:** número de arquivos condiz com a realidade | ✓ (4) | ✓ (3) | ✓ (12) |
| **Fase 2:** relatório segue o template | ✓ | ✓ | ✓ |
| **Fase 2:** cada finding tem arquivo e linhas exatos | ✓ | ✓ | ✓ |
| **Fase 2:** findings ordenados CRITICAL → LOW | ✓ | ✓ | ✓ |
| **Fase 2:** mínimo de 5 findings | ✓ (37) | ✓ (20) | ✓ (67) |
| **Fase 2:** APIs deprecated detectadas | n/a¹ | ✓ (1) | ✓ (9) |
| **Fase 2:** pausa e pede confirmação antes da Fase 3 | ✓ | ✓ | ✓ |
| **Fase 3:** estrutura de diretórios segue MVC | ✓ | ✓ | ✓ |
| **Fase 3:** configuração extraída (sem hardcoded) | ✓ | ✓ | ✓ |
| **Fase 3:** models abstraem os dados | ✓ | ✓ | ✓ |
| **Fase 3:** views/routes separadas | ✓ | ✓ | ✓ |
| **Fase 3:** controllers concentram o fluxo | ✓ | ✓ | ✓ |
| **Fase 3:** error handling centralizado | ✓ | ✓ | ✓ |
| **Fase 3:** entry point claro | ✓ | ✓ | ✓ |
| **Fase 3:** aplicação inicia sem erros | ✓ | ✓ | ✓ |
| **Fase 3:** endpoints originais respondem corretamente | ✓² | ✓² | ✓² |

¹ O projeto 1 não usa nenhuma API da tabela de deprecated. No projeto 2, a skill marcou a API de callbacks aninhados do `sqlite3`; no projeto 3, `Model.query.get()` e `datetime.utcnow()`.
² Todas as rotas originais continuam existindo e, com as credenciais certas, respondem o mesmo status e as mesmas chaves de antes. As diferenças vêm das decisões aprovadas em cada relatório: rotas protegidas respondem `401` sem token e `403` sem permissão, e campos sensíveis (`senha`, `password`, `secret_key`) saíram das respostas.

### Saída da Fase 1 e pausa da Fase 2

Os blocos abaixo são a saída da Fase 1 nesta rodada. A skill foi executada com `claude -p "/refactor-arch"` sobre o código original. Nos 3 projetos, as Fases 1 e 2 rodaram só com ferramentas de leitura e pararam em `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]`. As decisões foram revisadas antes de responder `y` na mesma sessão.

**Projeto 1**
```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python (runtime version not pinned)
Framework:     Flask 3.1.1 (flask==3.1.1)
Dependencies:  flask-cors==5.0.1
Domain:        E-commerce API (produtos, usuários, pedidos, itens de pedido, relatório de vendas)
Architecture:  Monolithic — app.py registra rotas e executa SQL; controllers.py mistura regras, notificações e SQL; models.py cobre todos os domínios via um singleton global de conexão
Source files:  4 files analyzed (~780 lines)
DB tables:     produtos, usuarios, pedidos, itens_pedido
Endpoints:     19 routes
Start command: python app.py
================================
```

**Projeto 2**
```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      JavaScript (Node.js, runtime não fixado)
Framework:     Express ^4.18.2
Dependencies:  sqlite3 ^5.1.6
Domain:        LMS API com checkout (users, courses, enrollments, payments, audit_logs)
Architecture:  Monolithic — a classe `AppManager` abre o banco, cria o schema, faz o seed, registra as rotas e executa SQL e regras de negócio
Source files:  3 files analyzed (~180 lines)
DB tables:     users, courses, enrollments, payments, audit_logs (SQLite `:memory:`)
Endpoints:     3 routes
Start command: npm start (node src/app.js)
================================
```

**Projeto 3**
```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python (versão não fixada)
Framework:     Flask 3.0.0 (flask==3.0.0)
Dependencies:  flask-sqlalchemy==3.1.1, flask-cors==4.0.0, marshmallow==3.20.1 (não importado), requests==2.31.0 (não importado), python-dotenv==1.0.0 (não importado)
Domain:        Task Manager API (tasks, users, categories)
Architecture:  Partially layered — models/, routes/, services/, utils/ existem, mas as rotas executam queries e regras de negócio, NotificationService nunca é usado e utils/helpers.py duplica regras ignoradas
Source files:  12 files analyzed (~1155 lines)
DB tables:     users, tasks, categories (SQLite tasks.db via Flask-SQLAlchemy)
Endpoints:     22 routes
Start command: pip install -r requirements.txt && python seed.py && python app.py
================================
```

### Controle de acesso e logs após a refatoração

Cada app foi iniciada com o comando original do projeto, com o banco em `/tmp`. Um script chamou cada rota como anônimo, como usuário comum e como admin; as colunas mostram o status HTTP retornado. As requests foram feitas na ordem da tabela, sobre o mesmo banco.

**Projeto 1** (`python app.py`). Cliente: `joao@email.com`; admin: `admin@loja.com`, ambos do seed.
```
login cliente: 200
login admin: 200
ROUTE                                      anon  cliente    admin
GET /                                       200      200      200
GET /health                                 200      200      200
GET /produtos                               200      200      200
GET /produtos/1                             200      200      200
GET /produtos/busca?q=mouse                 200      200      200
GET /usuarios                               401      403      200
GET /usuarios/2                             401      200      200
GET /usuarios/3                             401      403      200
GET /pedidos                                401      403      200
GET /pedidos/usuario/2                      401      200      200
GET /relatorios/vendas                      401      403      200
POST /usuarios                              201      400      400
POST /pedidos                               401      201      201
PUT /pedidos/1/status                       401      403      200
POST /produtos                              401      403      201
PUT /produtos/2                             401      403      200
POST /admin/query                           401      403      200
DELETE /produtos/9                          401      403      200
login com SQL injection: 401 {"erro":"Email ou senha inv\u00e1lidos","sucesso":false}

admin/query com DELETE (admin): 400 {"erro":"Apenas uma instru\u00e7\u00e3o SELECT \u00e9 permitida","sucesso":false}

GET /usuarios/1 (admin) corpo: 200 {"dados":{"criado_em":"2026-10-30 22:12:40","email":"admin@loja.com","id":1,"nome":"Admin"
token forjado (assinatura inválida): 401 {"erro":"Token inv\u00e1lido","sucesso":false}

reset-db como cliente: 403 {"erro":"Acesso restrito a administradores","sucesso":false}
```
O `POST /usuarios` dá `400` nas colunas cliente e admin porque o mesmo e-mail já tinha sido cadastrado na coluna anônima.

Trecho do log do servidor:
```
 * Debug mode: off
 * Running on http://127.0.0.1:5000
[30/Oct/2026 19:12:43] "GET /produtos HTTP/1.1" 200 -
[30/Oct/2026 19:12:43] "GET /produtos HTTP/1.1" 200 -
[30/Oct/2026 19:12:43] "GET /produtos HTTP/1.1" 200 -
[30/Oct/2026 19:12:43] "GET /produtos/1 HTTP/1.1" 200 -
[30/Oct/2026 19:12:43] "GET /usuarios HTTP/1.1" 401 -
[30/Oct/2026 19:12:43] "GET /usuarios HTTP/1.1" 403 -
[30/Oct/2026 19:12:43] "GET /usuarios/2 HTTP/1.1" 401 -
[30/Oct/2026 19:12:43] "GET /usuarios/3 HTTP/1.1" 401 -
[30/Oct/2026 19:12:43] "GET /usuarios/3 HTTP/1.1" 403 -
[30/Oct/2026 19:12:43] "GET /pedidos HTTP/1.1" 401 -
```

**Projeto 2** (`ADMIN_TOKEN=meu-token npm start`). O projeto não tem login, então as rotas de admin usam o token estático de config.
```
ROUTE                                      anon   errado    admin
GET /api/admin/financial-report             401      401      200
checkout novo usuário cartão 4: 200 {"msg":"Sucesso","enrollment_id":2}
checkout cartão 5 (recusado): 400 Pagamento recusado
checkout campos faltando: 400 Bad Request
checkout curso inexistente: 404 Curso não encontrado
checkout email existente senha errada: 401 Credenciais inválidas
checkout email existente senha certa: 200 {"msg":"Sucesso","enrollment_id":3}
relatório (admin) corpo: 200 [{"course":"Clean Architecture","revenue":1994,"students":[{"student":"Leonan","paid":997}
DELETE user sem token: 401 Não autorizado
DELETE user token errado: 401 Não autorizado
DELETE user admin: 200 Usuário deletado.
```
Log do servidor (o cartão aparece só com os 4 últimos dígitos):
```
2026-10-30T22:12:44.549Z INFO Frankenstein LMS rodando na porta 3000...
2026-10-30T22:12:46.503Z INFO Processando cartão final 4444 valor 497
2026-10-30T22:12:46.532Z INFO Processando cartão final 4444 valor 997
2026-10-30T22:12:46.587Z INFO Processando cartão final 4111 valor 997
```

**Projeto 3** (`python seed.py && python app.py`). Usuária comum: `maria@email.com`; admin: `joao@email.com`, ambos do seed; `fake` é o antigo `fake-jwt-token-1`.
```
login maria: 200
login admin: 200
ROUTE                                      anon    maria    admin     fake
GET /                                       200      200      200      200
GET /health                                 200      200      200      200
GET /tasks                                  401      200      200      401
GET /tasks/1                                401      200      200      401
GET /tasks/search?q=a                       401      200      200      401
GET /tasks/stats                            401      200      200      401
GET /categories                             401      200      200      401
GET /users                                  401      403      200      401
GET /users/1                                401      403      200      401
GET /users/2                                401      200      200      401
GET /users/2/tasks                          401      200      200      401
GET /reports/summary                        401      403      200      401
GET /reports/user/2                         401      200      200      401
POST /categories                            401      403      201      401
PUT /categories/1                           401      403      200      401
PUT /users/2                                401      200      200      401
DELETE /categories/4                        401      403      200      401
DELETE /users/3                             401      403      200      401
```
Escrita em tasks de outros usuários, num banco recém-criado:
```
login maria: 200
login admin: 200
ROUTE                                      anon    maria    admin
maria apaga task 3 do pedro: 403 {"error":"Acesso negado"}

maria apaga task 1 do joao: 403 {"error":"Acesso negado"}

admin apaga task 3 do pedro: 200 {"message":"Task deletada com sucesso"}

cadastro anônimo pedindo admin: 201 {"active":true,"created_at":"2026-10-30 22:12:51.468610","email":"h@x.com","id":4,"name":"
```
O cadastro anônimo pedindo `role: admin` responde `201`, mas o usuário é criado como `user`. Conferido pelo login dele, que retorna `"role": "user"`.

Log do servidor durante o teste de escrita em tasks alheias:
```
 * Debug mode: off
 * Running on http://127.0.0.1:5000
[30/Oct/2026 19:12:51] "POST /login HTTP/1.1" 200 -
[30/Oct/2026 19:12:51] "POST /login HTTP/1.1" 200 -
[30/Oct/2026 19:12:51] "DELETE /tasks/3 HTTP/1.1" 403 -
[30/Oct/2026 19:12:51] "DELETE /tasks/1 HTTP/1.1" 403 -
[30/Oct/2026 19:12:51] "DELETE /tasks/3 HTTP/1.1" 200 -
[30/Oct/2026 19:12:51] "POST /users HTTP/1.1" 201 -
```

### Comportamento da skill em stacks diferentes

- **Projeto 1, monólito Python:** a skill criou o layout MVC completo do zero. A autenticação usa tokens assinados com `itsdangerous`. O `/admin/query` continua existindo, só para admin, aceitando apenas `SELECT` numa conexão somente leitura.
- **Projeto 2, Express com callbacks:** a pirâmide de callbacks virou `async/await`, com o checkout numa transação. Como o projeto não tem login, as rotas de admin usam um token estático de config, e sem `ADMIN_TOKEN` respondem `401` a todos (fail closed). As respostas continuam em texto puro (`"Bad Request"`, `"Pagamento recusado"`), porque fazem parte do contrato.
- **Projeto 3, parcialmente organizado:** gerou o maior número de findings, incluindo as APIs deprecated (`Query.get`, `datetime.utcnow`). A estrutura existente foi reorganizada em `src/`, com controllers novos recebendo a regra de negócio. A política de acesso é a mais detalhada dos 3: rotas públicas, autenticadas, de dono ou admin, e só de admin.

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
# Projeto 1 — admin do seed: admin@loja.com / admin123
cd code-smells-project
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python app.py                       # http://localhost:5000
TOKEN=$(curl -s -X POST localhost:5000/login -H 'Content-Type: application/json' \
  -d '{"email":"admin@loja.com","senha":"admin123"}' | python -c 'import json,sys; print(json.load(sys.stdin)["token"])')
curl localhost:5000/usuarios                                   # 401
curl -H "Authorization: Bearer $TOKEN" localhost:5000/usuarios # 200

# Projeto 2 — rotas de admin exigem ADMIN_TOKEN
cd ecommerce-api-legacy
npm install
ADMIN_TOKEN=meu-token npm start               # http://localhost:3000
# use api.http, com @adminToken = meu-token, para as rotas administrativas

# Projeto 3 — admin do seed: joao@email.com / 1234
cd task-manager-api
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python seed.py
.venv/bin/python app.py                       # http://localhost:5000
TOKEN=$(curl -s -X POST localhost:5000/login -H 'Content-Type: application/json' \
  -d '{"email":"joao@email.com","password":"1234"}' | python -c 'import json,sys; print(json.load(sys.stdin)["token"])')
curl -H "Authorization: Bearer $TOKEN" localhost:5000/tasks    # 200
```

As variáveis de ambiente de cada projeto estão documentadas no `.env.example` dele (`SECRET_KEY`, `PORT`, `HOST`, `CORS_ORIGINS`, `ADMIN_TOKEN`, `TOKEN_MAX_AGE`, …). Sem nenhuma variável definida, a autenticação já vem ativa, o servidor escuta só em `127.0.0.1` e a `SECRET_KEY` é gerada a cada boot, o que invalida os tokens a cada reinício.

No npm 12+, scripts de instalação de dependências são bloqueados por padrão. O `package.json` do projeto 2 libera o build do `sqlite3` no campo `allowScripts`; versões anteriores do npm ignoram esse campo.

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