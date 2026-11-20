================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   JavaScript + Express 4 (SQLite in-memory via sqlite3)
Files:   3 analyzed | ~180 lines of code

## Summary
CRITICAL: 5 | HIGH: 6 | MEDIUM: 6 | LOW: 5

## Findings

### [CRITICAL] Hardcoded credentials and secrets (AP-01)
File: src/utils.js:2-5, src/AppManager.js:18, 68
Description: O objeto `config` declara literais `dbUser: "admin_master"`, `dbPass: "senha_super_secreta_prod_123"`, `paymentGatewayKey: "pk_live_1234567890abcdef"` e `smtpUser`. O seed insere o usuário Leonan com a senha literal `'123'` (AppManager.js:18), e o checkout atribui a senha padrão `"123456"` a qualquer conta criada sem `pwd` (AppManager.js:68).
Impact: Quem lê o repositório obtém a chave live do gateway e a senha do banco de produção. O usuário semeado e toda conta criada sem `pwd` têm senhas conhecidas publicamente.
Recommendation: P-01 + P-16. `dbUser`, `dbPass`, `smtpUser` e `paymentGatewayKey` são removidos, porque nenhum código real os usa (a chave só aparece num `console.log` e o pagamento é simulado). A senha do seed vem de `SEED_USER_PASSWORD` ou é gerada e impressa uma vez no boot. Uma conta criada sem `pwd` recebe uma senha aleatória que não é divulgada. A configuração fica em `src/config/index.js`, o seed em `src/database/seed.js` e as variáveis são listadas em `.env.example`.
Verification: (1) `grep -rnE "senha_super_secreta|pk_live|admin_master|dbPass|smtpUser|'123'|\"123456\"" src` → nenhum resultado; (2) boot sem variáveis + um checkout → o log não contém `pk_live`; (3) SQL `SELECT pass FROM users WHERE email='leonan@fullcycle.com.br'` → não é `'123'` e verifica contra a senha impressa no boot; (4) checkout anônimo sem `pwd` com e-mail novo e depois um checkout com o mesmo e-mail e `pwd: "123456"` → `403`; (5) upgrade path: N/A para um banco criado pelo código original, que só usa `':memory:'`. Mesmo assim, o schema e o seed originais são reproduzidos num arquivo e o app refatorado sobe nele (`DB_PATH`) → a senha `'123'` do Leonan é substituída e o log informa a troca.

### [CRITICAL] God class / God module (AP-03)
File: src/AppManager.js:4-139
Description: A classe `AppManager` abre a conexão (`new sqlite3.Database(':memory:')`, linha 7), cria o schema e o seed (`initDb`, 10-23), registra as três rotas (`setupRoutes`, 25-138), executa todo o SQL, decide o pagamento e monta o relatório.
Impact: Nenhuma regra pode ser testada ou reutilizada isoladamente. Qualquer mudança mexe no arquivo que concentra infraestrutura, HTTP e domínio.
Recommendation: P-03. A classe é dividida em `src/database/{connection,schema,seed}.js`, `src/models/{user,course,enrollment,payment,auditLog}.model.js`, `src/services/{payment,report,password}.service.js`, `src/controllers/{checkout,report,user}.controller.js`, `src/routes/*.routes.js` e `src/app.js` como composition root.
Verification: (1) `ls src/AppManager.js` → arquivo inexistente; (2) `grep -rnE "CREATE TABLE|INSERT INTO|SELECT " src/routes src/controllers` → nenhum resultado; (3) os 3 endpoints retornam o status e as chaves do baseline.

### [CRITICAL] Unprotected destructive or arbitrary-execution endpoint (AP-04)
File: src/AppManager.js:131-137
Description: `DELETE /api/users/:id` executa `DELETE FROM users WHERE id = ?` para qualquer requisição, sem verificar identidade nem papel.
Impact: Qualquer cliente anônimo apaga qualquer usuário, inclusive em massa, iterando os ids.
Recommendation: P-05 + P-16. A rota continua existindo e exige o papel admin (`src/routes/user.routes.js` com o middleware `requireAdmin`). O efeito é preservado para admins.
Verification: (1) `DELETE /api/users/1` anônimo → `401`, e o usuário 1 continua existindo (aparece no relatório como Leonan); (2) usuário comum (Basic `gui@fullcycle.com.br:senhaforte`) → `403`, e o usuário 1 continua existindo; (3) admin → `200`.

