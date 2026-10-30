================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask 3.1.1 (SQLite, driver sqlite3 bruto)
Files:   4 analyzed | ~780 lines of code

## Summary
CRITICAL: 11 | HIGH: 9 | MEDIUM: 7 | LOW: 10

## Findings

### [CRITICAL] Hardcoded credentials and secrets (AP-01)
File: app.py:7
Description: `app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"` fixa a chave de assinatura da aplicação como literal no código-fonte.
Impact: Qualquer pessoa com acesso ao repositório conhece a chave e pode forjar qualquer dado assinado com ela (sessões, tokens).
Recommendation: P-01 — ler `SECRET_KEY` do ambiente em `src/config/settings.py` (fallback `secrets.token_hex(32)` por boot) e documentar em `.env.example`.

### [CRITICAL] Hardcoded credentials and secrets (AP-01)
File: controllers.py:285-289
Description: `health_check` devolve na resposta pública `"secret_key": "minha-chave-super-secreta-123"`, além de `"db_path": "loja.db"`, `"debug": True` e `"ambiente": "producao"` escritos como literais (também AP-06 e AP-18).
Impact: Qualquer cliente anônimo obtém a chave secreta e detalhes de infraestrutura com um GET em `/health`.
Recommendation: P-01 + P-05 — remover `secret_key`, `db_path` e `debug` da resposta; `versao`/`ambiente` vêm de `src/config/settings.py`; o handler fica em `src/controllers/sistema_controller.py`.

### [CRITICAL] SQL injection (AP-02)
File: models.py:28, 48-49, 58-60, 68, 92, 110, 127-128, 140, 149-150, 155, 158-160, 164-165, 174, 188, 192, 220, 224, 280, 291, 293, 295, 297
Description: Todas as queries são montadas por concatenação: `"SELECT * FROM produtos WHERE id = " + str(id)`, `"... WHERE email = '" + email + "' AND senha = '" + senha + "'"` em `login_usuario`, `"INSERT INTO produtos ... VALUES ('" + nome + "'"`, `" AND (nome LIKE '%" + termo + "%'"` em `buscar_produtos`, `"UPDATE pedidos SET status = '" + novo_status + "'"`.
Impact: `POST /login` com `senha = "' OR '1'='1"` autentica como o primeiro usuário (admin); `GET /produtos/busca?q=` permite ler ou alterar qualquer tabela; nomes com apóstrofo quebram o INSERT.
Recommendation: P-02 — queries parametrizadas com `?` em `src/models/produto_model.py`, `usuario_model.py` e `pedido_model.py`; busca dinâmica com lista de cláusulas fixas e `params`.

### [CRITICAL] God class / God module (AP-03)
File: app.py:1-88
Description: O entry point define configuração (linhas 7-9), registra as 19 rotas (11-47), executa SQL diretamente em `reset_database` e `executar_query` (49-76), formata respostas e sobe o servidor.
Impact: Nenhuma camada pode ser testada ou trocada isoladamente; não existe app factory para testes.
Recommendation: P-03 + P-07 — `app.py` vira um entry point fino sobre `src/app.py:create_app()`; rotas em `src/views/*_routes.py`; SQL administrativo em `src/models/sistema_model.py`.

### [CRITICAL] God class / God module (AP-03)
File: controllers.py:1-292
Description: Um único módulo trata produtos, usuários, pedidos, relatórios e health check; faz parse de request, validação, regras de status, notificações simuladas (208-210, 248-250), formatação `jsonify` e SQL direto em `health_check` (266-274).
Impact: Qualquer mudança em um domínio toca o mesmo arquivo; regras e HTTP ficam acoplados e não são testáveis sem o Flask.
Recommendation: P-03 — dividir por domínio em `src/controllers/{produto,usuario,pedido,sistema}_controller.py`, `src/views/*_routes.py` e `src/services/{notification,relatorio}_service.py`.

