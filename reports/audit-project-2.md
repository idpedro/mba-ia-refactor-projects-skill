================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   JavaScript + Express 4 (SQLite em memória)
Files:   3 analyzed | ~180 lines of code

## Summary
CRITICAL: 4 | HIGH: 6 | MEDIUM: 5 | LOW: 5

## Findings

### [CRITICAL] Hardcoded credentials and secrets (AP-01)
File: src/utils.js:1-7
Description: O objeto `config` guarda `dbUser`, `dbPass: "senha_super_secreta_prod_123"`, `paymentGatewayKey: "pk_live_1234567890abcdef"` e `smtpUser` como literais no código-fonte. `AppManager.js:45` consome a chave do gateway.
Impact: Quem tem acesso ao repositório obtém a chave live do gateway de pagamento e as credenciais do banco. Os valores não mudam por ambiente.
Recommendation: P-01 — `src/config/index.js` lê `PAYMENT_GATEWAY_KEY`, `ADMIN_TOKEN` e demais valores de `process.env`, sem default secreto. Adicionar `.env.example`.

### [CRITICAL] God class / God module (AP-03)
File: src/AppManager.js:4-139
Description: `AppManager` abre a conexão (`new sqlite3.Database(':memory:')`, linha 7), cria o schema e as seeds (`initDb`, 10-23), registra as 3 rotas (`setupRoutes`, 25-138), executa SQL, decide o pagamento e agrega o relatório financeiro.
Impact: Nada pode ser testado isoladamente. Qualquer mudança em checkout, relatório ou usuários mexe na mesma classe.
Recommendation: P-03 — dividir em `src/database/` (connection, schema), `src/models/` (course, user, enrollment, payment, auditLog), `src/services/` (payment, report, password), `src/controllers/`, `src/routes/` e `src/app.js` como composition root.

### [CRITICAL] Plaintext or weak password storage (AP-05)
File: src/utils.js:17-23; src/AppManager.js:18, 68-69
Description: `badCrypto` concatena 10000 vezes os 2 primeiros caracteres do base64 da senha e corta em 10 caracteres. O resultado é determinístico, sem salt, e tem espaço de busca minúsculo. O checkout grava esse valor em `users.pass` (linha 69), com o default `"123456"` quando `pwd` não vem (linha 68). A seed insere a senha `'123'` em texto puro (linha 18).
Impact: As senhas ficam praticamente em claro. Todo usuário criado sem `pwd` compartilha a mesma senha.
Recommendation: P-04 — `src/services/password.service.js` com `scrypt` e salt aleatório (`salt:hash`). Hashear a senha da seed. Sem `pwd`, não definir senha padrão: gerar um segredo aleatório que ninguém conhece.

### [CRITICAL] Sensitive data exposure (AP-06)
File: src/AppManager.js:45
Description: `console.log(\`Processando cartão ${cc} na chave ${config.paymentGatewayKey}\`)` imprime o número completo do cartão e a chave live do gateway a cada checkout.
Impact: O PAN do cartão e a chave de produção vão para stdout e para qualquer agregador de logs.
Recommendation: P-05 — logar só os 4 últimos dígitos (`card.slice(-4)`) e nunca a chave, no `PaymentService` via `src/utils/logger.js`.

### [HIGH] Business logic in the controller / route (AP-07)
File: src/AppManager.js:28-78, 80-129
Description: O handler de `/api/checkout` (51 linhas) valida o payload, decide o pagamento (`cc.startsWith("4") ? "PAID" : "DENIED"`, linha 46), cria o usuário, a matrícula, o pagamento e o log de auditoria. O handler do relatório (50 linhas) soma `revenue` e monta `students` dentro da rota.
Impact: As regras de pagamento e de relatório só rodam dentro do Express, então não dá para testá-las nem reaproveitá-las.
Recommendation: P-06 — `CheckoutController` + `PaymentService.charge` e `ReportService.financialReport`. As rotas em `src/routes/*.routes.js` ficam com uma chamada cada.

