================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask 3.1.1 (SQLite via sqlite3, file loja.db)
Files:   4 analyzed | ~780 lines of code

## Summary
CRITICAL: 9 | HIGH: 8 | MEDIUM: 6 | LOW: 10

## Findings

### [CRITICAL] Hardcoded credentials and secrets (AP-01)
File: app.py:7
Description: `app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"` grava a chave de assinatura de sessão do Flask como literal no código-fonte.
Impact: Qualquer pessoa com acesso ao repositório conhece a chave e pode forjar cookies de sessão assinados; a chave não pode ser trocada por ambiente sem editar código.
Recommendation: P-01 — ler `SECRET_KEY` de variável de ambiente em `src/config/settings.py` (com `secrets.token_hex(32)` como fallback de desenvolvimento) e carregar via `app.config.from_object(Settings)` em `src/app.py`; documentar em `.env.example`.

### [CRITICAL] Hardcoded credentials and secrets (AP-01)
File: controllers.py:285-289
Description: `health_check` devolve no JSON público `"secret_key": "minha-chave-super-secreta-123"`, além de `"db_path": "loja.db"`, `"debug": True` e `"ambiente": "producao"` como literais (também exposição de dados sensíveis, AP-06).
Impact: Qualquer cliente anônimo obtém a SECRET_KEY e detalhes de infraestrutura com um `GET /health`.
Recommendation: P-01 + P-05 — remover `secret_key`, `db_path` e `debug` da resposta (decisão 1) e ler `ambiente`/`versao` do `Settings`; o handler passa para `src/views/health_routes.py` + `src/controllers/health_controller.py`.

### [CRITICAL] SQL injection (AP-02)
File: models.py:28, 48-49, 58-60, 68, 92, 110, 127-128, 140, 149-150, 155, 158-160, 164-165, 174, 188, 192, 220, 224, 280, 291, 293, 295, 297
Description: Todas as queries são montadas por concatenação: `"SELECT * FROM produtos WHERE id = " + str(id)`, `INSERT INTO produtos ... VALUES ('" + nome + "'...`, `"SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"` em `login_usuario`, `"UPDATE pedidos SET status = '" + novo_status + "'"`, e em `buscar_produtos` `"nome LIKE '%" + termo + "%'"` e `"categoria = '" + categoria + "'"` vindos da query string.
Impact: `POST /login` com `email = "' OR 1=1 --"` autentica sem senha; `GET /produtos/busca?q=...` e `POST /produtos`/`/usuarios` permitem ler ou alterar qualquer tabela; um nome com apóstrofo (`D'Ávila`) quebra o INSERT com 500.
Recommendation: P-02 — reescrever todas as queries com placeholders `?` e tupla de parâmetros nos models por entidade (`src/models/produto_model.py`, `usuario_model.py`, `pedido_model.py`); em `buscar_produtos`, lista de cláusulas fixas + `params`.

### [CRITICAL] God class / God module (AP-03)
File: models.py:1-314
Description: Um único módulo de 314 linhas cobre três domínios (produtos, usuários, pedidos) mais relatório, e mistura acesso a dados (`get_db()` + SQL cru), serialização manual de linhas e regras de negócio: checagem de estoque e cálculo do total em `criar_pedido` (models.py:139-146), faixas de desconto em `relatorio_vendas` (models.py:256-262).
Impact: Qualquer mudança num domínio toca o mesmo arquivo; regras de negócio não podem ser testadas sem banco; não há fronteira de camada.
Recommendation: P-03 — dividir em `src/models/produto_model.py`, `src/models/usuario_model.py`, `src/models/pedido_model.py` (só persistência e serialização), mover o relatório e as faixas de desconto para `src/services/relatorio_service.py` e a orquestração do pedido para `src/controllers/pedido_controller.py`.