### [CRITICAL] God class / God module (AP-03)
File: models.py:1-314
Description: 314 linhas cobrindo produtos, usuários, pedidos e relatório; além de persistência, calcula total do pedido (137-146) e faixas de desconto (256-262) e monta à mão os dicts de resposta.
Impact: Persistência, regra de negócio e serialização ficam misturadas; um erro em um domínio afeta todos.
Recommendation: P-03 — `src/models/produto_model.py`, `usuario_model.py`, `pedido_model.py`; regras de relatório em `src/services/relatorio_service.py`.

### [CRITICAL] Unprotected destructive or arbitrary-execution endpoint (AP-04)
File: app.py:47-57, 59-78
Description: `POST /admin/reset-db` executa `DELETE FROM` sem `WHERE` em todas as tabelas, e `POST /admin/query` executa `cursor.execute(dados.get("sql"))` com SQL vindo do corpo, inclusive escrita com `db.commit()`. Nenhuma das duas rotas tem autenticação.
Impact: Qualquer cliente anônimo apaga a base inteira ou lê e altera qualquer dado, senhas incluídas.
Recommendation: P-05 + P-16 — manter as duas rotas em `src/views/sistema_routes.py` com `@require_admin`; `/admin/query` restrita a uma única instrução SELECT executada em conexão somente leitura.

### [CRITICAL] Plaintext or weak password storage (AP-05)
File: models.py:110, 126-128
Description: `criar_usuario` grava `senha` crua vinda do request, e `login_usuario` compara `WHERE email = ... AND senha = ...` contra o valor em texto puro.
Impact: Um vazamento da base (trivial via `/admin/query` ou `GET /usuarios`) expõe todas as senhas reutilizáveis dos clientes.
Recommendation: P-04 — `generate_password_hash`/`check_password_hash` (werkzeug) em `src/models/usuario_model.py`; login busca por email e verifica o hash.

### [CRITICAL] Plaintext or weak password storage (AP-05)
File: database.py:76-78
Description: O seed insere `("Admin", "admin@loja.com", "admin123", "admin")` e os demais usuários com senhas literais gravadas como texto puro.
Impact: A conta admin nasce com senha conhecida e sem hash.
Recommendation: P-04 — aplicar hash às senhas no seed em `src/database.py`; documentar no README as credenciais de desenvolvimento.

### [CRITICAL] Sensitive data exposure (AP-06)
File: models.py:83, 99
Description: Os serializers de `get_todos_usuarios` e `get_usuario_por_id` incluem `"senha": row["senha"]`, devolvida por `GET /usuarios` e `GET /usuarios/<id>`.
Impact: Qualquer cliente lista as senhas de todos os usuários.
Recommendation: P-05 — um único `to_public_dict` em `src/models/usuario_model.py` sem o campo `senha`.

### [CRITICAL] Sensitive data exposure (AP-06)
File: controllers.py:161, 165, 179, 182, 186
Description: `print("Usuário criado: " + email)` e `print("Login falhou: " + email)` gravam PII em stdout, e os caminhos de autenticação (`criar_usuario`, `login`) devolvem `str(e)` cru ao cliente.
Impact: Logs com emails e tentativas de login; mensagens de exceção revelam a estrutura de SQL, o que ajuda a explorar o AP-02.
Recommendation: P-05 + P-10 — logging sem dados sensíveis e erro 500 genérico pelo handler central em `src/middlewares/error_handler.py`.

### [HIGH] Business logic in the controller / route (AP-07)
File: controllers.py:24-62, 188-220, 237-255
Description: `criar_produto` concentra validação e a lista `categorias_validas`; `criar_pedido` dispara notificações inline (`print("ENVIANDO EMAIL ...")`, SMS, PUSH); `atualizar_status_pedido` decide transições de status e efeitos colaterais ("Devolver estoque") dentro do handler HTTP.
Impact: Regras inacessíveis fora do Flask; notificações acopladas à camada de transporte.
Recommendation: P-06 — handlers finos em `src/views/*_routes.py`; regras em `src/controllers/pedido_controller.py`; notificações em `src/services/notification_service.py`.

