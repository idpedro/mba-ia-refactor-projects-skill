================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask 3.1.1 (SQLite, driver sqlite3 puro)
Files:   4 analyzed | ~780 lines of code

## Summary
CRITICAL: 6 | HIGH: 6 | MEDIUM: 5 | LOW: 5

## Findings

### [CRITICAL] Hardcoded credentials and secrets (AP-01)
File: app.py:7, controllers.py:289
Description: `app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"` está escrito no código, e o mesmo valor é devolvido no JSON de `health_check` (`"secret_key": ...`), junto com `db_path` e `debug`.
Impact: qualquer pessoa com acesso ao repositório ou a `GET /health` obtém a chave que assina sessões. O endpoint é anônimo.
Recommendation: P-01 — ler `SECRET_KEY` do ambiente em `config.py`, gerar uma chave aleatória por boot quando ausente, e remover `secret_key`, `db_path` e `debug` da resposta de `/health`.

### [CRITICAL] SQL injection (AP-02)
File: models.py:28, 47-50, 57-61, 68, 92, 110, 126-129, 140, 148-151, 155, 157-166, 174, 188, 192, 220, 224, 279-281, 289-297
Description: todas as consultas são montadas por concatenação (`"SELECT * FROM produtos WHERE id = " + str(id)`, `"... WHERE email = '" + email + "' AND senha = '" + senha + "'"`, `"... LIKE '%" + termo + "%'"` em `buscar_produtos`). `str()` não sanitiza. `login_usuario` aceita `' OR '1'='1` como senha.
Impact: bypass de login, leitura e alteração arbitrárias do banco por qualquer cliente anônimo.
Recommendation: P-02 — consultas parametrizadas (`?`) em todas as funções de `models/`.

### [CRITICAL] God class / God module (AP-03)
File: app.py:32-78, controllers.py:264-292, models.py:1-314
Description: `app.py` registra rotas, abre conexão e executa SQL em `reset_database` e `executar_query`. `health_check` roda SQL dentro do controller. `models.py` mistura produtos, usuários, pedidos e relatório (314 linhas, 4 domínios) com regra de preço, desconto e estoque. `database.py` junta conexão, schema e seed.
Impact: nada pode ser testado isoladamente e qualquer mudança de domínio toca os mesmos arquivos.
Recommendation: P-03 — separar em `config`, `database`, `models/` (um por entidade), `services/`, `controllers/`, `routes/`, `middlewares/` e uma app factory.

### [CRITICAL] Unprotected destructive or arbitrary-execution endpoint (AP-04)
File: app.py:47-57, 59-78
Description: `POST /admin/reset-db` apaga `itens_pedido`, `pedidos`, `produtos` e `usuarios` sem autenticação. `POST /admin/query` executa `cursor.execute(dados["sql"])` com o SQL vindo do corpo, e também aceita DML e DDL.
Impact: qualquer cliente anônimo apaga ou lê o banco inteiro, incluindo as senhas.
Recommendation: P-05 e P-16 — manter as duas rotas, exigir papel admin (401 sem credencial, 403 para não-admin). `/admin/query` aceita apenas uma instrução `SELECT`, em modo somente leitura.

### [CRITICAL] Plaintext or weak password storage (AP-05)
File: database.py:76-78, models.py:110, 126-129, controllers.py:155-160
Description: `criar_usuario` grava `senha` exatamente como veio do request. O seed insere `"admin123"`, `"123456"` e `"senha123"` em texto puro. `login_usuario` compara `senha = '<valor>'` direto no SQL.
Impact: um vazamento do banco expõe todas as senhas, e a conta admin tem senha conhecida e fraca.
Recommendation: P-04 — hash salgado (werkzeug `generate_password_hash`/`check_password_hash`) em `services/auth_service.py`. O seed grava hashes, e o login verifica o hash em Python.

### [CRITICAL] Sensitive data exposure (AP-06)
File: models.py:83, 99, controllers.py:165, 186, 289
Description: `get_todos_usuarios` e `get_usuario_por_id` incluem `"senha"` na resposta de `GET /usuarios` e `GET /usuarios/<id>`. `criar_usuario` e `login` devolvem `str(e)` ao cliente em caminhos de autenticação. `/health` devolve a chave secreta.
Impact: as senhas de todos os usuários (e o hash, após o P-04) ficam visíveis a qualquer cliente anônimo.
Recommendation: P-05 — serializar usuário sem `senha` (`models/usuario_model.py`) e mensagens genéricas nos erros de auth.