### [HIGH] Tight coupling / no dependency injection (AP-08)
File: src/AppManager.js:7, 2; src/app.js:8-10
Description: O banco é criado dentro do construtor (`this.db = new sqlite3.Database(':memory:')`). `AppManager` importa direto `config`, `logAndCache` e `badCrypto` de `utils.js`, e `app.js` faz `new AppManager()` sem composition root.
Impact: Não dá para trocar o banco ou o gateway nos testes, e todas as dependências são concretas.
Recommendation: P-07 — `src/app.js` cria a conexão, os models, os services e os controllers e os injeta nas rotas.

### [HIGH] Mutable global state (AP-09)
File: src/utils.js:9-10, 12-15, 25; src/AppManager.js:2, 59
Description: `let globalCache = {}` é escrito por `logAndCache` a cada checkout (`last_checkout_${userId}`) e exportado. Nenhuma rota nem regra lê o valor: o grep de `globalCache` só encontra escritas e o export. `let totalRevenue = 0` é exportado e importado em `AppManager.js:2`, e nunca é lido nem escrito.
Impact: O cache cresce sem limite, é perdido no restart e difere por processo. `totalRevenue` é um contador morto que sugere um total que não existe.
Recommendation: P-08 — apagar `globalCache`, `logAndCache` e `totalRevenue`. Ninguém lê o estado, então ele não vira tabela. Manter o efeito real do checkout e um log `logger.info` do curso e do usuário. O grep de AP-09 deve ficar sem hits.

### [HIGH] Non-atomic multi-step writes and orphaned data (AP-10)
File: src/AppManager.js:50-57, 66-72, 131-136
Description: O checkout faz `INSERT` em enrollments, payments e audit_logs em callbacks aninhados, sem transação. Se o segundo `INSERT` falhar, a matrícula já está gravada sem pagamento. O usuário novo é inserido (linhas 69-71) antes da decisão de pagamento (46-48), então um cartão recusado deixa um usuário criado. `DELETE /api/users/:id` apaga só o usuário e responde que "as matrículas e pagamentos ficaram sujos".
Impact: Dados inconsistentes: matrículas sem pagamento, usuários de checkout recusado e enrollments/payments órfãos após o delete.
Recommendation: P-11 — conexão promisificada com `transaction()`. Cobrança primeiro, depois usuário, matrícula, pagamento e auditoria na mesma transação. O delete remove payments e enrollments do usuário e depois o usuário, na mesma transação.

### [HIGH] Missing authentication / authorization (AP-11)
File: src/AppManager.js:80, 131
Description: `GET /api/admin/financial-report` expõe nomes de alunos e receita por curso sem nenhuma verificação. `DELETE /api/users/:id` apaga qualquer usuário de forma anônima.
Impact: Qualquer cliente lê o relatório financeiro e remove contas.
Recommendation: P-16 — `src/middlewares/adminAuth.js` com token admin estático de `ADMIN_TOKEN` (comparação com `timingSafeEqual`), ativo por padrão e fail-closed. Aplicado às duas rotas em `src/routes/admin.routes.js` e `user.routes.js`. O checkout continua público.

### [HIGH] Debug mode and unsafe defaults in the entry point (AP-12)
File: src/app.js:12
Description: `app.listen(config.port, ...)` não passa host, então o Node escuta em todas as interfaces (`::`/`0.0.0.0`). Não há `HOST` configurável nem lista de origens CORS.
Impact: A API, incluindo as rotas administrativas, fica exposta na rede local por padrão.
Recommendation: P-01 — `config.host = process.env.HOST || '127.0.0.1'` passado ao `listen`. Expor em todas as interfaces exige `HOST=0.0.0.0`. Não há `cors` instalado, então nenhum header CORS é enviado e nenhuma origem é liberada.