### [HIGH] Business logic in the controller / route (AP-07)
File: models.py:137-146, 256-262
Description: A camada de dados calcula o total do pedido (`total = total + (produto["preco"] * item["quantidade"])`) e as faixas de desconto do relatório (`if faturamento > 10000: desconto = faturamento * 0.1 ...`).
Impact: Regras de negócio escondidas na persistência, sem testes isolados.
Recommendation: P-06 — o total vai para `src/controllers/pedido_controller.py` e o desconto para `src/services/relatorio_service.py`; o model só lê e escreve.

### [HIGH] Tight coupling / no dependency injection (AP-08)
File: app.py:4, 6, 49, 66
Description: `app = Flask(__name__)` em nível de módulo, sem `create_app`; rotas administrativas chamam `get_db()` direto.
Impact: Impossível criar a app com outra configuração ou outro banco, por exemplo em testes.
Recommendation: P-07 — composition root `create_app(settings)` em `src/app.py` que instancia `Database`, models, controllers e blueprints.

### [HIGH] Tight coupling / no dependency injection (AP-08)
File: controllers.py:2-3, 266
Description: Os controllers importam o módulo `models` e o singleton `get_db` concretos; `health_check` abre o banco por conta própria.
Impact: Controllers não recebem colaboradores, o que impede substituir a persistência.
Recommendation: P-07 — controllers recebem model/service no construtor, a partir de `create_app`.

### [HIGH] Tight coupling / no dependency injection (AP-08)
File: models.py:1, 5, 25, 44, 55, 66, 73, 90, 106, 123, 134, 172, 204, 236, 276, 286
Description: Cada função de model chama `get_db()` global em vez de receber a conexão.
Impact: Todos os models ficam presos ao arquivo `loja.db` e à conexão compartilhada.
Recommendation: P-07 — classes `ProdutoModel(db)`, `UsuarioModel(db)`, `PedidoModel(db)` com o `Database` injetado.

### [HIGH] Mutable global state (AP-09)
File: database.py:4, 8, 10
Description: `global db_connection` guarda uma única conexão `sqlite3.connect(db_path, check_same_thread=False)`, compartilhada por todas as threads do servidor.
Impact: Requisições concorrentes compartilham cursor e transação: um commit de uma requisição confirma escritas pendentes de outra.
Recommendation: P-08 — classe `Database` em `src/database.py`, criada em `create_app`, com conexão por requisição (`flask.g`) fechada no teardown.

### [HIGH] Non-atomic multi-step writes and orphaned data (AP-10)
File: models.py:65-70, 133-168
Description: `criar_pedido` lê o estoque, depois faz INSERT em `pedidos`, N INSERTs em `itens_pedido` e N UPDATEs de estoque sem transação explícita e sem rechecar o estoque no UPDATE; uma exceção no meio deixa escritas pendentes na conexão global, e o próximo commit de outra rota as confirma. `deletar_produto` apaga o produto e deixa `itens_pedido` órfãos.
Impact: Pedidos sem itens, estoque negativo sob concorrência, itens apontando para produtos inexistentes.
Recommendation: P-11 — validar tudo primeiro e gravar dentro de `with conn:` com `UPDATE ... WHERE estoque >= ?` checado; recusar o DELETE de produto referenciado por pedidos (`src/models/pedido_model.py`, `produto_model.py`).