### [CRITICAL] Plaintext or weak password storage (AP-05)
File: src/utils.js:17-23, src/AppManager.js:18, 68
Description: `badCrypto` repete os 2 primeiros caracteres do base64 da senha e corta em 10 caracteres. Senhas com o mesmo prefixo geram o mesmo "hash" e não há salt. O seed grava `'123'` em texto puro (linha 18).
Impact: Senhas são reversíveis ou colidem trivialmente. Um vazamento da tabela `users` expõe as senhas (ou um prefixo delas).
Recommendation: P-04. `src/services/password.service.js` usa `crypto.scryptSync` com salt aleatório (formato `salt:hash`) e `timingSafeEqual`. O seed grava com hash. No boot, qualquer valor que não esteja no formato novo é substituído por uma senha nova (do env ou gerada e impressa).
Verification: (1) SQL `SELECT pass FROM users` → todo valor casa com `^[0-9a-f]{32}:[0-9a-f]{128}$` (usuário semeado e usuário criado por checkout); (2) duas contas com a mesma senha → valores armazenados diferentes; (3) Basic com a senha certa → aceito, com a senha errada → `401`; (4) `grep -rn "badCrypto\|base64" src` → nenhum resultado; (5) upgrade path: o schema e o seed originais reproduzidos em arquivo (ver AP-01) → após o boot, toda `pass` está no formato `salt:hash`.

### [CRITICAL] Sensitive data exposure (AP-06)
File: src/AppManager.js:45
Description: `console.log(\`Processando cartão ${cc} na chave ${config.paymentGatewayKey}\`)` grava o número completo do cartão e a chave do gateway no log a cada checkout.
Impact: Qualquer pessoa com acesso aos logs obtém números de cartão completos (violação PCI) e a chave live.
Recommendation: P-05. O log passa a mostrar só os 4 últimos dígitos (`src/services/payment.service.js`, via `src/utils/logger.js`).
Verification: (1) `POST /api/checkout` com `card: "4111222233334444"` → o log do servidor não contém `4111222233334444` nem `pk_live`, apenas o final `4444`.

### [HIGH] Business logic in the controller / route (AP-07)
File: src/AppManager.js:28-78, 80-129
Description: O handler de checkout decide o pagamento (`cc.startsWith("4") ? "PAID" : "DENIED"`, linha 46), cria o usuário, a matrícula, o pagamento e a auditoria. O handler do relatório agrega a receita (`courseData.revenue += payment.amount`, linha 109). Os dois têm mais de 40 linhas.
Impact: A regra de aprovação e a de cálculo de receita só podem ser exercidas via HTTP e não podem ser trocadas, por exemplo por um gateway real.
Recommendation: P-06. A decisão de pagamento vai para `PaymentService.charge()` e a agregação para `ReportService.financialReport()`. O orquestramento fica em `CheckoutController.checkout()`. As rotas apenas fazem o parse e respondem.
Verification: (1) `grep -rnE "startsWith|revenue" src/routes` → nenhum resultado; (2) checkout com cartão iniciado em 4 → `200 {msg, enrollment_id}`, com cartão iniciado em 5 → `400 "Pagamento recusado"`; (3) relatório (admin) → mesma estrutura `[{course, revenue, students[{student, paid}]}]` do baseline.

### [HIGH] Tight coupling / no dependency injection (AP-08)
File: src/AppManager.js:7, 26, src/app.js:8-10
Description: O construtor cria a conexão concreta (`new sqlite3.Database(':memory:')`). Os handlers usam `this.db`/`self.db` diretamente. `app.js` não tem composition root: instancia o `AppManager` e chama o `listen` no topo do módulo.
Impact: Não dá para trocar o banco, injetar dublês em testes ou subir o app sem abrir a porta.
Recommendation: P-07. `src/app.js` exporta `createApp(config)`, que cria a conexão, os models, os services e os controllers e os injeta nos routers. O `listen` só ocorre quando o arquivo é executado diretamente.
Verification: (1) `grep -rn "new sqlite3.Database" src` → apenas `src/database/connection.js`; (2) `grep -rnE "require\('sqlite3'\)|require\('\.\./database" src/controllers src/routes src/services` → nenhum resultado; (3) `node -e "require('./src/app').createApp"` carrega sem abrir porta.