### [MEDIUM] N+1 queries (AP-13)
File: src/AppManager.js:92, 104, 106
Description: O relatório roda uma query de enrollments por curso e, para cada matrícula, uma query de `users` e outra de `payments`. A ordem do array final também depende de qual callback termina primeiro (`report.push` nas linhas 96 e 119).
Impact: O número de queries cresce com cursos × matrículas, e a ordem do relatório não é determinística.
Recommendation: P-09 — `ReportService` com um único `JOIN` courses/enrollments/users/payments, agrupado em memória e ordenado por `courses.id`.

### [MEDIUM] Missing or inconsistent input validation (AP-15)
File: src/AppManager.js:29-35, 46, 132
Description: O checkout só testa a presença de `usr`, `eml`, `c_id` e `card`. `cc.startsWith` lança se `card` não for string (linha 46), `eml` não é validado como e-mail, `c_id` não é validado como inteiro e `req.body` pode ser `undefined`. `req.params.id` do delete não é validado.
Impact: Um payload malformado vira exceção ou erro 500, ou grava lixo.
Recommendation: P-12 — `src/validators/checkout.validator.js` e validação do `:id` numérico. Erros respondem 400 com as mesmas mensagens quando existirem.

### [MEDIUM] Scattered or leaky error handling (AP-16)
File: src/AppManager.js:38, 41, 49, 51, 55, 57, 70, 84, 93, 105, 107, 133
Description: Os erros viram `res.send("Erro DB")`, `"Erro Matrícula"` etc. em texto puro. Os callbacks das linhas 57, 93, 105, 107 e 133 ignoram `err`. Na linha 93, `enrollments.length` lança se a query falhar. Não existe middleware central de erro.
Impact: Falhas silenciosas e respostas inconsistentes. O relatório pode travar sem responder.
Recommendation: P-10 — `src/errors.js`, `src/middlewares/errorHandler.js` e `asyncHandler`. Mesmos status HTTP e mesmos textos de hoje, em texto puro; erro inesperado responde 500 `Erro interno` e o detalhe vai só para o log.

### [MEDIUM] Deprecated APIs (AP-17)
File: src/AppManager.js:37-63, 83-128
Description: O driver sqlite3 é usado em callbacks aninhados até 5 níveis no checkout e no relatório, com contadores manuais (`coursesPending`, `enrPending`).
Impact: É o que esconde os bugs de AP-10 e AP-16.
Recommendation: P-11 — envolver `run/get/all` em Promises (`src/database/connection.js`) e usar `async/await`.

### [MEDIUM] Configuration in code instead of a config module (AP-18)
File: src/utils.js:6; src/AppManager.js:7
Description: `port: 3000` e o caminho do banco `':memory:'` são literais em `utils.js` e no construtor de `AppManager`.
Impact: Porta e banco não mudam por ambiente.
Recommendation: P-01 — `src/config/index.js` com `PORT`, `HOST`, `DB_PATH` (default `:memory:`) e `.env.example`.

### [LOW] Magic numbers and strings (AP-19)
File: src/utils.js:19-22; src/AppManager.js:46, 48, 68, 108
Description: Os literais `10000`, `2` e `10` em `badCrypto`, o prefixo de cartão `"4"`, os status `"PAID"`/`"DENIED"` comparados inline e a senha padrão `"123456"` não têm nome.
Impact: As regras ficam implícitas e quem lê não sabe a intenção.
Recommendation: P-14 — constantes `PAYMENT_STATUS` e `APPROVED_CARD_PREFIX` em `payment.service.js`, e parâmetros do scrypt no `password.service.js`.

### [LOW] Poor naming (AP-20)
File: src/AppManager.js:29-33, 43; src/utils.js:12, 17
Description: As variáveis `u`, `e`, `p`, `cid`, `cc` e `c`, a função `processPaymentAndEnroll`, a classe `AppManager`, e as funções `badCrypto` e `logAndCache` (esta faz duas coisas) têm nomes pouco claros. Os campos de request `usr`, `eml`, `pwd`, `c_id` também.
Impact: Dificulta a leitura. Os nomes dos campos de request fazem parte do contrato.
Recommendation: P-14 — renomear só as variáveis internas (`name`, `email`, `password`, `courseId`, `card`) via destructuring. Os campos de request continuam `usr`, `eml`, `pwd`, `c_id`, `card`.