### [HIGH] Missing authentication / authorization (AP-11)
File: app.py:14-28
Description: Escrita de produtos, `GET /usuarios`, `GET /usuarios/<id>`, `GET /pedidos`, `GET /pedidos/usuario/<id>`, `PUT /pedidos/<id>/status` e `GET /relatorios/vendas` são anônimos; `login` (controllers.py:180) não emite token nenhum; `criar_pedido` aceita `usuario_id` do corpo (controllers.py:195), então qualquer um cria pedido em nome de outro.
Impact: Qualquer cliente lê dados de todos os usuários e pedidos, altera preços e aprova pedidos.
Recommendation: P-16 — tokens assinados com `itsdangerous` emitidos no login; `require_auth`, `require_self_or_admin` e `require_admin` em `src/middlewares/auth.py`, ativos por padrão.

### [HIGH] Debug mode and unsafe defaults in the entry point (AP-12)
File: app.py:8-9, 88
Description: `app.config["DEBUG"] = True` e `app.run(host="0.0.0.0", port=5000, debug=True)` expõem o debugger do Werkzeug na rede; `CORS(app)` sem lista de origens.
Impact: Execução remota de código pelo console do debugger; qualquer site pode chamar a API pelo navegador.
Recommendation: P-01 — `DEBUG`, `HOST`, `PORT` e `CORS_ORIGINS` em `src/config/settings.py`, com padrões seguros (debug off, `127.0.0.1`, origens locais).

### [MEDIUM] N+1 queries (AP-13)
File: models.py:187-193, 219-225, 239-254
Description: `get_pedidos_usuario` e `get_todos_pedidos` fazem uma query de itens por pedido (`cursor2`) e uma de produto por item (`cursor3`); `relatorio_vendas` faz cinco consultas separadas onde um `GROUP BY status` bastaria.
Impact: O custo cresce linearmente com pedidos × itens.
Recommendation: P-09 — um único `LEFT JOIN` agrupado em memória em `src/models/pedido_model.py`; agregação com `GROUP BY` no relatório.

### [MEDIUM] Duplicated logic (AP-14)
File: controllers.py:28-46, 72-90, 242
Description: O bloco `if "nome" not in dados ... if preco < 0 ...` está copiado em `criar_produto` e `atualizar_produto`; a lista de status está em literal inline.
Impact: As cópias já divergiram: o update não valida tamanho do nome nem categoria.
Recommendation: P-12 — `validar_produto` e `STATUS_VALIDOS` únicos em `src/controllers/validators.py`.

### [MEDIUM] Duplicated logic (AP-14)
File: models.py:12-21, 31-40, 304-313, 79-86, 95-102, 178-199, 211-231
Description: O dict de produto é montado campo a campo três vezes, o de usuário duas, e o laço de montagem de pedido+itens está duplicado entre `get_pedidos_usuario` e `get_todos_pedidos`.
Impact: Um campo novo exige mudar vários lugares; foi assim que `senha` vazou nas duas cópias.
Recommendation: P-12 — um serializer por entidade (`_to_dict`) e um único método de listagem de pedidos com filtro opcional.

### [MEDIUM] Missing or inconsistent input validation (AP-15)
File: controllers.py:43-50, 82-90, 118-121, 157, 170, 196-201, 240, 245
Description: `preco < 0` com string gera TypeError → 500; `float(preco_min)` inválido → 500; `dados.get(...)` em `login` e `atualizar_status_pedido` com corpo ausente → AttributeError 500; itens do pedido sem checagem de `produto_id`/`quantidade` (quantidade negativa aumenta o estoque); email sem formato nem unicidade; status atualizado em pedido inexistente responde 200.
Impact: Erros do cliente viram 500, e dados inválidos (estoque inflado) entram na base.
Recommendation: P-12 — validators em `src/controllers/validators.py` que levantam `ValidationError` (400) e `NotFoundError` (404).