### [CRITICAL] Unprotected destructive or arbitrary-execution endpoint (AP-04)
File: app.py:47-57, 59-78
Description: `POST /admin/reset-db` (`reset_database`) executa `DELETE FROM` sem `WHERE` em `itens_pedido`, `pedidos`, `produtos` e `usuarios`; `POST /admin/query` (`executar_query`) executa `cursor.execute(query)` com o SQL cru de `dados.get("sql")` e faz `commit`. Nenhum dos dois verifica autenticação (também AP-11) e `executar_query` devolve `str(e)` ao cliente (também AP-16).
Impact: Qualquer cliente anônimo apaga o banco inteiro ou executa SQL arbitrário (leitura de senhas, `DROP TABLE`).
Recommendation: P-05 — mover para `src/views/admin_routes.py` + `src/controllers/admin_controller.py`, protegidos pela flag `ADMIN_ENABLED` (padrão desligado → 403) conforme decisão 3.

### [CRITICAL] Plaintext or weak password storage (AP-05)
File: models.py:110, 127-128
Description: `criar_usuario` grava `senha` exatamente como recebida no `INSERT INTO usuarios`; `login_usuario` autentica com `WHERE email = '...' AND senha = '...'` comparando o valor cru.
Impact: Um vazamento do `loja.db` (ou o `/admin/query`) expõe todas as senhas em texto puro; a comparação em SQL é também o vetor da injeção de login.
Recommendation: P-04 — `generate_password_hash` ao criar e `check_password_hash` após buscar por email em `src/models/usuario_model.py` (werkzeug já vem com o Flask); decisão 4.

### [CRITICAL] Plaintext or weak password storage (AP-05)
File: database.py:75-82
Description: O seed insere os usuários `admin@loja.com`/`admin123`, `joao@email.com`/`123456` e `maria@email.com`/`senha123` com a senha literal na coluna `senha`.
Impact: Credenciais do administrador ficam conhecidas e armazenadas em claro em toda instalação.
Recommendation: P-04 — o seed em `src/database.py` passa a gravar `generate_password_hash(senha)`.

### [CRITICAL] Sensitive data exposure (AP-06)
File: models.py:83, 99
Description: Os serializadores manuais de `get_todos_usuarios` e `get_usuario_por_id` incluem `"senha": row["senha"]`, então `GET /usuarios` e `GET /usuarios/<id>` devolvem a senha de cada usuário.
Impact: Qualquer cliente anônimo lista email + senha de todos os usuários, incluindo o admin.
Recommendation: P-05 + P-12 — um único `to_public_dict` em `src/models/usuario_model.py` sem `senha` (decisão 2).

### [CRITICAL] Sensitive data exposure (AP-06)
File: controllers.py:161, 165, 179, 182, 186
Description: `criar_usuario` e `login` registram o email do usuário em `print` ("Usuário criado: ", "Login bem-sucedido: ", "Login falhou: ") e devolvem `str(e)` cru ao cliente no caminho de autenticação (`return jsonify({"erro": str(e)}), 500`). Também print-debugging (AP-22).
Impact: Mensagens internas do sqlite/Python vazam para quem tenta autenticar; tentativas de login com emails ficam em stdout sem nível nem controle.
Recommendation: P-05 + P-10 + P-15 — erros inesperados viram mensagem genérica no handler central `src/middlewares/error_handler.py`; logs via `logging` sem dados pessoais desnecessários.

### [HIGH] Business logic in the controller / route (fat controller) (AP-07)
File: controllers.py:24-62, 188-220, 237-255
Description: As funções de `controllers.py` são ao mesmo tempo view e controller: leem `request`, validam, decidem e montam `jsonify`. `criar_produto` tem 39 linhas de validação inline; `criar_pedido` dispara efeitos colaterais de notificação (`print("ENVIANDO EMAIL...")`, SMS, PUSH) no handler; `atualizar_status_pedido` mantém a lista de transições válidas e as notificações de "aprovado"/"cancelado" inline.
Impact: Regras de pedido e notificação não podem ser reutilizadas nem testadas sem um request Flask; qualquer canal novo (fila, CLI) duplicaria a lógica.
Recommendation: P-06 — rotas finas em `src/views/*_routes.py` (Blueprints), fluxo em `src/controllers/produto_controller.py` / `pedido_controller.py`, notificações em `src/services/notification_service.py`.

