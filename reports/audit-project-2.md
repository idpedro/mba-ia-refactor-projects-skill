================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   JavaScript + Express 4 (SQLite in-memory, sqlite3 driver)
Files:   3 analyzed | ~180 lines of code

## Summary
CRITICAL: 5 | HIGH: 5 | MEDIUM: 6 | LOW: 8

## Findings

### [CRITICAL] Hardcoded credentials and secrets (AP-01)
File: src/utils.js:2-5
Description: O objeto `config` contém literais de credenciais de produção: `dbUser: "admin_master"`, `dbPass: "senha_super_secreta_prod_123"`, `paymentGatewayKey: "pk_live_1234567890abcdef"` e `smtpUser`. A chave do gateway ainda é impressa no log em src/AppManager.js:45.
Impact: Qualquer pessoa com acesso ao repositório obtém a senha do banco e a chave live do gateway de pagamento; trocar a chave exige alterar código e fazer deploy.
Recommendation: P-01 — mover os valores para variáveis de ambiente lidas em `src/config/index.js` (`PAYMENT_GATEWAY_KEY`, etc.), sem valores reais no código, e criar `.env.example`.

### [CRITICAL] God class / God module (AP-03)
File: src/AppManager.js:4-139
Description: A classe `AppManager` abre a conexão (`new sqlite3.Database(':memory:')`, linha 7), cria schema e seeds em `initDb()` (10-23), registra todas as rotas em `setupRoutes(app)` (25-138), executa todo o SQL, decide o pagamento (`cc.startsWith("4")`) e agrega o relatório financeiro.
Impact: Nenhuma parte pode ser testada isoladamente; qualquer mudança em checkout, relatório ou usuários toca o mesmo arquivo e o mesmo objeto.
Recommendation: P-03 — dividir em `src/database/{connection,schema,seed}.js`, `src/models/*.model.js`, `src/services/payment.service.js`, `src/controllers/*.controller.js`, `src/routes/*.routes.js`, com `src/app.js` como composition root.

### [CRITICAL] Plaintext or weak password storage (AP-05)
File: src/AppManager.js:18, 68
Description: O seed insere o usuário `Leonan` com `pass = '123'` em texto puro (linha 18); o checkout grava `badCrypto(p || "123456")` (linha 68), isto é, a senha padrão `"123456"` quando `pwd` não é enviado.
Impact: Senhas legíveis no banco e uma senha padrão previsível para todo usuário criado sem `pwd`.
Recommendation: P-04 — hash com `crypto.scryptSync` + salt em `src/services/password.service.js`, seed com senha hasheada em `src/database/seed.js`, e senha aleatória inutilizável quando `pwd` estiver ausente (ver decisão 1).

### [CRITICAL] Plaintext or weak password storage (AP-05)
File: src/utils.js:17-23
Description: `badCrypto(pwd)` concatena 10000 vezes os 2 primeiros caracteres do `Buffer.from(pwd).toString('base64')` e devolve os 10 primeiros caracteres: é base64 truncado, reversível em parte e sem salt.
Impact: Senhas iguais geram o mesmo "hash"; as senhas podem ser recuperadas ou colididas trivialmente se o banco vazar.
Recommendation: P-04 — substituir por `hashPassword`/`verifyPassword` com `crypto.scryptSync` em `src/services/password.service.js`; apagar `badCrypto`.

### [CRITICAL] Sensitive data exposure (AP-06)
File: src/AppManager.js:45
Description: `console.log(\`Processando cartão ${cc} na chave ${config.paymentGatewayKey}\`)` grava o número completo do cartão e a chave live do gateway no log a cada checkout. Também é print-debugging (AP-22).
Impact: Vazamento de PAN (violação PCI-DSS) e da chave do gateway para quem tiver acesso aos logs.
Recommendation: P-05 — `src/services/payment.service.js` registra apenas os 4 últimos dígitos via `src/utils/logger.js` e nunca loga a chave.