### [HIGH] Business logic in the controller / route (AP-07)
File: controllers.py:52-54, 208-210, 242-250, models.py:137-169, 256-262
Description: `criar_pedido` dispara `print("ENVIANDO EMAIL/SMS/PUSH ...")` dentro do handler. `atualizar_status_pedido` mantém a lista de status e as notificações no controller. As categorias válidas ficam inline em `criar_produto`. As faixas de desconto do relatório (`> 10000 → 10%`) e o cálculo de total do pedido estão em `models.py`, junto do SQL.
Impact: regras não testáveis sem HTTP ou banco, e duplicáveis por novos controllers.
Recommendation: P-06 — `services/pedido_service.py`, `services/relatorio_service.py`, `services/notification_service.py`. Controllers só parseiam a requisição e formatam a resposta.

### [HIGH] Tight coupling / no dependency injection (AP-08)
File: app.py:4, 49, 66, controllers.py:3, 266, models.py:1 (todas as funções chamam `get_db()`)
Description: controllers e models importam `get_db` diretamente, e `app.py` o chama dentro de handlers. Não existe app factory nem composition root, e o módulo `app` cria o `Flask` no import.
Impact: impossível trocar o banco (por exemplo, `:memory:` em teste) ou substituir serviços.
Recommendation: P-07 — `create_app()` em `app.py` como composition root, que cria a conexão e injeta repositórios e serviços nos controllers.

### [HIGH] Mutable global state (AP-09)
File: database.py:4, 8-10
Description: `db_connection` é global mutável, criado preguiçosamente via `global db_connection`, e compartilhado entre threads com `check_same_thread=False`. O módulo não tem nenhuma outra coleção em memória.
Impact: uma conexão para todas as requisições concorrentes sem lock. Uma exceção no meio de uma escrita deixa transação aberta para a próxima requisição.
Recommendation: P-08 — remover o singleton: conexão por requisição aberta e fechada pela app factory (`g`/`teardown_appcontext`). Não restam coleções de estado em processo para persistir.

### [HIGH] Non-atomic multi-step writes and orphaned data (AP-10)
File: models.py:133-169, 65-70, 275-283
Description: `criar_pedido` insere o pedido, os itens e baixa o estoque sem rollback em caso de exceção (a conexão global mantém a transação aberta), e o estoque lido na validação não é conferido de novo na escrita. `quantidade` negativa passa e aumenta o estoque. `deletar_produto` apaga o produto e deixa as linhas de `itens_pedido` apontando para um `produto_id` inexistente (o relatório depois mostra "Desconhecido").
Impact: pedidos parciais, estoque negativo ou inflado e histórico de pedidos órfão.
Recommendation: P-11 — transação única com `rollback` em falha e `UPDATE ... WHERE estoque >= ?` verificando `rowcount`; validação de `quantidade` inteira positiva; recusar a exclusão de produto referenciado por itens.

### [HIGH] Missing authentication / authorization (AP-11)
File: app.py:11-30, 47-78
Description: nenhuma das 19 rotas verifica credencial. `GET /usuarios`, `GET /pedidos`, `PUT /pedidos/<id>/status`, `POST/PUT/DELETE /produtos` e `GET /relatorios/vendas` respondem a qualquer anônimo. `/login` devolve só o usuário, sem token, então não há como o cliente provar quem é.
Impact: qualquer pessoa lê dados de todos os usuários, altera pedidos e catálogo, e consulta o faturamento.
Recommendation: P-16 — token assinado emitido em `/login`, `middlewares/auth.py` com `require_auth` e `require_admin`, ativo por padrão. Rotas públicas e papéis estão em "Decisions".

### [HIGH] Debug mode and unsafe defaults in the entry point (AP-12)
File: app.py:8, 9, 88
Description: `app.config["DEBUG"] = True` e `app.run(host="0.0.0.0", port=5000, debug=True)` expõem o debugger do Werkzeug (execução remota de código) em todas as interfaces. `CORS(app)` libera qualquer origem.
Impact: execução remota de código a partir da rede e chamadas cross-origin de qualquer site.
Recommendation: P-01 — padrões `DEBUG=false`, `HOST=127.0.0.1` e `CORS_ORIGINS` como lista explícita, todos lidos de `config.py`.