### [HIGH] Tight coupling / no dependency injection (AP-08)
File: app.py:3-4, 6, 49, 66, 82
Description: `app = Flask(__name__)` é criado em nível de módulo sem `create_app`; `app.py` importa o módulo `controllers` concreto e o singleton `get_db` e chama `get_db()` direto em `reset_database`, `executar_query` e no `__main__`.
Impact: Não há como instanciar a aplicação com outro banco ou configuração (testes, ambientes); o import do módulo já tem efeitos colaterais.
Recommendation: P-07 — app factory `create_app(settings)` em `src/app.py` como composition root; `app.py` na raiz vira só o ponto de entrada.

### [HIGH] Tight coupling / no dependency injection (AP-08)
File: controllers.py:2-3, 266-274
Description: `controllers.py` importa o módulo `models` e o singleton `get_db`; `health_check` executa `SELECT COUNT(*)` diretamente no cursor, pulando a camada de model.
Impact: Controllers não recebem colaboradores, então não podem ser testados com dublês; SQL vaza para a camada de controle.
Recommendation: P-07 — controllers como classes que recebem models/serviços no construtor, montados em `src/app.py`; contagens do health em métodos `contar()` dos models.

### [HIGH] Tight coupling / no dependency injection (AP-08)
File: models.py:1, 5, 25, 44, 55, 66, 73, 90, 106, 123, 134, 172, 204, 236, 276, 286
Description: Cada uma das 15 funções de `models.py` chama o singleton global `get_db()` importado de `database`.
Impact: Models ficam presos a um único arquivo `loja.db` e à conexão global; impossível injetar um banco de teste.
Recommendation: P-07 — models como classes que recebem um objeto `Database` (`src/database.py`) criado em `create_app()`.

### [HIGH] Mutable global state (AP-09)
File: database.py:4, 8, 10
Description: `db_connection = None` em nível de módulo, mutado com `global db_connection` em `get_db()`, e uma única conexão `sqlite3.connect(db_path, check_same_thread=False)` compartilhada entre todas as threads do servidor.
Impact: Requisições concorrentes compartilham cursor/transação: um `commit` de uma requisição grava escritas pendentes de outra; erros de "recursive use of cursors" sob carga.
Recommendation: P-08 — classe `Database` em `src/database.py`, instanciada em `create_app()`, com uma conexão por requisição (guardada em `flask.g` e fechada em `teardown_appcontext`).

### [HIGH] Non-atomic multi-step writes and orphaned data (AP-10)
File: models.py:133-169, 65-70
Description: `criar_pedido` lê estoque em um loop, depois insere `pedidos`, `itens_pedido` e faz `UPDATE produtos SET estoque = estoque - ...` sem transação explícita nem rollback: uma exceção no meio (ex.: item sem `quantidade`) deixa escritas pendentes na conexão compartilhada, que o próximo `commit` de qualquer requisição grava; o estoque não é rechecado no momento do `UPDATE`. `deletar_produto` apaga o produto e deixa `itens_pedido` órfãos apontando para ele.
Impact: Pedidos sem itens ou estoque decrementado pela metade; venda acima do estoque sob concorrência; itens de pedido referenciando produtos inexistentes.
Recommendation: P-11 — validar tudo antes, depois gravar dentro de `with conn:` (commit/rollback automático) em `src/models/pedido_model.py`, com `UPDATE ... WHERE id = ? AND estoque >= ?` para rechecagem. Órfãos de `deletar_produto`: o histórico de pedidos é mantido de propósito (a leitura já trata como "Desconhecido"), então o delete não apaga itens; documentado no model.

### [HIGH] Missing authentication / authorization (AP-11)
File: app.py:18-19, 24-26, 28
Description: `GET /usuarios`, `GET /usuarios/<id>`, `GET /pedidos`, `GET /pedidos/usuario/<id>`, `PUT /pedidos/<id>/status` e `GET /relatorios/vendas` estão registrados sem nenhuma checagem de identidade ou papel; `POST /login` não emite token nem sessão, então não existe mecanismo de autenticação na API.
Impact: Qualquer cliente lista todos os usuários e pedidos, lê o faturamento e muda o status de qualquer pedido (ex.: cancelar pedidos alheios).
Recommendation: P-05 para os casos flagrantes (rotas admin, AP-04; remoção de `senha`); autenticação completa altera o contrato da API e é a decisão 7.