### [HIGH] Business logic in the controller / route (AP-07)
File: src/AppManager.js:28-78, 80-129
Description: O handler de `POST /api/checkout` (51 linhas) decide o pagamento (`let status = cc.startsWith("4") ? "PAID" : "DENIED"`, linha 46), cria usuário, matrícula, pagamento e auditoria; o handler de `GET /api/admin/financial-report` (50 linhas) soma `courseData.revenue` e monta `students` dentro da rota.
Impact: Regras de pagamento e de relatório só podem ser testadas via HTTP e não podem ser reutilizadas.
Recommendation: P-06 — mover o fluxo para `src/controllers/checkout.controller.js` + `src/services/payment.service.js` e a agregação para `src/services/report.service.js` chamado por `src/controllers/report.controller.js`; rotas ficam com uma linha.

### [HIGH] Tight coupling / no dependency injection (AP-08)
File: src/AppManager.js:2, 7
Description: O construtor cria a própria conexão `new sqlite3.Database(':memory:')` (linha 7) e a classe importa diretamente `config`, `logAndCache`, `badCrypto` do módulo `./utils` (linha 2); `src/app.js:8-10` apenas instancia o God class, não há composition root que injete dependências.
Impact: Impossível substituir o banco ou o gateway por dublês em testes; o caminho do banco é fixo.
Recommendation: P-07 — `src/app.js` cria a conexão, models, services e controllers e os injeta por construtor.

### [HIGH] Mutable global state (AP-09)
File: src/utils.js:9, 12-15, 25
Description: `let globalCache = {}` é um objeto de módulo exportado (linha 25) e mutado por `logAndCache` (`globalCache[key] = data`, linha 14), chamado a cada checkout em src/AppManager.js:59.
Impact: Estado compartilhado entre requisições, cresce sem limite (vazamento de memória) e vaza entre testes.
Recommendation: P-08 — `src/services/cache.service.js` (classe com `Map`) instanciado em `src/app.js` e injetado no controller de checkout.

### [HIGH] Non-atomic multi-step writes and orphaned data (AP-10)
File: src/AppManager.js:50-63, 69-71, 133-135
Description: O checkout faz `INSERT INTO users` (69), `INSERT INTO enrollments` (50), `INSERT INTO payments` (54) e `INSERT INTO audit_logs` (57) em callbacks aninhados (4 níveis, estilo callback superado — AP-17) sem transação; uma falha no meio deixa matrícula sem pagamento. `DELETE FROM users WHERE id = ?` (133) apaga o usuário e deixa matrículas e pagamentos órfãos, como a própria resposta admite ("ficaram sujos no banco", linha 135).
Impact: Dados inconsistentes: matrículas sem pagamento, pagamentos de usuários inexistentes, relatório financeiro com alunos `Unknown`.
Recommendation: P-11 — driver promisificado + `transaction()` em `src/database/connection.js`; checkout e exclusão de usuário (filhos antes do pai) dentro de uma transação em `src/controllers/checkout.controller.js` e `src/models/user.model.js`.

### [HIGH] Missing authentication / authorization (AP-11)
File: src/AppManager.js:80, 131
Description: `GET /api/admin/financial-report` (receita e nomes de alunos) e `DELETE /api/users/:id` (exclusão de qualquer usuário) não têm nenhuma verificação de autenticação ou papel.
Impact: Qualquer cliente anônimo lê dados financeiros e pessoais e apaga contas de terceiros.
Recommendation: P-05 — middleware `src/middlewares/adminAuth.js` exigindo `Authorization: Bearer <ADMIN_TOKEN>` nas duas rotas (ver decisão 2).

### [MEDIUM] N+1 queries (AP-13)
File: src/AppManager.js:89-125
Description: `courses.forEach(c => this.db.all("SELECT * FROM enrollments WHERE course_id = ?"...))` (89-92) e, para cada matrícula, `SELECT name, email FROM users` (104) e `SELECT amount, status FROM payments` (106): 1 + C + 2·E queries.
Impact: O relatório cresce linearmente em queries com o número de matrículas.
Recommendation: P-09 — uma query com `LEFT JOIN` de courses/enrollments/users/payments em `src/models/course.model.js` (`findFinancialRows`), agrupada em memória em `src/services/report.service.js`.