### [HIGH] Mutable global state (AP-09)
File: src/utils.js:9-10, 12-15, src/AppManager.js:59
Description: `let globalCache = {}` recebe uma escrita por checkout (`logAndCache(\`last_checkout_${userId}\`, course.title)`) e nunca é lido. `let totalRevenue = 0` é exportado e nunca é usado.
Impact: Memória cresce sem limite a cada checkout, o dado se perde no restart e diverge entre processos.
Recommendation: P-08. Nada lê o estado, então ele é apagado junto com as escritas. O efeito real (a matrícula e a auditoria) permanece.
Verification: (1) o grep AP-09 do catálogo (`^(const|let|var) [A-Za-z_$]+ = (\{\}|\[\]|0|new (Map|Set)\()|^(let|var) |^\s*global |this\.[a-zA-Z_]+ = (new (Map|Set)\(|\{\}|\[\])`) em `src` → nenhum resultado de estado mutável; (2) `grep -rn "globalCache\|totalRevenue" src` → nenhum resultado.

### [HIGH] Non-atomic multi-step writes and orphaned data (AP-10)
File: src/AppManager.js:50-63, 66-72, 131-137
Description: Matrícula, pagamento e auditoria são três `INSERT` em callbacks aninhados, sem transação (50-63). O usuário novo é inserido (69) antes da decisão do pagamento, que pode recusar (48). `DELETE FROM users` (133) deixa `enrollments` e `payments` órfãos, e a própria resposta admite: "as matrículas e pagamentos ficaram sujos no banco".
Impact: Uma falha entre os passos deixa a matrícula sem pagamento. Um pagamento recusado deixa um usuário criado. O delete gera alunos "Unknown" e receita de alunos inexistentes no relatório.
Recommendation: P-11. Driver promisificado, uma fila de transações sobre a conexão única e a decisão de pagamento antes de qualquer escrita. Usuário, matrícula, pagamento e auditoria ficam em uma transação (`src/controllers/checkout.controller.js`). O delete remove pagamentos, matrículas e o usuário na mesma transação (`src/models/user.model.js`).
Verification: (1) checkout anônimo com e-mail novo e cartão `5…` → `400`; depois o mesmo e-mail com outra `pwd` e cartão `4…` → `200` (o usuário não foi criado na recusa); SQL `SELECT COUNT(*) FROM users WHERE email=?` após a recusa → 0; (2) falha forçada no INSERT de `payments` (in-process) → `500`, e a contagem de `enrollments`/`users` é igual à de antes; (3) admin `DELETE /api/users/1` e depois o relatório (admin) → nenhum aluno `Unknown`; SQL de órfãos `SELECT COUNT(*) FROM enrollments WHERE user_id NOT IN (SELECT id FROM users)` → 0, e o mesmo para `payments` sem matrícula → 0.

### [HIGH] Missing authentication / authorization (AP-11)
File: src/AppManager.js:40, 66-75, 80, 131
Description: `GET /api/admin/financial-report` expõe nomes de alunos e receita para qualquer um. `DELETE /api/users/:id` não verifica nada. No checkout, um `eml` já existente reaproveita o usuário (`processPaymentAndEnroll(user.id)`, linha 74) sem checar `pwd`, então o dono da matrícula vem do corpo da requisição.
Impact: Um anônimo lê o relatório financeiro, apaga contas e cria matrículas em nome de outro usuário (basta saber o e-mail).
Recommendation: P-16, ativo por padrão. HTTP Basic (`email:senha`) é verificado contra os hashes, e a nova coluna `role` é criada com migração idempotente. A conta admin semeada (`admin@fullcycle.com.br`) recebe a senha de `ADMIN_PASSWORD` ou uma senha gerada e impressa uma vez. Relatório e delete exigem admin. No checkout com e-mail existente, o chamador precisa provar ser o dono (a `pwd` correta, ou Basic do próprio usuário) ou ser admin; caso contrário, `403`. Middleware em `src/middlewares/auth.js`.
Verification: (1) `GET /api/admin/financial-report` anônimo → `401`; usuário comum (Gui) → `403`; admin → `200`, com as chaves do baseline; (2) `DELETE /api/users/1` anônimo → `401`, Gui → `403`, admin → `200`; (3) usuário A criando um registro de B: checkout anônimo com `eml: leonan@fullcycle.com.br` e `pwd` errada → `403`, sem nova matrícula; Basic do Gui com `eml` do Leonan → `403`; (4) o dono: checkout com `eml` do Leonan e a senha impressa no boot → `200`; (5) Basic com senha errada → `401`.