### [HIGH] Debug mode and unsafe defaults in the entry point (AP-12)
File: app.py:8-9, 85, 88
Description: `app.config["DEBUG"] = True` e `app.run(host="0.0.0.0", port=5000, debug=True)` expõem o debugger do Werkzeug em todas as interfaces; `CORS(app)` sem lista de origens; porta 5000 literal (também AP-18).
Impact: Com debug ligado em 0.0.0.0, qualquer máquina na rede que provoque uma exceção chega ao console interativo do Werkzeug (execução remota de código).
Recommendation: P-01 — `DEBUG`, `HOST`, `PORT` e `CORS_ORIGINS` vindos de `src/config/settings.py`, debug desligado e host `127.0.0.1` por padrão (decisão 6).

### [MEDIUM] N+1 queries (AP-13)
File: models.py:139-140, 154-155, 186-193, 218-225, 239-254
Description: `get_pedidos_usuario` e `get_todos_pedidos` fazem uma query de `itens_pedido` por pedido (`cursor2`) e uma query de `produtos` por item (`cursor3`); `criar_pedido` consulta `produtos` uma vez por item duas vezes (validação e inserção); `relatorio_vendas` faz cinco `SELECT COUNT/SUM` separados onde um `GROUP BY status` basta.
Impact: `GET /pedidos` com N pedidos e M itens dispara 1 + N + N·M queries; latência cresce linearmente com o histórico.
Recommendation: P-09 — um `LEFT JOIN` agrupado em memória em `src/models/pedido_model.py`, um `SELECT ... WHERE id IN (...)` em `criar_pedido`, e uma única agregação com `GROUP BY status` em `src/services/relatorio_service.py`.

### [MEDIUM] Duplicated logic (AP-14)
File: controllers.py:28-45, 72-90, 242
Description: O bloco `if "nome" not in dados` / `"preco"` / `"estoque"` + `preco < 0` / `estoque < 0` + leitura dos campos é copiado em `criar_produto` e `atualizar_produto`; a lista de status válidos é um literal inline em `atualizar_status_pedido`.
Impact: As duas cópias já divergiram (o update não valida tamanho de nome nem categoria, AP-15); mudar uma regra exige lembrar de todas as cópias.
Recommendation: P-12 — `validar_produto()` e `STATUS_VALIDOS` em `src/controllers/validators.py`, usados por create e update com as mesmas mensagens.

### [MEDIUM] Duplicated logic (AP-14)
File: models.py:12-21, 31-40, 79-86, 95-102, 177-200, 209-232, 304-313
Description: O dicionário de produto (`id, nome, descricao, preco, estoque, categoria, ativo, criado_em`) é montado à mão três vezes; o de usuário duas vezes; a montagem de pedido com itens é idêntica em `get_pedidos_usuario` e `get_todos_pedidos`.
Impact: Um campo novo ou removido (ex.: tirar `senha`) precisa ser alterado em vários lugares, e é fácil esquecer um.
Recommendation: P-12 — um serializador por entidade (`_to_dict`) em cada `src/models/<entidade>_model.py`; listagem de pedidos compartilha um único método com filtro opcional por usuário.

### [MEDIUM] Missing or inconsistent input validation (AP-15)
File: controllers.py:43-50, 86-90, 118-121, 157, 169-171, 196, 239-240
Description: `preco < 0` / `estoque < 0` sem checar tipo (string → `TypeError` → 500); `atualizar_produto` pula as checagens de tamanho de `nome` e de `categoria` que `criar_produto` faz; `float(preco_min)` em `buscar_produtos` estoura 500 com entrada inválida; email sem formato; `login` e `atualizar_status_pedido` chamam `dados.get` sem checar corpo nulo; itens de `criar_pedido` usados sem checar `produto_id`/`quantidade`.
Impact: Entradas inválidas viram 500 com mensagem interna em vez de 400; um produto pode ser atualizado com categoria inexistente.
Recommendation: P-12 — validadores únicos em `src/controllers/validators.py` que levantam `ValidationError` (400), aplicados igualmente a create e update (decisão 5).

