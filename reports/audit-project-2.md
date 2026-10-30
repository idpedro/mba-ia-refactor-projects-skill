================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   JavaScript + Express (SQLite in-memory via sqlite3)
Files:   3 analyzed | ~180 lines of code

## Summary
CRITICAL: 5 | HIGH: 5 | MEDIUM: 6 | LOW: 4

## Findings

### [CRITICAL] Hardcoded credentials and secrets (AP-01)
File: src/utils.js:1-7
Description: O objeto `config` contém literais de produção: `dbUser: "admin_master"`, `dbPass: "senha_super_secreta_prod_123"`, `paymentGatewayKey: "pk_live_1234567890abcdef"` e `smtpUser`. `dbUser`, `dbPass` e `smtpUser` nunca são lidos (também AP-21).
Impact: Qualquer pessoa com acesso ao repositório obtém a chave live do gateway de pagamento e a senha do banco; rotacionar exige um novo deploy, e os segredos ficam para sempre no histórico do git.
Recommendation: P-01 — mover para `src/config/index.js` lendo `process.env` (`PAYMENT_GATEWAY_KEY`, `PORT`, `DB_PATH`, `ADMIN_TOKEN`), sem valores reais no código; remover as chaves não usadas; criar `.env.example`.

### [CRITICAL] God class / God module (AP-03)
File: src/AppManager.js:4-139
Description: `AppManager` abre a conexão (`new sqlite3.Database(':memory:')`, linha 7), cria o schema e o seed (`initDb`, 10-23), registra as três rotas em `setupRoutes` (25-138), executa todo o SQL, decide o pagamento, cria usuários, monta o relatório financeiro e formata as respostas.
Impact: Nenhuma regra pode ser testada sem subir Express e SQLite juntos; qualquer mudança de checkout, relatório ou usuário mexe no mesmo arquivo.
Recommendation: P-03 — separar em `src/database/{connection,schema,seed}.js`, `src/models/{user,course,enrollment,payment,auditLog}.model.js`, `src/services/{payment,password,report}.service.js`, `src/controllers/{checkout,report,user}.controller.js`, `src/routes/*.routes.js`, com `src/app.js` como composition root.

### [CRITICAL] Unprotected destructive or arbitrary-execution endpoint (AP-04)
File: src/AppManager.js:131-137
Description: `DELETE /api/users/:id` executa `DELETE FROM users WHERE id = ?` com qualquer `id` vindo da URL, sem nenhuma verificação de autenticação ou papel (também AP-11).
Impact: Um cliente anônimo pode apagar qualquer conta, inclusive enumerando ids sequenciais.
Recommendation: P-05 + P-16 — manter a rota em `src/routes/user.routes.js` protegida por `requireAdmin` (401 sem token válido); a exclusão passa a `UserController.delete` → `UserModel.deleteById`.

### [CRITICAL] Plaintext or weak password storage (AP-05)
File: src/utils.js:17-23, src/AppManager.js:18, 68
Description: `badCrypto` repete `Buffer.from(pwd).toString('base64').substring(0, 2)` 10000 vezes e corta em 10 caracteres: é base64 reversível dos 2 primeiros caracteres, sem salt. O seed grava `pass = '123'` em texto puro (linha 18) e o checkout usa a senha padrão `"123456"` quando `pwd` está ausente (linha 68).
Impact: Senhas com o mesmo prefixo geram o mesmo "hash"; um vazamento do banco revela as senhas na hora; contas criadas sem `pwd` ficam todas com a mesma senha conhecida.
Recommendation: P-04 — `src/services/password.service.js` com `crypto.scryptSync` + salt aleatório (`salt:hash`) e `verifyPassword` com `timingSafeEqual`; seed gravando a senha já com hash; remover `badCrypto` e a senha padrão.

### [CRITICAL] Sensitive data exposure (AP-06)
File: src/AppManager.js:45
Description: `console.log(\`Processando cartão ${cc} na chave ${config.paymentGatewayKey}\`)` grava o número completo do cartão e a chave live do gateway no log a cada checkout (também AP-22).
Impact: Qualquer pessoa com acesso aos logs (agregadores, suporte, backups) obtém PANs completos e a chave do gateway; viola PCI-DSS.
Recommendation: P-05 — `PaymentService.charge` em `src/services/payment.service.js` registra apenas os 4 últimos dígitos via logger e nunca a chave.