### [MEDIUM] Scattered or leaky error handling (AP-16)
File: controllers.py:10-12, 21-22, 60-62, 95-96, 108-109, 125-126, 133-134, 143-144, 164-165, 185-186, 218-220, 226-227, 234-235, 254-255, 261-262, 291-292
Description: Os 16 handlers repetem `try/except Exception as e: return jsonify({"erro": str(e)}), 500`.
Impact: Detalhes internos vão para o cliente; não existe tratamento central.
Recommendation: P-10 — `register_error_handlers` em `src/middlewares/error_handler.py` com `AppError`, `HTTPException` e catch-all genérico.

### [MEDIUM] Scattered or leaky error handling (AP-16)
File: app.py:77-78
Description: `executar_query` devolve `{"erro": str(e)}` com a mensagem crua do SQLite.
Impact: Facilita o reconhecimento do schema.
Recommendation: P-10 — erros de SQL viram `ValidationError` com mensagem controlada via handler central.

### [MEDIUM] Configuration in code instead of a config module (AP-18)
File: database.py:5
Description: `db_path = "loja.db"` fixo no módulo de banco.
Impact: Impossível usar outro banco por ambiente (testes, produção).
Recommendation: P-01 — `DATABASE_PATH` em `src/config/settings.py`.

### [LOW] Magic numbers and strings (AP-19)
File: models.py:247, 250, 253, 257-262
Description: Status `'pendente'`, `'aprovado'`, `'cancelado'` inline e faixas `10000/0.1`, `5000/0.05`, `1000/0.02` sem nome.
Impact: Regra de desconto opaca e difícil de alterar.
Recommendation: P-14 — `FAIXAS_DESCONTO` e constantes de status em `src/services/relatorio_service.py`.

### [LOW] Magic numbers and strings (AP-19)
File: controllers.py:47-52, 242
Description: Limites de nome `2`/`200`, lista `categorias_validas` e lista de status como literais.
Impact: Limites espalhados e sem documentação.
Recommendation: P-14 — `NOME_MIN`, `NOME_MAX`, `CATEGORIAS_VALIDAS`, `STATUS_VALIDOS` em `src/controllers/validators.py`.

### [LOW] Poor naming (AP-20)
File: controllers.py:14, 56, 64, 98, 160
Description: `id` sombreia o builtin em vários handlers; `e` genérico para exceções.
Impact: Leitura confusa e risco de bug ao usar `id()`.
Recommendation: P-14 — renomear para `produto_id`/`usuario_id` internamente (parâmetros de rota Flask são internos ao servidor).

### [LOW] Poor naming (AP-20)
File: models.py:187, 191, 219, 223
Description: `cursor2`, `cursor3`, `prod`.
Impact: Nomes não dizem o que cada cursor percorre.
Recommendation: P-14 — desaparecem com o JOIN de P-09.

### [LOW] Unused imports and dead code (AP-21)
File: database.py:2
Description: `import os` nunca é usado.
Impact: Ruído.
Recommendation: Remover.

### [LOW] Unused imports and dead code (AP-21)
File: models.py:2
Description: `import sqlite3` nunca é referenciado em models.py.
Impact: Ruído.
Recommendation: Remover.

### [LOW] Print-debugging instead of logging (AP-22)
File: app.py:56, 83-86
Description: `print("!!! BANCO DE DADOS RESETADO !!!")` e banner `print("=" * 50)`.
Impact: Sem níveis nem destino configurável.
Recommendation: P-15 — `logging` configurado em `create_app`.

### [LOW] Print-debugging instead of logging (AP-22)
File: controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248, 250
Description: 14 `print(...)`, incluindo as notificações simuladas por print.
Impact: Logs não estruturados; notificações sem ponto de extensão.
Recommendation: P-15 — `logger.info` e `NotificationService` em `src/services/notification_service.py`.

### [LOW] Verbose control flow (AP-23)
File: controllers.py:200
Description: `if not itens or len(itens) == 0` é redundante (`not itens` já cobre a lista vazia).
Impact: Leitura.
Recommendation: P-14 — `if not itens`.