### [MEDIUM] Scattered or leaky error handling (AP-16)
File: controllers.py:10-12, 21-22, 60-62, 95-96, 108-109, 125-126, 133-134, 143-144, 164-165, 185-186, 218-220, 226-227, 234-235, 254-255, 261-262, 291-292
Description: Todos os 16 handlers envolvem o corpo em `try/except Exception as e` e devolvem `jsonify({"erro": str(e)}), 500` (ou `"detalhes": str(e)` no health); não há handler central, e 404/405 do Flask saem em HTML.
Impact: Detalhes internos (mensagens do sqlite, nomes de colunas) chegam ao cliente; formato de erro inconsistente; erros são engolidos sem log.
Recommendation: P-10 — `AppError`/`ValidationError`/`NotFoundError`/`ForbiddenError` e `register_error_handlers` em `src/middlewares/error_handler.py`, com handler de `HTTPException`; handlers deixam de ter `try/except`.

### [MEDIUM] Configuration in code instead of a config module (AP-18)
File: database.py:5
Description: `db_path = "loja.db"` é literal no módulo de banco (e repetido como `"db_path": "loja.db"` em controllers.py:287).
Impact: Não dá para apontar testes ou outro ambiente para outro arquivo de banco sem editar código.
Recommendation: P-01 — `DATABASE_PATH` em `src/config/settings.py`, passado ao `Database` em `create_app()`.

### [LOW] Magic numbers and strings (AP-19)
File: controllers.py:47, 49, 52, 242, 285-286
Description: Limites de nome `2` e `200`, a lista `categorias_validas`, a lista de status e `"versao": "1.0.0"` / `"ambiente": "producao"` são literais inline nos handlers.
Impact: Regras de domínio ficam escondidas no fluxo HTTP e repetidas.
Recommendation: P-14 — constantes nomeadas (`NOME_MIN`, `NOME_MAX`, `CATEGORIAS_VALIDAS`, `STATUS_VALIDOS`) em `src/controllers/validators.py`; versão/ambiente em `Settings`.

### [LOW] Magic numbers and strings (AP-19)
File: models.py:150, 247, 250, 253, 257-262
Description: Faixas de desconto `10000 / 0.1`, `5000 / 0.05`, `1000 / 0.02` e os status `'pendente'`, `'aprovado'`, `'cancelado'` escritos inline em `relatorio_vendas` e `criar_pedido`.
Impact: A política de desconto não tem nome nem um lugar único para ser alterada.
Recommendation: P-14 — `FAIXAS_DESCONTO` e `calcular_desconto()` em `src/services/relatorio_service.py`; constantes de status em `src/models/pedido_model.py`.

### [LOW] Poor naming (AP-20)
File: controllers.py:56, 160
Description: `id = models.criar_produto(...)` e `id = models.criar_usuario(...)` sobrescrevem o builtin `id`; exceções sempre como `e`.
Impact: Leitura confusa e risco de bug ao usar `id()` no mesmo escopo.
Recommendation: P-14 — `produto_id`, `usuario_id` nos novos controllers.

### [LOW] Poor naming (AP-20)
File: models.py:24, 54, 65, 89, 187, 191, 219, 223
Description: Parâmetros chamados `id` (sombra do builtin) e cursores numerados `cursor2` / `cursor3` nos loops de pedidos.
Impact: Nomes não dizem o que o cursor percorre; dificulta a leitura das queries aninhadas.
Recommendation: P-14 — `produto_id`/`usuario_id`; os cursores somem com o JOIN de P-09.

### [LOW] Unused imports and dead code (AP-21)
File: database.py:2
Description: `import os` nunca é usado em `database.py`.
Impact: Ruído; sugere configuração por ambiente que não existe.
Recommendation: Remover (o novo `src/database.py` só importa o que usa).

### [LOW] Unused imports and dead code (AP-21)
File: models.py:2
Description: `import sqlite3` nunca é usado em `models.py`.
Impact: Ruído e acoplamento aparente ao driver.
Recommendation: Remover.

### [LOW] Print-debugging instead of logging (AP-22)
File: app.py:56, 83-86
Description: `print("!!! BANCO DE DADOS RESETADO !!!")` e o banner `print("=" * 50)` / `"SERVIDOR INICIADO"` / `"Rodando em http://localhost:5000"` (porta fixa, mesmo que a real mude).
Impact: Sem nível nem destino configurável; o banner pode mentir sobre a porta.
Recommendation: P-15 — `logging.basicConfig` em `create_app()` e `logger.info`/`logger.warning`.