### [MEDIUM] N+1 queries (AP-13)
File: models.py:171-201, 203-233, 239-254
Description: `get_pedidos_usuario` e `get_todos_pedidos` rodam uma consulta de itens por pedido (`cursor2`) e outra de produto por item (`cursor3`). `relatorio_vendas` executa cinco `COUNT`/`SUM` separados sobre `pedidos`.
Impact: o número de consultas cresce com o número de pedidos e itens.
Recommendation: P-09 — um `JOIN` pedidos/itens/produtos agrupado em Python, e um único `SELECT` com `GROUP BY status` no relatório.

### [MEDIUM] Duplicated logic (AP-14)
File: controllers.py:30-50, 74-90, models.py:12-21, 31-40, 79-86, 95-102, 178-199, 211-231, 304-313
Description: a validação de nome, preço e estoque existe em `criar_produto` e, parcialmente, em `atualizar_produto`. O mapeamento linha → dict de produto aparece três vezes, o de usuário duas, e o de pedido com itens duas (idêntico em `get_pedidos_usuario` e `get_todos_pedidos`).
Impact: correções feitas em um lugar ficam de fora do outro (o update já não valida nome nem categoria).
Recommendation: P-12 — `controllers/validators.py` único para produto, e um `to_dict()` por model em `models/`.

### [MEDIUM] Missing or inconsistent input validation (AP-15)
File: controllers.py:26-35, 66-90, 118-121, 169-171, 239-240, models.py:144
Description: `preco < 0` com `preco` string gera 500. `atualizar_produto` não valida tamanho do nome nem categoria. `buscar_produtos` faz `float(preco_min)` sem tratar valor inválido (500). `login` e `atualizar_status_pedido` chamam `.get` num corpo que pode ser `None`. `criar_pedido` acessa `item["produto_id"]` e `item["quantidade"]` sem checar tipo ou presença.
Impact: entradas ruins viram 500 com texto de exceção em vez de 400.
Recommendation: P-12 — validators compartilhados em `controllers/validators.py`, aplicados em criar e atualizar.

### [MEDIUM] Scattered or leaky error handling (AP-16)
File: controllers.py:10-12, 21-22, 60-62, 95-96, 108-109, 125-126, 133-134, 143-144, 164-165, 185-186, 218-220, 226-227, 234-235, 254-255, 261-262, 291-292, app.py:77-78
Description: todo handler tem `try/except Exception` e devolve `{"erro": str(e)}` com 500, expondo texto interno (nomes de tabela, SQL). `/admin/query` também devolve `str(e)`.
Impact: vazamento de detalhes internos e formatos de erro diferentes por rota (`{"erro"}`, `{"status": "erro", "detalhes"}`).
Recommendation: P-10 — exceções de domínio em `errors.py` e um handler central em `middlewares/error_handler.py`, com corpo de erro único e genérico no 500.

### [MEDIUM] Configuration in code instead of a config module (AP-18)
File: database.py:5, app.py:88, controllers.py:285-288
Description: `db_path = "loja.db"`, porta `5000`, host, versão `"1.0.0"` e ambiente `"producao"` são literais espalhados em três módulos.
Impact: impossível configurar por ambiente sem editar o código.
Recommendation: P-01 — `config.py` lendo `DB_PATH`, `HOST`, `PORT`, `DEBUG`, `CORS_ORIGINS` do ambiente com padrões seguros, e `.env.example`.

### [LOW] Magic numbers and strings (AP-19)
File: controllers.py:47-52, 242, models.py:257-262
Description: limites de nome `2` e `200`, lista de categorias, lista de status do pedido, e faixas de desconto `10000/0.1`, `5000/0.05`, `1000/0.02` inline.
Impact: regras difíceis de localizar e alterar.
Recommendation: P-14 — constantes nomeadas (`CATEGORIAS_VALIDAS`, `STATUS_PEDIDO`, `FAIXAS_DESCONTO`) em `models/` ou `services/`.

### [LOW] Poor naming (AP-20)
File: models.py:187, 191, 219, 223, controllers.py:14, 56, 98
Description: `cursor2` e `cursor3` para consultas distintas, e o parâmetro `id` sombreia o builtin.
Impact: leitura mais difícil e risco de erro por sombreamento.
Recommendation: P-14 — renomear internamente (`pedido_id`, `produto_id`). Os campos de request e response ficam como estão.