### [LOW] Unused imports and dead code (AP-21)
File: src/AppManager.js:2; src/utils.js:3-5, 10, 25
Description: `totalRevenue` é importado e nunca usado, `globalCache` é exportado e nunca lido, e `dbUser`, `dbPass` e `smtpUser` do `config` nunca são referenciados. O parâmetro `err` nas linhas 57 e 133 não é usado.
Impact: Ruído que sugere funcionalidades inexistentes.
Recommendation: Apagar. O estado é tratado em AP-09 (P-08); as chaves de config sem uso não voltam para o novo `config`.

### [LOW] Print-debugging instead of logging (AP-22)
File: src/AppManager.js:45; src/utils.js:13; src/app.js:13
Description: `console.log` é o único mecanismo de log (checkout, cache e banner de boot).
Impact: Sem níveis e sem formato padronizado.
Recommendation: P-15 — `src/utils/logger.js` com níveis, configurado por `LOG_LEVEL`.

### [LOW] Verbose control flow (AP-23)
File: src/AppManager.js:86, 98, 117-121
Description: Contadores manuais (`coursesPending--`, `enrPending--`) controlam o fim do relatório, no lugar de `Promise.all`/agrupamento.
Impact: Código frágil: um curso sem matrículas ou um erro silencioso trava a resposta.
Recommendation: P-14 — o `JOIN` do P-09 elimina os contadores.

================================
Total: 20 findings
================================

## Decisions requiring approval
1. Autenticação (P-16): `GET /api/admin/financial-report` e `DELETE /api/users/:id` passam a exigir `Authorization: Bearer <ADMIN_TOKEN>`. Sem token ou com token inválido a resposta é `401`. O checkout continua público. — o projeto não tem login, então um token admin estático de config atende. — default: ativo sem nenhuma variável. Com `ADMIN_TOKEN` vazio as duas rotas respondem `401` a todos (fail closed). O token é definido por `ADMIN_TOKEN` e documentado no README.
2. Formato do hash de senha — `badCrypto` (10 caracteres) é substituído por `scrypt` (`salt:hash`). — default: aplicar. A seed passa a gravar hash. Nenhum endpoint lê a senha, então nenhuma resposta muda.
3. Checkout atômico e ordem das etapas — a cobrança é decidida antes de criar o usuário, e enrollment, payment e audit_log entram numa transação. — default: aplicar. Um cartão recusado continua respondendo `400 "Pagamento recusado"`, mas deixa de criar o usuário.
4. `DELETE /api/users/:id` remove também payments e enrollments do usuário, numa transação. — default: aplicar, mantendo `200` e trocando o texto (que dizia "ficaram sujos") por uma mensagem de que os dados relacionados foram removidos.
5. Ordem do relatório financeiro — passa a ser determinística, por `courses.id`. — default: aplicar. As chaves `course`, `revenue` e `students[].student/paid` não mudam.
6. Estado em memória — `globalCache`, `logAndCache` e `totalRevenue` são apagados, porque nada os lê (P-08). — default: apagar. Nenhuma resposta muda. O trecho `last_checkout_*` deixa de existir e o checkout registra um `logger.info`.
7. Bind e CORS — o servidor passa a escutar em `127.0.0.1` por padrão (`HOST=0.0.0.0` para expor) e nenhuma origem CORS é liberada. — default: aplicar.
8. Erros — as respostas de erro em texto puro (`Bad Request`, `Curso não encontrado`, `Pagamento recusado`) continuam em texto puro, com os mesmos textos e status, porque fazem parte do contrato dos clientes. Erros inesperados respondem `500` com o texto `Erro interno`, também em texto puro, e o detalhe vai só para o log. As respostas de sucesso não mudam. — default: aplicar.

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