### [LOW] Print-debugging instead of logging (AP-22)
File: controllers.py:8, 11, 57, 61, 106, 208-210, 219, 248, 250
Description: `print` em todos os caminhos de sucesso e erro, e notificações simuladas (`"ENVIANDO EMAIL"`, `"ENVIANDO SMS"`, `"ENVIANDO PUSH"`, `"NOTIFICAÇÃO: Pedido ... aprovado"`) como `print`. (As linhas 161, 179, 182 estão no achado AP-06.)
Impact: Logs sem nível/timestamp; notificações não podem ser trocadas por uma implementação real.
Recommendation: P-15 — `logging` nos controllers e `NotificationService` (`src/services/notification_service.py`) cujos métodos registram em log.

### [LOW] Verbose control flow (AP-23)
File: controllers.py:200
Description: `if not itens or len(itens) == 0:` — `not itens` já cobre a lista vazia.
Impact: Condição redundante.
Recommendation: P-14 — `if not itens:` no validador de pedido.

### [LOW] Verbose control flow (AP-23)
File: models.py:63, 70, 146, 283
Description: `total = total + (produto["preco"] * item["quantidade"])` num loop que `sum()` substitui; `return True` incondicional em `atualizar_produto`, `deletar_produto` e `atualizar_status_pedido` que ninguém lê.
Impact: Ruído; o retorno sugere um resultado que nunca é `False`.
Recommendation: P-14 — `total = sum(...)`; métodos de escrita sem retorno falso-booleano.

================================
Total: 33 findings
================================

## Decisions requiring approval
1. Remover `secret_key`, `db_path` e `debug` da resposta de `GET /health` — vazam segredo e infraestrutura (AP-01/AP-06) — default: as três chaves somem; `status`, `database`, `counts`, `versao`, `ambiente` permanecem (os dois últimos lidos do config).
2. Remover `senha` das respostas de `GET /usuarios` e `GET /usuarios/<id>` — expõe senhas (AP-06) — default: o campo some; os demais (`id`, `nome`, `email`, `tipo`, `criado_em`) permanecem.
3. `POST /admin/reset-db` e `POST /admin/query` — executam wipe/SQL arbitrário sem auth (AP-04) — default: rotas mantidas, protegidas pela flag `ADMIN_ENABLED` (env, padrão desligado) e respondendo `403 {"erro": ..., "sucesso": false}` enquanto desligada.
4. Formato de senha passa a ser hash werkzeug (`scrypt:`/`pbkdf2:`) — senhas em texto puro (AP-05) — default: seed e novos usuários gravam hash; login busca por email e usa `check_password_hash`; linhas legadas em texto puro de um `loja.db` antigo continuam autenticando via fallback e são re-hasheadas no primeiro login bem-sucedido.
5. Formato de erro normalizado e validação de entrada — `str(e)` vazando internals (AP-16) e entradas inválidas virando 500 (AP-15) — default: todo erro sai como `{"erro": <mensagem>, "sucesso": false}`; exceções inesperadas retornam 500 com `"Erro interno do servidor"`; corpo ausente/tipos errados retornam 400 em vez de 500; 404/405 do Flask passam a ser JSON; `PUT /produtos/<id>` passa a aplicar as mesmas checagens de tamanho de nome e categoria que o `POST`; o erro do health passa de `{"status": "erro", "detalhes": ...}` para o formato comum.
6. Debug e host por ambiente — debugger remoto exposto (AP-12) — default: `DEBUG` desligado (liga com `FLASK_DEBUG=1`), host padrão `127.0.0.1` (sobrescreve com `HOST=0.0.0.0`), porta via `PORT` (padrão 5000), `CORS_ORIGINS` padrão `*` (comportamento atual).
7. Autenticação/autorização completa nas rotas de usuários, pedidos e relatórios (AP-11) — mudaria o contrato de todas essas rotas — default: NÃO implementada nesta refatoração; apenas os casos flagrantes (admin, `senha`) são tratados, e AP-11 fica registrado como não resolvido.
8. Nomes de campos de request/response — default: todos os nomes originais mantidos (`dados`, `sucesso`, `erro`, `mensagem`, etc.).

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