### [MEDIUM] Duplicated logic (AP-14)
File: src/AppManager.js:95-99, 118-122
Description: O bloco `report.push(courseData); coursesPending--; if (coursesPending === 0) res.json(report);` aparece duas vezes, junto com contadores manuais `coursesPending`/`enrPending` (controle de fluxo verboso, AP-23).
Impact: Correções na finalização do relatório precisam ser feitas em dois lugares; contadores manuais facilitam respostas duplas ou ausentes.
Recommendation: P-12 — uma única função de agregação em `src/services/report.service.js` usando async/await.

### [MEDIUM] Missing or inconsistent input validation (AP-15)
File: src/AppManager.js:35, 46, 132
Description: O checkout só testa presença (`if (!u || !e || !cid || !cc)`); `cc.startsWith("4")` (46) lança `TypeError` dentro do callback do sqlite quando `card` não é string (ex.: número), derrubando o processo; `c_id` e `eml` não têm checagem de tipo/formato. `req.params.id` (132) é usado sem validação.
Impact: Um único corpo malformado derruba o servidor inteiro (DoS); dados inválidos chegam ao banco.
Recommendation: P-12 — `src/validators/checkout.validator.js` validando tipos (strings não vazias, `c_id` inteiro) e lançando `ValidationError` (400 "Bad Request").

### [MEDIUM] Scattered or leaky error handling (AP-16)
File: src/AppManager.js:38, 41, 51, 55, 57, 70, 84, 92, 104, 106, 133
Description: Cada callback responde erros com `res.status(...).send("Erro DB")`/`"Erro Matrícula"` etc.; `err || !course` (38) transforma erro de banco em 404; os callbacks das linhas 57, 92, 104, 106 e 133 ignoram `err` (em 92 `enrollments.length` lança se houver erro). Não existe middleware central de erros em src/app.js.
Impact: Erros de banco são mascarados ou derrubam o processo; o tratamento é inconsistente entre rotas.
Recommendation: P-10 — classes `AppError`/`ValidationError`/`NotFoundError` em `src/errors.js`, `asyncHandler` nas rotas e `src/middlewares/errorHandler.js` registrado por último em `src/app.js`.

### [MEDIUM] Configuration in code instead of a config module (AP-18)
File: src/utils.js:6
Description: `port: 3000` fixo no objeto `config` de um módulo utilitário.
Impact: Não é possível subir em outra porta por ambiente sem editar código.
Recommendation: P-01 — `port: Number(process.env.PORT) || 3000` em `src/config/index.js`.

### [MEDIUM] Configuration in code instead of a config module (AP-18)
File: src/AppManager.js:7
Description: Caminho do banco `':memory:'` fixo no construtor de `AppManager`.
Impact: Impossível usar um arquivo persistente ou outro banco por ambiente.
Recommendation: P-01 — `dbPath: process.env.DB_PATH || ':memory:'` em `src/config/index.js`, usado por `src/database/connection.js`.

### [LOW] Magic numbers and strings (AP-19)
File: src/AppManager.js:46, 48, 68, 108
Description: Prefixo de cartão `"4"` como regra de aprovação, status `"PAID"`/`"DENIED"` comparados inline (46, 48, 108) e senha padrão `"123456"` (68).
Impact: Regras implícitas e strings repetidas que divergem com facilidade.
Recommendation: P-14 — constantes `PAYMENT_STATUS` e `APPROVED_CARD_PREFIX` em `src/services/payment.service.js`.