### [HIGH] Business logic in the controller / route (fat controller) (AP-07)
File: src/AppManager.js:28-78, 80-129
Description: O handler de `POST /api/checkout` (50 linhas) busca o curso, cria o usuário, decide o pagamento (`cc.startsWith("4") ? "PAID" : "DENIED"`, linha 46), cria matrícula, pagamento, log de auditoria e cache. O handler de `GET /api/admin/financial-report` (49 linhas) agrega receita por curso e monta a lista de alunos dentro da rota.
Impact: Regra de aprovação de pagamento e cálculo de receita só podem ser testados via HTTP; trocar o gateway exige reescrever a rota.
Recommendation: P-06 — `CheckoutController.checkout(input)` orquestra o caso de uso; a aprovação vai para `PaymentService.charge`; a agregação vai para `ReportService.financialReport`; as rotas chamam o controller em uma linha.

### [HIGH] Tight coupling / no dependency injection (AP-08)
File: src/AppManager.js:2, 7, src/app.js:8-10
Description: O construtor de `AppManager` instancia o banco diretamente (`new sqlite3.Database(':memory:')`) e o módulo importa `config`, `logAndCache` e `badCrypto` concretos de `./utils`; `app.js` apenas chama `manager.initDb()` e `manager.setupRoutes(app)`, sem composition root, e começa a escutar antes de o schema terminar de ser criado.
Impact: Impossível trocar o banco por um de teste ou simular o gateway; a ordem de inicialização depende de callbacks não aguardados.
Recommendation: P-07 — `src/app.js` cria a conexão, aguarda schema/seed, instancia models, services e controllers, injeta-os nos routers e só então chama `app.listen`.

### [HIGH] Mutable global state (AP-09)
File: src/utils.js:9-10, 14, 25
Description: `let globalCache = {}` e `let totalRevenue = 0` são variáveis de módulo exportadas; `logAndCache` muta `globalCache[key]` a cada checkout (chamado em src/AppManager.js:59).
Impact: Estado compartilhado entre requisições, crescimento ilimitado de memória e acoplamento implícito entre quem importa `utils`.
Recommendation: P-08 — `CacheService` (`src/services/cache.service.js`) com um `Map` interno, uma instância criada em `app.js` e injetada no `CheckoutController`; remover `totalRevenue`.

### [HIGH] Non-atomic multi-step writes and orphaned data (AP-10)
File: src/AppManager.js:50-61, 66-72, 133-135
Description: O checkout faz `INSERT INTO enrollments`, depois `INSERT INTO payments`, depois `INSERT INTO audit_logs` em callbacks aninhados sem transação; o usuário novo é inserido (linha 69) antes de o pagamento ser recusado (linha 48), ficando no banco sem matrícula. `DELETE FROM users` (linha 133) apaga só o usuário e a própria resposta admite que "as matrículas e pagamentos ficaram sujos no banco".
Impact: Uma falha no meio deixa matrícula sem pagamento ou pagamento sem auditoria; exclusões deixam matrículas e pagamentos órfãos, e o relatório passa a listar alunos "Unknown".
Recommendation: P-11 — driver promisificado em `src/database/connection.js` com `transaction()`; checkout decide o pagamento antes de qualquer escrita e grava usuário, matrícula, pagamento e auditoria numa única transação; `UserModel.deleteById` apaga pagamentos, matrículas e o usuário na mesma transação.

### [HIGH] Missing authentication / authorization (AP-11)
File: src/AppManager.js:40, 66-75, 80
Description: `GET /api/admin/financial-report` (linha 80) devolve receita e nomes de todos os alunos sem autenticação. No checkout, quando o `eml` já existe (linhas 40, 73-74) a matrícula e o pagamento são vinculados à conta existente sem conferir `pwd`, de modo que qualquer cliente age em nome de outro usuário.
Impact: Dados financeiros e pessoais acessíveis anonimamente; qualquer pessoa cria matrículas e cobranças na conta de terceiros só conhecendo o e-mail.
Recommendation: P-16 — middleware `requireAdmin` em `src/middlewares/auth.js` com token de admin estático vindo de `ADMIN_TOKEN` (comparado com `timingSafeEqual`, fail closed quando ausente) nas rotas de admin; no checkout, `pwd` é verificado com `verifyPassword` quando o e-mail já existe.