### [HIGH] Debug mode and unsafe defaults in the entry point (AP-12)
File: src/app.js:12
Description: `app.listen(config.port, ...)` não passa host, então o Express escuta em todas as interfaces (`*:3000`).
Impact: A API, incluindo as rotas administrativas, fica exposta em qualquer rede à qual a máquina esteja conectada.
Recommendation: P-01. `HOST` vem do config com padrão `127.0.0.1`; `HOST=0.0.0.0` é opt-in explícito. Não há CORS, debug nem stack traces (ver AP-16).
Verification: (1) `ss -ltnp | grep 3000` no boot sem variáveis → `127.0.0.1:3000`, sem `*:3000` ou `0.0.0.0`; (2) preflight `OPTIONS /api/checkout` com `Origin: http://evil.example` → sem `Access-Control-Allow-Origin`.

### [MEDIUM] N+1 queries (AP-13)
File: src/AppManager.js:83-106
Description: Para cada curso, roda `SELECT * FROM enrollments WHERE course_id = ?`. Para cada matrícula, roda `SELECT name, email FROM users WHERE id = ?` e `SELECT amount, status FROM payments WHERE enrollment_id = ?`.
Impact: O relatório executa 1 + C + 2·M queries e degrada linearmente com o número de matrículas.
Recommendation: P-09. Um único `SELECT` com `LEFT JOIN` entre courses, enrollments, users e payments, agrupado em memória em `src/services/report.service.js`, preservando a ordem e o formato.
Verification: (1) in-process, com trace do driver: o relatório com 2 matrículas e com 7 matrículas executa o mesmo número de statements (1).

### [MEDIUM] Duplicated logic (AP-14)
File: src/AppManager.js:96-98, 117-121
Description: O bloco de conclusão `report.push(courseData); coursesPending--; if (coursesPending === 0) res.json(report);` está copiado nos dois ramos do callback.
Impact: Uma correção num ramo não chega ao outro, e uma divergência entre eles faz a resposta nunca ser enviada ou ser enviada duas vezes.
Recommendation: P-12. A agregação passa a ser uma função única sobre o resultado do JOIN (`ReportService.financialReport`).
Verification: (1) `grep -rn "coursesPending\|enrPending" src` → nenhum resultado; (2) o relatório (admin) mantém as chaves do baseline, incluindo cursos sem matrícula (`students: []`).

### [MEDIUM] Missing or inconsistent input validation (AP-15)
File: src/AppManager.js:35, 40, 46, 69, src/AppManager.js:12 (schema)
Description: Só a presença dos campos é checada. `card` numérico faz `cc.startsWith` lançar `TypeError` dentro do callback do sqlite e derrubar o processo. `eml` não tem o formato validado e é comparado de forma case-sensitive. `users.email` não tem constraint `UNIQUE`, então checkouts simultâneos com e-mail novo criam usuários duplicados. `c_id` e `usr` não têm tipo checado.
Impact: Uma única requisição com `card: 4111` derruba a API. E-mails duplicados (ou com caixa diferente) geram contas paralelas.
Recommendation: P-12. Um validador único em `src/validators/checkout.validator.js`: strings não vazias, e-mail com formato válido normalizado para minúsculas, `c_id` inteiro positivo finito e `card` só com 12 a 19 dígitos; violações → `400`. Índice `CREATE UNIQUE INDEX IF NOT EXISTS ... ON users(email COLLATE NOCASE)` e leitura e escrita do usuário dentro da mesma transação serializada.
Verification: (1) checkout com `card: 4111` (número) → `400`, e em seguida qualquer requisição ainda é respondida; (2) `eml: "nao-e-email"` → `400`; `c_id: "abc"`, `c_id: 1.5`, `usr: 123` → `400`; (3) 20 checkouts simultâneos com o mesmo e-mail novo (metade em maiúsculas) e a mesma `pwd` → SQL `SELECT COUNT(*) FROM users WHERE lower(email)=?` → 1; (4) upgrade path: o schema original reproduzido em arquivo → após o boot, `PRAGMA index_list(users)` mostra o índice único.