### [LOW] Verbose control flow (AP-23)
File: models.py:146
Description: `total = total + (produto["preco"] * item["quantidade"])` acumulado em laço manual.
Impact: Leitura.
Recommendation: P-14 — `sum(...)` sobre os itens validados no controller.

================================
Total: 37 findings
================================

## Decisions requiring approval
1. `GET /health` deixa de retornar `secret_key`, `db_path` e `debug` — expõem segredo e infraestrutura (AP-01/AP-06) — default: resposta mantém `status`, `database`, `counts`, `versao`, `ambiente` (este último vindo de config, padrão `producao`).
2. `GET /usuarios` e `GET /usuarios/<id>` deixam de retornar `senha` — AP-06 — default: demais campos mantidos.
3. Senhas passam a ser armazenadas com hash werkzeug (scrypt/pbkdf2) — AP-05 — default: seed com hash; senhas legadas em texto puro de um `loja.db` existente ainda funcionam no login (comparação em tempo constante) e são re-hasheadas no primeiro login bem-sucedido.
4. Autenticação obrigatória por padrão (P-16) — AP-11 — default: `POST /login` mantém as chaves atuais e acrescenta `token` (assinado com itsdangerous, validade 24h); clientes enviam `Authorization: Bearer <token>`. Públicas: `GET /`, `GET /health`, `POST /login`, `POST /usuarios` (cadastro sempre como `cliente`), `GET /produtos`, `GET /produtos/busca`, `GET /produtos/<id>`. Autenticada: `POST /pedidos` (`usuario_id` precisa ser o do token, salvo admin). Dono ou admin: `GET /usuarios/<id>`, `GET /pedidos/usuario/<id>`. Somente admin: `POST/PUT/DELETE /produtos`, `GET /usuarios`, `GET /pedidos`, `PUT /pedidos/<id>/status`, `GET /relatorios/vendas`, `POST /admin/reset-db`, `POST /admin/query`. Sem token/inválido → 401; sem permissão → 403.
5. `POST /admin/query` continua existindo, mas restrita — AP-04 — default: somente admin; aceita uma única instrução `SELECT` executada em conexão SQLite somente leitura (`mode=ro`); qualquer outra instrução → 400.
6. `POST /admin/reset-db` continua existindo — AP-04 — default: somente admin; mesmo comportamento de limpar as 4 tabelas (como hoje, o seed só volta no próximo boot, então o token do admin deixa de valer até reiniciar).
7. `SECRET_KEY` sai do código — AP-01 — default: lida do ambiente; se ausente, chave aleatória por boot (tokens invalidam a cada reinício). `.env.example` documenta as variáveis.
8. Defaults do servidor — AP-12 — default: `debug` desligado (`FLASK_DEBUG=1` religa), host `127.0.0.1` (`HOST` configurável), porta 5000, CORS limitado a `CORS_ORIGINS` (padrão `http://localhost:5000,http://127.0.0.1:5000`).
9. Erros normalizados — AP-16 — default: corpo `{"erro": ..., "sucesso": false}` em todos os erros; 500 com mensagem genérica "Erro interno do servidor" (detalhe só no log); 404/405 do Flask em JSON.
10. Validação mais rígida — AP-15 — default: corpo ausente ou campos de tipo errado → 400 (antes 500); itens de pedido exigem `produto_id` e `quantidade` inteiros > 0; `PUT /produtos/<id>` aplica as mesmas regras do create (tamanho de nome, categoria); email duplicado no cadastro → 400; `PUT /pedidos/<id>/status` em pedido inexistente → 404 (antes 200). Mensagens e nomes de campos originais mantidos.
11. Integridade de dados — AP-10 — default: criação de pedido atômica com estoque rechecado no UPDATE (falta de estoque → 400 com a mensagem atual); `DELETE /produtos/<id>` de produto que já consta em pedidos → 409 "Produto possui pedidos vinculados" (sem vínculo continua 200).

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