### [MEDIUM] N+1 queries (AP-13)
File: src/AppManager.js:89-106
Description: `courses.forEach` dispara `SELECT * FROM enrollments WHERE course_id = ?` por curso, e `enrollments.forEach` dispara `SELECT name, email FROM users` e `SELECT amount, status FROM payments` por matrícula: 1 + C + 2·M consultas.
Impact: O relatório cresce linearmente em consultas com o número de matrículas e a ordem da resposta depende da ordem de término dos callbacks.
Recommendation: P-09 — uma única consulta com `LEFT JOIN enrollments/users/payments` ordenada por curso e matrícula, agrupada em memória em `ReportService.financialReport`.

### [MEDIUM] Duplicated logic (AP-14)
File: src/AppManager.js:86-87, 95-99, 117-122
Description: O bloco de contagem manual "decrementa `coursesPending`/`enrPending` e, se chegou a zero, `report.push(courseData)` + `res.json(report)`" aparece copiado em dois pontos, com o mesmo controle verboso de contadores (também AP-23).
Impact: Qualquer ajuste na finalização do relatório precisa ser feito em dois lugares; esquecer um gera resposta duplicada ou requisição que nunca responde.
Recommendation: P-12 — substituído pelo agrupamento único de P-09 em `ReportService`, sem contadores.

### [MEDIUM] Missing or inconsistent input validation (AP-15)
File: src/AppManager.js:29-35, 46
Description: Só há checagem de presença de `usr`, `eml`, `c_id`, `card`; nenhum tipo é validado. `card` numérico faz `cc.startsWith` (linha 46) lançar `TypeError` dentro de um callback do sqlite, derrubando o processo; `eml` sem formato de e-mail e `pwd` ausente são aceitos.
Impact: Uma única requisição com `"card": 4111...` (número) encerra o servidor para todos os clientes.
Recommendation: P-12 — `src/validators/checkout.validator.js` validando tipos (strings não vazias, `c_id` inteiro positivo, `card` só dígitos, `eml` com formato de e-mail), lançando `ValidationError` → 400 "Bad Request".

### [MEDIUM] Scattered or leaky error handling (AP-16)
File: src/AppManager.js:38, 41, 51, 55, 57, 70, 84, 92, 104, 106, 133, src/app.js:5-10
Description: Cada callback responde erros com `res.status(...).send("Erro DB")` em texto puro; a linha 38 trata erro de banco como 404; os callbacks das linhas 57, 92, 104, 106 e 133 ignoram `err` (na 92 `enrollments.length` sobre `undefined` derruba o processo); não existe middleware de erro em `app.js`.
Impact: Falhas de banco viram 404 ou crash do processo; comportamento de erro inconsistente entre rotas.
Recommendation: P-10 — `src/middlewares/errorHandler.js` + `asyncHandler`; classes `ValidationError`, `NotFoundError`, `PaymentDeclinedError`, `UnauthorizedError` em `src/errors.js`; controllers lançam, o middleware responde.

### [MEDIUM] Deprecated APIs (AP-17)
File: src/AppManager.js:37-77, 83-128
Description: APIs de banco em estilo callback aninhadas 4 níveis no checkout (`db.get` → `db.get` → `db.run` → `db.run` → `db.run`) e 5 no relatório; é esse aninhamento que esconde os `err` ignorados de AP-16 e a falta de transação de AP-10.
Impact: Fluxo difícil de ler; exceções dentro dos callbacks escapam do Express e derrubam o processo.
Recommendation: P-11/P-13 — `async/await` sobre o driver promisificado (`run/get/all`) em `src/database/connection.js`.

### [MEDIUM] Configuration in code instead of a config module (AP-18)
File: src/utils.js:6, src/AppManager.js:7
Description: `port: 3000` fica num arquivo de utilidades junto com o cache e o "hash"; o caminho do banco `':memory:'` está literal no construtor de `AppManager`.
Impact: Não é possível trocar porta ou usar um banco em arquivo por ambiente sem editar o código.
Recommendation: P-01 — `src/config/index.js` com `port: Number(process.env.PORT) || 3000` e `dbPath: process.env.DB_PATH || ':memory:'`.

### [LOW] Magic numbers and strings (AP-19)
File: src/AppManager.js:21, 46, 48, 68, 108, src/utils.js:19, 22
Description: Status `"PAID"`/`"DENIED"` comparados inline (21, 46, 48, 108); prefixo de aprovação `"4"` (46); senha padrão `"123456"` (68); laço de `10000` iterações e corte em `10` em `badCrypto`.
Impact: A regra de aprovação e os status ficam espalhados; mudar um exige caçar literais.
Recommendation: P-14 — constantes `PAYMENT_STATUS` e `APPROVED_CARD_PREFIX` em `src/services/payment.service.js`; `badCrypto` e a senha padrão somem com P-04.