### [MEDIUM] Scattered or leaky error handling (AP-16)
File: src/AppManager.js:38, 41, 51, 55, 57, 70, 84, 92, 104, 106, 133
Description: Cada callback trata o erro à sua maneira (`res.status(500).send("Erro DB")`) ou o ignora: na linha 92, `enrollments.length` com `err` lança exceção; nas linhas 57, 104, 106 e 133, `err` é descartado e na 133 a resposta diz "deletado" mesmo com falha. Não existe middleware de erro, e um JSON malformado recebe a página HTML padrão do Express com stack trace.
Impact: Erros de banco derrubam o processo ou são mascarados como sucesso. Stack traces com caminhos internos vazam para o cliente.
Recommendation: P-10. Erros de domínio (`src/errors.js`), `asyncHandler` e um único `src/middlewares/errorHandler.js` que responde em texto puro, preservando o formato original: o status do erro com a mensagem, ou `500 "Erro interno do servidor"`, com o detalhe só no log.
Verification: (1) `POST /api/checkout` com corpo `{malformado` → `400`, corpo em texto sem `at ` nem caminhos de arquivo; (2) erro de banco forçado (in-process, tabela renomeada) no relatório e no delete → `500 "Erro interno do servidor"`, stack só no log, e o servidor segue respondendo.

### [MEDIUM] Deprecated APIs (AP-17)
File: src/AppManager.js:37-77, 83-128, 133
Description: A API de callbacks do sqlite3 está aninhada em até 6 níveis no checkout e 4 no relatório (`db.get(..., (err, course) => { db.get(..., (err, user) => { db.run(..., function(err) { ...`).
Impact: O fluxo de erro fica ilegível e propenso a respostas duplicadas ou perdidas, e impede o uso de `try/catch` e transações.
Recommendation: P-11/P-13. Wrappers `run/get/all` promisificados em `src/database/connection.js`, com `async/await` em todo o resto.
Verification: (1) `grep -rnE "\.(run|get|all)\(.*(function ?\(|=>)" src --exclude=connection.js` → nenhum resultado; (2) `node --throw-deprecation src/app.js` sobe sem erro.