### [LOW] Unused imports and dead code (AP-21)
File: database.py:2, models.py:2
Description: `import os` em `database.py` e `import sqlite3` em `models.py` nunca são usados.
Impact: ruído.
Recommendation: remover os dois imports.

### [LOW] Print-debugging instead of logging (AP-22)
File: app.py:56, 83-86, controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248, 250
Description: `print` como único log, banners `"=" * 50`, e notificações de e-mail, SMS e push simuladas com `print`. `controllers.py:161, 179, 182` imprimem o e-mail do usuário.
Impact: sem níveis nem formato, e dados pessoais em stdout.
Recommendation: P-15 — `logging` configurado em `config.py`, e `services/notification_service.py` registra os eventos sem guardar estado.

### [LOW] Verbose control flow (AP-23)
File: controllers.py:200, models.py:146, 244-245
Description: `not itens or len(itens) == 0` é redundante, `total = total + ...` num laço de soma, e `if faturamento is None: faturamento = 0` no lugar de `COALESCE`.
Impact: leitura mais lenta.
Recommendation: P-14 — `if not itens`, `sum(...)` e `COALESCE(SUM(total), 0)`.

================================
Total: 22 findings
================================

## Decisions requiring approval
1. Autenticação ativa por padrão (AP-11) — `/login` passa a devolver também um `token` (campo novo em `dados`/raiz; os campos existentes ficam); o cliente envia `Authorization: Bearer <token>`. Rotas públicas: `/`, `/health`, `/login`, `POST /usuarios` (cadastro, sempre papel `cliente`), `GET /produtos`, `GET /produtos/busca`, `GET /produtos/<id>`. Exigem login: `POST /pedidos` (o `usuario_id` do corpo deve ser o do token, ou admin), `GET /pedidos/usuario/<id>` e `GET /usuarios/<id>` (dono ou admin). Exigem admin: `GET /usuarios`, `POST/PUT/DELETE /produtos`, `GET /pedidos`, `PUT /pedidos/<id>/status`, `GET /relatorios/vendas`, `/admin/*` — default: aplicar exatamente isso; sem credencial 401, não-admin 403.
2. `/admin/reset-db` e `/admin/query` (AP-04) — as rotas continuam no app. Exigem admin, e `/admin/query` aceita só uma instrução `SELECT`, em conexão somente leitura (`UPDATE`/`DELETE`/DDL passam a responder 400) — default: aplicar.
3. Formato do hash de senha (AP-05) — senhas passam a ser guardadas com hash salgado do werkzeug. Os usuários de seed (`admin123`, `123456`, `senha123`) continuam logando com as mesmas senhas, agora gravadas como hash. Um `loja.db` antigo com senhas em texto puro é migrado para hash no boot — default: aplicar.
4. Campos removidos das respostas (AP-01, AP-06) — `senha` sai de `GET /usuarios` e `GET /usuarios/<id>`. `secret_key`, `db_path` e `debug` saem de `/health` — default: remover.
5. Padrões de execução (AP-12) — `DEBUG` desligado, bind em `127.0.0.1` (expor em todas as interfaces exige `HOST=0.0.0.0`) e CORS limitado a `CORS_ORIGINS` (padrão `http://localhost:3000,http://127.0.0.1:3000`) — default: aplicar. `SECRET_KEY` ausente gera uma chave aleatória por boot, e os tokens deixam de valer após reiniciar.
6. Erros normalizados (AP-16) — 500 passa a devolver `{"erro": "Erro interno", "sucesso": false}` sem `str(e)`. Entradas inválidas que hoje geram 500 (preço em texto, `preco_min` não numérico, corpo ausente) passam a responder 400 — default: aplicar.
7. `POST /pedidos` mais estrito (AP-10, AP-15) — `quantidade` precisa ser inteiro positivo (400 caso contrário), e o estoque é conferido de novo dentro da transação — default: aplicar.
8. `DELETE /produtos/<id>` (AP-10) — produto referenciado por algum item de pedido responde 409 em vez de apagar e deixar itens órfãos. Produto sem pedidos continua respondendo 200 — default: aplicar.
9. Cancelamento de pedido — hoje só imprime "Devolver estoque" e não devolve. Default: manter o comportamento atual, sem devolução automática.
10. Nomes de campos de request e response (AP-20) — default: manter todos os originais.