### [LOW] Poor naming (AP-20)
File: src/AppManager.js:26, 29-33, 89, src/utils.js:12, 17
Description: Variáveis `u`, `e`, `p`, `cid`, `cc`, `c`, `self`; `logAndCache` faz duas coisas; `badCrypto` descreve o defeito, não a função. Os campos de requisição `usr`, `eml`, `pwd`, `c_id` são contrato público.
Impact: O leitor precisa rastrear cada abreviação até o `req.body`.
Recommendation: P-14 — desestruturar `const { usr: name, eml: email, pwd: password, c_id: courseId, card } = req.body`; manter os nomes dos campos de requisição (contrato).

### [LOW] Unused imports and dead code (AP-21)
File: src/AppManager.js:2, src/utils.js:2-3, 5, 10, 25
Description: `totalRevenue` é importado (AppManager.js:2) e exportado (utils.js:10, 25) e nunca lido; `globalCache` é exportado e nunca lido fora de `utils`; `dbUser`, `dbPass`, `smtpUser` nunca são usados (segredos tratados em AP-01).
Impact: Ruído que sugere funcionalidades inexistentes (receita total, SMTP).
Recommendation: Remover.

### [LOW] Print-debugging instead of logging (AP-22)
File: src/app.js:13, src/utils.js:13
Description: `console.log` é o único mecanismo de log: banner de boot e `[LOG] Salvando no cache: ...` a cada checkout (o log do cartão em AppManager.js:45 está em AP-06).
Impact: Sem níveis nem formato; impossível silenciar ou filtrar em produção.
Recommendation: P-15 — `src/utils/logger.js` com `info/warn/error` sobre `console`, usado pelo boot e pelos services.

================================
Total: 20 findings
================================

## Decisions requiring approval
1. Autenticação de admin — `GET /api/admin/financial-report` e `DELETE /api/users/:id` exigem `Authorization: Bearer <ADMIN_TOKEN>`; sem token ou com token inválido respondem 401 — AP-04/AP-11, o projeto não tem login nem papéis, então o token estático de config (P-16) é o mecanismo mais simples — default: proteção ativa sempre; se `ADMIN_TOKEN` não estiver definido as duas rotas respondem 401 a todos (fail closed); `POST /api/checkout` continua público; README e `.env.example` documentam a variável.
2. Checkout com e-mail já cadastrado exige `pwd` correto — AP-11, hoje qualquer um compra na conta de outro — default: senha conferida com `verifyPassword`; ausente ou errada → 401 `Credenciais inválidas` (texto puro).
3. Formato do hash de senha — AP-05 — default: `scrypt` com salt (`salt:hash`); o seed grava a senha do Leonan (`123`) já com hash; `pwd` passa a ser obrigatório para criar usuário novo (sem a senha padrão `123456`) → 400 `Bad Request` quando ausente. O banco é em memória, então nenhum hash antigo precisa de compatibilidade.
4. Checkout atômico — AP-10 — default: o cartão é avaliado antes de qualquer escrita; checkout recusado (400 `Pagamento recusado`) não cria mais o usuário; usuário, matrícula, pagamento e auditoria são gravados numa única transação.
5. Exclusão de usuário em cascata — AP-10 — default: `DELETE /api/users/:id` apaga pagamentos, matrículas e o usuário na mesma transação; continua 200 com corpo texto, que passa de "Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco." para "Usuário deletado." (a frase antiga deixa de ser verdade).
6. Corpos de erro — AP-16 — default: mantêm texto puro e as mensagens/status originais (`Bad Request` 400, `Curso não encontrado` 404, `Pagamento recusado` 400); erros inesperados → 500 `Erro interno` com detalhes só no log; entradas de tipo inválido (ex.: `card` numérico) → 400 `Bad Request` em vez de derrubar o processo.
7. Logs — AP-06 — default: o log do checkout mostra só os 4 últimos dígitos do cartão e nunca a chave do gateway.
8. Ordem do relatório — AP-13 — default: mesmas chaves (`course`, `revenue`, `students[{student, paid}]`), agora em ordem determinística por id do curso e da matrícula (hoje depende da ordem de término dos callbacks).
9. Nomes de campos — AP-20 — default: os campos de requisição (`usr`, `eml`, `pwd`, `c_id`, `card`) e de resposta (`msg`, `enrollment_id`) ficam como estão; só variáveis internas são renomeadas.

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