### [MEDIUM] Configuration in code instead of a config module (AP-18)
File: src/utils.js:6, src/AppManager.js:7
Description: `port: 3000` está dentro de `utils.js` e o caminho do banco `':memory:'` está no construtor do `AppManager`.
Impact: Não é possível mudar a porta ou usar um banco em arquivo por ambiente sem editar o código.
Recommendation: P-01. `src/config/index.js` lê `PORT`, `HOST`, `DB_PATH`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` e `SEED_USER_PASSWORD`, com padrões seguros (exceto para segredos).
Verification: (1) `grep -rnE "3000|:memory:" src --exclude-dir=config` → nenhum resultado; (2) o boot sem variáveis escuta em `127.0.0.1:3000`.

### [LOW] Magic numbers and strings (AP-19)
File: src/AppManager.js:21, 46, 108, src/utils.js:19, 22
Description: `startsWith("4")` como regra de aprovação, os status `'PAID'`/`"DENIED"` comparados inline e o laço `10000` e o corte `10` dentro de `badCrypto`.
Impact: As regras ficam implícitas e espalhadas, e uma mudança de status exige caçar strings.
Recommendation: P-14. `PAYMENT_STATUS` e `APPROVED_CARD_PREFIX` ficam em `src/services/payment.service.js`. `badCrypto` é removido (AP-05).
Verification: (1) `grep -rnE "startsWith\([\"']4[\"']\)|[=!]== *[\"'](PAID|DENIED)[\"']|10000" src` → nenhum resultado.

### [LOW] Poor naming (AP-20)
File: src/AppManager.js:4, 26, 29-33, 89, 102, src/utils.js:12, 17
Description: Variáveis `u`, `e`, `p`, `cid`, `cc`, `c`, `enr`, `self`. Nomes enganosos: `badCrypto`, `logAndCache` (faz duas coisas) e `AppManager`.
Impact: Leitura e busca difíceis, e o nome não revela a intenção.
Recommendation: P-14. `const { usr: name, eml: email, pwd: password, c_id: courseId, card } = body`. Os campos públicos do request se mantêm.
Verification: (1) `grep -rnE "\blet (u|e|p|cid|cc)\b|\b(badCrypto|logAndCache|AppManager)\b|\bconst self\b" src` → nenhum resultado.

### [LOW] Unused imports and dead code (AP-21)
File: src/AppManager.js:2, src/utils.js:2-5, 10, 25
Description: `totalRevenue` é importado e nunca usado. `globalCache` é exportado e nunca lido. `config.dbUser`, `dbPass` e `smtpUser` nunca são referenciados.
Impact: Ruído que sugere funcionalidades inexistentes e mantém segredos vivos no código.
Recommendation: Apagar.
Verification: (1) `grep -rnE "totalRevenue|globalCache|dbUser|dbPass|smtpUser" src` → nenhum resultado.

### [LOW] Print-debugging instead of logging (AP-22)
File: src/app.js:13, src/utils.js:13, src/AppManager.js:45
Description: `console.log` é o único mecanismo de log (banner de boot, "[LOG] Salvando no cache" e o processamento do cartão).
Impact: Sem níveis nem timestamp, não é possível filtrar e separar erros (stderr) de informação.
Recommendation: P-15. `src/utils/logger.js` com `info/warn/error`, timestamp e nível, que é o único ponto que chama `console`.
Verification: (1) `grep -rn "console\." src --exclude=logger.js` → nenhum resultado.

### [LOW] Verbose control flow (AP-23)
File: src/AppManager.js:86-87, 93-100, 117-122
Description: Contadores manuais `coursesPending--`/`enrPending--` controlam quando responder, em vez de aguardar promessas ou agregar o resultado de uma consulta.
Impact: Um contador fora de sincronia (um erro ignorado) deixa a requisição pendurada para sempre.
Recommendation: P-14 + P-09. Uma consulta única com a agregação num laço simples sobre as linhas.
Verification: (1) `grep -rnE "Pending(--|\+\+| *-= *1)" src` → nenhum resultado.

================================
Total: 22 findings
================================

## Decisions requiring approval
1. Autenticação via HTTP Basic (`Authorization: Basic base64(email:senha)`), verificada contra os hashes. Nova coluna `users.role` e conta admin semeada `admin@fullcycle.com.br`, com senha de `ADMIN_PASSWORD` ou gerada e impressa uma vez no boot. — Não existe rota de login e as rotas admin precisam distinguir anônimo/comum/admin. — default: `GET /api/admin/financial-report` e `DELETE /api/users/:id` exigem admin (`401` sem credenciais ou com credenciais inválidas, `403` para usuário comum). `POST /api/checkout` continua público para e-mails novos.
2. Checkout com e-mail já cadastrado exige provar a posse: `pwd` correta no corpo, ou Basic do próprio usuário, ou Basic de admin. — Hoje qualquer um matricula outra pessoa sabendo só o e-mail. — default: sem prova → `403 "Acesso negado"` em texto puro. Os exemplos do `api.http` (e-mails novos) não mudam.
3. Senha do seed do Leonan vem de `SEED_USER_PASSWORD` ou é gerada e impressa uma vez no boot. Senhas passam a ser `scrypt` no formato `salt:hash`. — Hoje é `'123'` em texto puro. — default: o banco é em memória, então não há hashes antigos a preservar. Num `DB_PATH` em arquivo, qualquer valor fora do formato novo é substituído por uma senha nova (env ou gerada), e o log informa a troca.
4. Checkout de e-mail novo sem `pwd` cria a conta com uma senha aleatória não divulgada (antes era `"123456"`). — Elimina a credencial padrão conhecida. — default: a resposta continua `200 {msg, enrollment_id}`.
5. `DELETE /api/users/:id` passa a apagar também as matrículas e os pagamentos do usuário, na mesma transação. A resposta muda para `"Usuário deletado."` (texto puro, `200`). — Elimina os órfãos. — default: o relatório deixa de listar o aluno removido e a receita desse aluno sai do total. O registro em `audit_logs` (que não referencia usuário) é mantido.
6. Validação de entrada do checkout. — `card` numérico derruba o processo e e-mails duplicados são aceitos. — default: `400` em texto puro para `usr` não-string ou vazio, `eml` em formato inválido, `c_id` que não seja inteiro positivo e `card` que não tenha 12 a 19 dígitos. Os campos ausentes mantêm `400 "Bad Request"`. E-mail normalizado para minúsculas e único (case-insensitive): `GUI@…` e `gui@…` são a mesma conta.
7. Tratamento de erros centralizado mantendo o formato texto puro e os status atuais. — Hoje há stack trace em HTML para JSON malformado e erros ignorados. — default: erros inesperados → `500 "Erro interno do servidor"`, JSON malformado → `400 "Bad Request"`, e o detalhe vai só para o log.
8. O servidor escuta em `127.0.0.1` por padrão; expor em todas as interfaces exige `HOST=0.0.0.0`. — default: `npm start` sem variáveis continua funcionando localmente na porta 3000.
9. `paymentGatewayKey`, `dbUser`, `dbPass` e `smtpUser` são removidos (nenhum é usado de fato; o pagamento é simulado). O log do checkout mostra só os 4 últimos dígitos do cartão. — default: nenhuma variável nova é necessária para subir.