### [LOW] Magic numbers and strings (AP-19)
File: src/utils.js:19, 22
Description: `10000` iterações e `substring(0, 10)` em `badCrypto` sem explicação.
Impact: Parece "custo" de hash, mas não acrescenta segurança.
Recommendation: P-14 / P-04 — removidos junto com `badCrypto`; parâmetros do scrypt como constantes nomeadas em `src/services/password.service.js`.

### [LOW] Poor naming (AP-20)
File: src/AppManager.js:29-33, 89
Description: Variáveis `u`, `e`, `p`, `cid`, `cc` (29-33) e `c` (89); campos de requisição crípticos `usr`, `eml`, `pwd`, `c_id`.
Impact: Leitura difícil do fluxo de checkout.
Recommendation: P-14 — desestruturar para `name`, `email`, `password`, `courseId`, `card` no controller; os campos públicos `usr`/`eml`/`pwd`/`c_id`/`card` permanecem (contrato).

### [LOW] Poor naming (AP-20)
File: src/utils.js:12, 17
Description: `logAndCache` faz duas coisas; `badCrypto` descreve a própria falha em vez da função.
Impact: Nomes enganosos escondem responsabilidades.
Recommendation: P-14 — substituídos por `CacheService.set` e `hashPassword`.

### [LOW] Unused imports and dead code (AP-21)
File: src/AppManager.js:2
Description: `totalRevenue` é importado e nunca usado.
Impact: Ruído e falsa impressão de que a receita é acumulada globalmente.
Recommendation: Deletar.

### [LOW] Unused imports and dead code (AP-21)
File: src/utils.js:10, 25
Description: `let totalRevenue = 0` exportado e nunca lido nem escrito; `globalCache` exportado e nunca lido fora do módulo; `dbUser`, `dbPass`, `smtpUser` nunca são lidos.
Impact: Código morto e segredos sem uso.
Recommendation: Deletar.

### [LOW] Print-debugging instead of logging (AP-22)
File: src/app.js:13
Description: `console.log` do banner de inicialização como único mecanismo de log.
Impact: Sem níveis nem formato consistente.
Recommendation: P-15 — `src/utils/logger.js` com níveis, usado pelo composition root.

### [LOW] Print-debugging instead of logging (AP-22)
File: src/utils.js:13
Description: `console.log(\`[LOG] Salvando no cache: ${key}\`)` dentro de `logAndCache`.
Impact: Log ad hoc misturado com efeito colateral de cache.
Recommendation: P-15 — `logger.debug` em `src/services/cache.service.js` (ou remoção).

================================
Total: 24 findings
================================

## Decisions requiring approval
1. Formato de hash de senha muda de `badCrypto` (base64 truncado) para `salt:scrypt` hex; o usuário seed passa a ter a senha `123` hasheada; checkout sem `pwd` grava um hash de senha aleatória em vez de `"123456"` — nenhuma rota lê senhas, então nenhuma resposta muda — default: aplicar scrypt e senha aleatória.
2. `GET /api/admin/financial-report` e `DELETE /api/users/:id` passam a exigir `Authorization: Bearer <ADMIN_TOKEN>`; sem `ADMIN_TOKEN` configurado ou com token errado respondem `403` em JSON `{"error": "..."}` — rotas administrativas abertas expõem dados e permitem exclusões anônimas — default: exigir o token (com `ADMIN_TOKEN` definido e o header correto, status e corpo iguais ao baseline).
3. `DELETE /api/users/:id` passa a apagar também matrículas e pagamentos do usuário numa transação, e o texto da resposta muda de "Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco." para "Usuário deletado." (status 200 mantido) — o texto antigo descreveria um estado que deixa de existir — default: cascata + novo texto.
4. Corpo de checkout com tipos inválidos (ex.: `card` numérico) passa a responder `400 "Bad Request"` em vez de derrubar o processo — a resposta atual é a queda do servidor — default: 400.
5. Corpos de erro existentes continuam em texto puro com os mesmos status e mensagens (sem normalização para JSON); erros inesperados respondem `500 "Erro interno do servidor"` em texto puro — default: manter texto puro.

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
