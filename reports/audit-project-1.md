================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask 3.1.1 (SQLite via sqlite3)
Files:   4 analyzed | ~780 lines of code

## Summary
CRITICAL: 12 | HIGH: 9 | MEDIUM: 10 | LOW: 10

## Findings

### [CRITICAL] Hardcoded credentials and secrets (AP-01)
File: app.py:7
Description: `app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"` é um literal no código-fonte.
Impact: Quem lê o repositório conhece a chave de assinatura; qualquer token ou sessão assinado com ela pode ser forjado.
Recommendation: P-01 — `SECRET_KEY` lido do ambiente em `src/config/settings.py`, gerado com `secrets.token_hex(32)` no boot quando ausente; listado em `.env.example` sem valor.
Verification: G 'minha-chave-super-secreta' → nenhum hit (inclui README.md e .env.example via `grep -rn "minha-chave" README.md .env.example`); G '(environ\.get|getenv)\(\s*"[A-Z_]*(SECRET|PASSWORD|KEY|TOKEN)"\s*,\s*"' → nenhum hit; um token forjado com a chave antiga (`URLSafeTimedSerializer("minha-chave-super-secreta-123", salt="auth").dumps({"uid":1})`) em GET /usuarios → 401.

### [CRITICAL] Hardcoded credentials and secrets (AP-01)
File: controllers.py:289
Description: `health_check` devolve `"secret_key": "minha-chave-super-secreta-123"` no corpo de GET /health, uma rota pública.
Impact: Qualquer visitante anônimo obtém a chave de assinatura da aplicação com um único GET.
Recommendation: P-01 + P-05 — remover o campo da resposta; a chave vive só em `src/config/settings.py`.
Verification: GET /health anônimo → 200 sem a chave `secret_key` e sem o valor da chave em parte alguma do corpo; G 'secret_key' → nenhum hit fora de `src/config/settings.py` (o nome do atributo lá é `SECRET_KEY`, então `grep -rnE 'secret_key' --include='*.py' --exclude-dir=.claude --exclude-dir=.venv .` → nenhum hit).

### [CRITICAL] Hardcoded credentials and secrets (AP-01)
File: database.py:76-78
Description: O seed grava as contas `admin@loja.com`/`admin123`, `joao@email.com`/`123456`, `maria@email.com`/`senha123` como literais no código.
Impact: Toda instalação nasce com uma conta admin de senha pública; qualquer pessoa faz login como admin.
Recommendation: P-16 — senhas do seed vêm de `ADMIN_PASSWORD`, `JOAO_PASSWORD`, `MARIA_PASSWORD`; quando ausentes, são geradas (`secrets.token_urlsafe`) e exibidas uma única vez no log do boot que faz o seed. Seed em `src/database.py`.
Verification: catálogo AP-01 (G '(secret|passw|pwd|senha|api_?key|token)[A-Za-z_]*[]"'"'"']*\s*[:=]\s*["'"'"'][^"'"'"']{3,}|["'"'"'][^"'"'"' ]+@[^"'"'"' ]+["'"'"']\s*,\s*["'"'"'][^"'"'"']{3,}["'"'"']' com -i) → nenhum hit; `grep -rnE "admin123|senha123|\"123456\"" --include='*.py' --include='*.md' --include='.env.example' --exclude-dir=.claude .` → nenhum hit; POST /login {"email":"admin@loja.com","senha":"admin123"} → 401, com a senha exibida no boot → 200. Upgrade path: num banco criado pelo código original, o boot refatorado substitui as senhas dessas contas; admin123/123456/senha123 → 401 e as senhas exibidas → 200.

### [CRITICAL] SQL injection (AP-02)
File: models.py:28, 47-50, 57-61, 68, 92, 109-111, 126-129, 140, 148-151, 155, 157-161, 163-166, 174, 188, 192, 220, 224, 279-281, 289-299
Description: Todas as queries são montadas por concatenação: `"SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"` em `login_usuario`, `" AND (nome LIKE '%" + termo + "%' ..."` e `" AND categoria = '" + categoria + "'"` em `buscar_produtos`, INSERT/UPDATE de produtos e usuários com `nome`, `descricao`, `email`, `senha` vindos do request.
Impact: Login como qualquer usuário sem senha (`admin@loja.com' --`), leitura de todo o catálogo e de outras tabelas pela busca, e escrita arbitrária; valores com apóstrofo (`O'Reilly`) quebram a gravação com 500.
Recommendation: P-02 — parâmetros `?` em todas as queries, filtros montados só com texto fixo, nos models `src/models/produto_model.py`, `usuario_model.py`, `pedido_model.py`.
Verification: catálogo AP-02 (G '(SELECT|INSERT|UPDATE|DELETE|WHERE|LIKE|VALUES|SET)\b[^#]*["'"'"'`] *(\+|% *[(a-z]|\.format\()') → nenhum hit; POST /login {"email":"admin@loja.com' --","senha":"x"} → 401; GET /produtos/busca?q=' OR '1'='1 → `total` 0; GET /produtos/busca?categoria=x' OR '1'='1 → `total` 0; admin POST /produtos {"nome":"O'Reilly","descricao":"it's","preco":10,"estoque":1} → 201 e GET /produtos/<id> devolve `nome` e `descricao` idênticos; POST /usuarios com nome "D'Ávila" → 201 e valor lido de volta intacto.

### [CRITICAL] God class / God module (AP-03)
File: app.py:6-30, 47-57, 59-78, 82
Description: `app.py` cria o app, registra as 19 rotas, abre a conexão (`get_db()` na linha 82) e executa SQL direto nas views `reset_database` e `executar_query`.
Impact: Rota, acesso a dados e configuração acoplados num módulo sem fábrica: nada pode ser testado nem reconfigurado isoladamente.
Recommendation: P-03 + P-07 — `app.py` vira só o ponto de entrada (`from src.app import create_app`); rotas em `src/views/*_routes.py`, SQL em `src/models/`, composição em `src/app.py`.
Verification: `grep -nE "execute|cursor|@app\.route|add_url_rule|get_db" app.py` → nenhum hit; `grep -rnE "execute\(|cursor" src/views src/controllers` → nenhum hit; as 19 rotas respondem o status do baseline (com credenciais onde exigido).

### [CRITICAL] God class / God module (AP-03)
File: controllers.py:1-292 (SQL em 264-274, notificações em 208-210 e 247-250, regras em 52-54 e 242)
Description: Um único `controllers.py` atende produtos, usuários, pedidos, relatórios e health; lê o request, valida, aplica regras, simula envio de e-mail/SMS/push, roda SQL (`health_check`) e formata `jsonify`.
Impact: Qualquer mudança num domínio mexe no arquivo de todos; regra, IO e HTTP não se testam separadamente.
Recommendation: P-03 — dividir por domínio em `src/controllers/{produto,usuario,pedido,sistema}_controller.py`, rotas em `src/views/`, notificações em `src/services/notification_service.py`.
Verification: `test ! -e controllers.py` → verdadeiro; `grep -rnE "jsonify|request\." src/controllers` → nenhum hit; `grep -rnE "execute\(" src/controllers src/views` → nenhum hit; os endpoints respondem o baseline.

### [CRITICAL] God class / God module (AP-03)
File: models.py:1-314 (desconto em 256-262, estoque em 144 e 163-166)
Description: `models.py` mistura os três domínios, monta dicts de resposta, decide estoque e calcula as faixas de desconto de `relatorio_vendas`.
Impact: A regra de faturamento/desconto só existe dentro da camada de dados; os domínios se acoplam pelo mesmo módulo.
Recommendation: P-03 + P-06 — um model por entidade em `src/models/`; o cálculo do relatório vai para `src/services/relatorio_service.py`.
Verification: `test ! -e models.py` → verdadeiro; `grep -rnE "desconto|faturamento \*" src/models` → nenhum hit; GET /relatorios/vendas (admin) → 200 com as mesmas chaves e valores do baseline para os mesmos pedidos.

### [CRITICAL] Unprotected destructive or arbitrary-execution endpoint (AP-04)
File: app.py:47-57, 59-78
Description: `POST /admin/reset-db` apaga as quatro tabelas e `POST /admin/query` executa `dados.get("sql")` direto em `cursor.execute(query)`, ambos sem autenticação.
Impact: Qualquer anônimo apaga o banco, lê as senhas (`SELECT senha FROM usuarios`) ou executa `DROP TABLE`.
Recommendation: P-05 + P-16 — as duas rotas ficam e exigem admin; `/admin/query` aceita só `{"consulta": "<nome>"}` de uma allow-list fixa de leituras parametrizadas sem colunas de credencial; `sql` livre → 400. Rotas em `src/views/sistema_routes.py`.
Verification: anônimo POST /admin/reset-db e /admin/query → 401; joao → 403 nos dois; admin POST /admin/query {"sql":"DROP TABLE produtos"} → 400 e GET /produtos continua 200 com 10 itens; admin {"sql":"SELECT senha FROM usuarios"} → 400; admin {"consulta":"pedidos_por_status"} → 200 com `dados`, `sucesso`; admin POST /admin/query sem corpo → 400; admin POST /admin/reset-db → 200 e as quatro tabelas ficam vazias (executado por último).

### [CRITICAL] Plaintext or weak password storage (AP-05)
File: database.py:75-83
Description: O seed insere `senha` em texto puro na tabela `usuarios`.
Impact: Quem acessa o arquivo `loja.db` (ou um backup) lê todas as senhas.
Recommendation: P-04 — seed grava `generate_password_hash(...)` (scrypt) em `src/database.py`; no boot, senhas legadas em texto puro são migradas.
Verification: `SELECT senha FROM usuarios` → todo valor começa com `scrypt:`; login do admin com a senha exibida no boot → 200, com senha errada → 401. Upgrade path: em banco criado pelo código original, após o boot refatorado, a mesma query → todos `scrypt:`.

### [CRITICAL] Plaintext or weak password storage (AP-05)
File: models.py:105-111, 122-131
Description: `criar_usuario` grava `senha` crua e `login_usuario` compara `WHERE ... AND senha = '<senha>'` com o valor bruto.
Impact: Toda senha cadastrada fica legível no banco; o login depende de texto puro armazenado.
Recommendation: P-04 — `UsuarioModel.criar` grava hash; login busca por e-mail e usa `check_password_hash`, em `src/models/usuario_model.py`.
Verification: POST /usuarios {"nome":"Ana","email":"ana@x.com","senha":"Segredo#1"} → 201 e `SELECT senha FROM usuarios WHERE email='ana@x.com'` começa com `scrypt:`; POST /login com a senha certa → 200, errada → 401. Upgrade path: usuário criado pelo código original (senha em texto puro) continua fazendo login com a própria senha após o boot refatorado, e o valor armazenado passa a começar com `scrypt:`.

### [CRITICAL] Sensitive data exposure (AP-06)
File: controllers.py:164-165, 185-186, 284-289
Description: `health_check` expõe `ambiente`, `db_path`, `debug` e `secret_key`; `criar_usuario` e `login` devolvem `str(e)` ao cliente em caminhos de autenticação.
Impact: Reconhecimento gratuito (caminho do banco, modo debug) e vazamento de detalhes internos de exceções em rotas de credencial.
Recommendation: P-05 + P-10 — health devolve só `status`, `database`, `counts`, `versao`; exceções inesperadas viram mensagem genérica com detalhe só no log (`src/middlewares/error_handler.py`).
Verification: GET /health → 200 sem as chaves `secret_key`, `db_path`, `debug`, `ambiente`; POST /login com corpo `null` → 400 com mensagem de validação, sem texto de exceção Python (hoje 500 com "'NoneType' object has no attribute 'get'"); falha forçada no banco (trigger `RAISE(ABORT,'forced-leak')` em `usuarios`) num POST /usuarios → 500 `{"erro":"Erro interno do servidor","sucesso":false}` sem "forced-leak" no corpo, e "forced-leak" presente no log.

### [CRITICAL] Sensitive data exposure (AP-06)
File: models.py:83, 99
Description: `get_todos_usuarios` e `get_usuario_por_id` serializam `"senha": row["senha"]`.
Impact: GET /usuarios entrega a senha de todos os usuários a quem chamar.
Recommendation: P-05 — serializer único de usuário sem `senha` em `src/models/usuario_model.py`.
Verification: admin GET /usuarios → nenhum item tem a chave `senha`; joao GET /usuarios/2 → sem `senha`; resposta de POST /login → sem `senha`; `grep -rnE '"senha": row' --include='*.py' --exclude-dir=.claude --exclude-dir=.venv .` → nenhum hit.

### [HIGH] Business logic in the controller / route (AP-07)
File: controllers.py:52-54, 208-210, 242, 247-250
Description: Os handlers `criar_produto`, `criar_pedido` e `atualizar_status_pedido` carregam a lista de categorias válidas, a lista de status e os efeitos colaterais de notificação (`print("ENVIANDO EMAIL ...")`, `"ENVIANDO SMS"`, `"ENVIANDO PUSH"`, `"NOTIFICAÇÃO: Pedido ... aprovado"`) inline.
Impact: Regras e notificações só existem dentro do handler HTTP; não há como reutilizar, testar ou trocar o canal de notificação.
Recommendation: P-06 — validação em `src/controllers/validators.py`, notificações em `src/services/notification_service.py` chamadas pelo `PedidoController`; a rota chama o controller em uma linha.
Verification: G 'ENVIANDO|NOTIFICAÇÃO' → hits só em `src/services/notification_service.py`; `grep -rnE "ENVIANDO|NOTIFICA|categorias_validas" src/views src/controllers/pedido_controller.py src/controllers/produto_controller.py` → nenhum hit; POST /pedidos (joao) → 201 e o log mostra as três notificações; admin PUT /pedidos/<id>/status {"status":"aprovado"} → 200 e o log mostra a notificação de aprovação.

### [HIGH] Tight coupling / no dependency injection (AP-08)
File: app.py:3-4, 6, 49, 66, 82
Description: `app = Flask(__name__)` no nível do módulo, sem `create_app`; as views importam `controllers` e `get_db` concretos.
Impact: Não há como subir o app com outra configuração ou outro banco (testes, staging) sem editar código.
Recommendation: P-07 — `create_app(settings)` em `src/app.py` constrói Database, models, services, controllers e blueprints.
Verification: `grep -nE "^def create_app" src/app.py` → 1 hit; G 'get_db\(|^from database import|^import (models|controllers)$' → nenhum hit; `python app.py` sobe e as rotas respondem o baseline.

### [HIGH] Tight coupling / no dependency injection (AP-08)
File: controllers.py:2-3, 266
Description: Os handlers importam o módulo `models` e o singleton `get_db` diretamente; `health_check` abre cursor no próprio handler.
Impact: Controllers só funcionam com o banco global; não recebem colaboradores, não se testam com um banco isolado.
Recommendation: P-07 — controllers são classes que recebem seus models/services no construtor, montadas em `src/app.py`.
Verification: G 'get_db\(|^import models$' → nenhum hit; `grep -rnE "^from src\.database|^import sqlite3" src/controllers src/views` → nenhum hit.

### [HIGH] Tight coupling / no dependency injection (AP-08)
File: models.py:1, 5, 25, 44, 55, 66, 73, 90, 106, 123, 134, 172, 204, 236, 276, 286
Description: Toda função de `models.py` chama `get_db()` do módulo global `database`.
Impact: Os models não podem apontar para outro banco nem ser testados com um banco temporário.
Recommendation: P-07 — models recebem a instância `Database` no construtor.
Verification: G 'get_db\(' → nenhum hit; G 'sqlite3\.connect' → hits só em `src/database.py`.

### [HIGH] Mutable global state (AP-09)
File: database.py:4, 8-11
Description: `db_connection` é um global mutado por `get_db()` e compartilhado entre threads com `check_same_thread=False`.
Impact: Requisições concorrentes usam a mesma conexão e a mesma transação: uma requisição pode commitar escritas pela metade de outra, e há erros de cursor sob concorrência.
Recommendation: P-08 — objeto `Database` criado no composition root que abre uma conexão por requisição (`flask.g` + teardown).
Verification: G '^\s*global |check_same_thread|^[A-Za-z_][A-Za-z0-9_]* *(: *[^=]+)?= *(\[\]|\{\}|set\(\)|dict\(\)|defaultdict\(|deque\()|self\.[a-z_]+ *(: *[^=]+)?= *(\[\]|\{\}|set\(\)|dict\(\)|list\(\)|defaultdict\(|deque\()' → nenhum hit; 20 POST /pedidos concorrentes (joao) → nenhum 500.

### [HIGH] Non-atomic multi-step writes and orphaned data (AP-10)
File: models.py:65-70, 133-169
Description: `criar_pedido` valida cada item isoladamente contra o estoque, depois insere pedido, itens e baixa estoque sem transação explícita nem rollback; o estoque não é rechecado na escrita. `deletar_produto` apaga o produto enquanto `itens_pedido` continua apontando para ele.
Impact: Itens repetidos ou pedidos concorrentes vendem além do estoque (estoque negativo); uma falha no meio deixa pedido sem itens que outra requisição acaba commitando; apagar produto deixa itens órfãos ("Desconhecido").
Recommendation: P-11 — quantidades somadas por produto, validação completa antes de escrever, transação `BEGIN IMMEDIATE` com `UPDATE ... SET estoque = estoque - ? WHERE id = ? AND estoque >= ?` checando `rowcount`; DELETE de produto vira exclusão lógica (`ativo = 0`), em `src/models/pedido_model.py` e `produto_model.py`.
Verification: joao POST /pedidos {"itens":[{"produto_id":6,"quantidade":5},{"produto_id":6,"quantidade":5}]} (estoque 8) → 400, nenhuma linha nova em `pedidos`, `SELECT estoque FROM produtos WHERE id=6` → 8; 20 POST /pedidos concorrentes de 1 unidade do produto 6 → exatamente 8 × 201 e 12 × 400, estoque 0, 8 pedidos; falha forçada no segundo item (trigger `BEFORE INSERT ON itens_pedido WHEN NEW.produto_id=2 BEGIN SELECT RAISE(ABORT,'forced'); END`) num pedido de itens [1, 2] → 500, nenhuma linha nova em `pedidos`/`itens_pedido` mesmo após outra requisição de escrita, estoque do produto 1 inalterado; admin DELETE /produtos/<id com pedidos> → 200, depois `SELECT COUNT(*) FROM itens_pedido i LEFT JOIN produtos p ON p.id=i.produto_id WHERE p.id IS NULL` → 0 e GET /pedidos mostra o `produto_nome` original. Upgrade path: as mesmas checagens de estoque e de órfãos num banco criado pelo código original.

### [HIGH] Missing authentication / authorization (AP-11)
File: app.py:11-30
Description: Todas as rotas são registradas sem nenhum guard: GET /usuarios, GET /usuarios/<id>, GET /pedidos, GET /pedidos/usuario/<id>, PUT /pedidos/<id>/status, GET /relatorios/vendas e POST/PUT/DELETE /produtos.
Impact: Qualquer anônimo lista usuários e pedidos de todos, muda status de pedidos, lê o faturamento e altera ou apaga o catálogo.
Recommendation: P-16 — tokens Bearer assinados (`itsdangerous`) com `require_auth`, `require_admin`, `require_self_or_admin` em `src/middlewares/auth.py`, aplicados nos blueprints segundo a política da Decisão 1.
Verification: anônimo em GET /usuarios, GET /usuarios/2, GET /pedidos, GET /pedidos/usuario/2, PUT /pedidos/1/status, GET /relatorios/vendas, POST /produtos, PUT /produtos/1, DELETE /produtos/1, POST /pedidos → 401; joao em GET /usuarios, GET /pedidos, PUT /pedidos/1/status, GET /relatorios/vendas, POST/PUT/DELETE /produtos → 403; joao em GET /usuarios/3 e GET /pedidos/usuario/3 (dados de maria) → 403; joao em GET /usuarios/2 e GET /pedidos/usuario/2 → 200; admin em todas → status do baseline; header `Authorization: Bearer forjado` → 401.

### [HIGH] Missing authentication / authorization (AP-11)
File: controllers.py:176-180, 195-203
Description: `login` devolve só os dados do usuário, sem nenhum token; `criar_pedido` usa `usuario_id` do corpo como dono do pedido.
Impact: Qualquer um cria pedidos em nome de outro usuário (e baixa estoque na conta dele); não existe credencial para proteger as demais rotas.
Recommendation: P-16 — login devolve `token`; o dono do pedido vem do token (`owner_for`), em `src/controllers/pedido_controller.py`.
Verification: POST /login (joao) → 200 com chave `token`; joao POST /pedidos {"usuario_id":3,"itens":[...]} → 403 e nenhuma linha nova; joao sem `usuario_id` → 201 e `SELECT usuario_id FROM pedidos WHERE id=<novo>` → 2; admin com `usuario_id`:3 → 201 com dono 3; joao GET /pedidos/usuario/3 não mostra pedido algum criado por joao.

### [HIGH] Debug mode and unsafe defaults in the entry point (AP-12)
File: app.py:8-9, 88
Description: `app.config["DEBUG"] = True`, `CORS(app)` sem lista de origens e `app.run(host="0.0.0.0", port=5000, debug=True)`.
Impact: O debugger do Werkzeug exposto em todas as interfaces permite execução remota de código; qualquer site pode chamar a API pelo navegador da vítima.
Recommendation: P-01 — debug desligado, bind em `127.0.0.1` (`HOST=0.0.0.0` é opt-in), CORS só para origens de `CORS_ORIGINS` (vazio por padrão), em `src/config/settings.py`.
Verification: `ss -ltnp | grep 5000` → `127.0.0.1:5000`; log do boot sem "Debugger is active" e com "Debug mode: off"; `curl -si -X OPTIONS -H "Origin: http://evil.example" -H "Access-Control-Request-Method: GET" localhost:5000/produtos` → sem header `Access-Control-Allow-Origin`.

### [MEDIUM] N+1 queries (AP-13)
File: models.py:139-140, 154-155, 177-199, 209-231, 239-254
Description: `get_pedidos_usuario` e `get_todos_pedidos` fazem um SELECT de itens por pedido e um SELECT de produto por item (`cursor2`, `cursor3`); `criar_pedido` faz SELECT por item duas vezes; `relatorio_vendas` faz cinco consultas separadas de COUNT/SUM.
Impact: O número de queries cresce linearmente com pedidos e itens; listagens ficam lentas com volume.
Recommendation: P-09 — um JOIN agrupado em memória para pedidos, um `SELECT ... WHERE id IN (...)` para os produtos do pedido, um `GROUP BY status` para o relatório.
Verification: contando statements via `set_trace_callback` num script de validação com `app.test_client()`: GET /pedidos com 1 pedido e com 5 pedidos → mesma contagem; GET /pedidos/usuario/2 idem; GET /relatorios/vendas → no máximo 2 SELECTs; POST /pedidos com 3 itens → 1 SELECT em `produtos`.

### [MEDIUM] Duplicated logic (AP-14)
File: controllers.py:28-50, 72-90
Description: `criar_produto` e `atualizar_produto` repetem a mesma sequência de `if "nome" not in dados` / `preco < 0` / `estoque < 0`, e o update ainda omite tamanho de nome e categoria.
Impact: As duas cópias já divergiram: o PUT aceita nome de 1 caractere e categoria inexistente que o POST rejeita.
Recommendation: P-12 — `validar_produto` único em `src/controllers/validators.py`, chamado por create e update com as mensagens originais.
Verification: admin POST e PUT /produtos/1 com cada um destes → 400 com a mesma mensagem nos dois: {"nome":"A","preco":1,"estoque":1}, {"nome":"Teste","preco":1,"estoque":1,"categoria":"xyz"}, {"nome":"Teste","preco":-1,"estoque":1}, {"nome":"Teste","preco":1} (hoje o PUT responde 200 nos dois primeiros); `grep -rn "Nome é obrigatório" --include='*.py' --exclude-dir=.claude --exclude-dir=.venv . | wc -l` → 1.

### [MEDIUM] Duplicated logic (AP-14)
File: models.py:12-21, 31-40, 79-86, 95-102, 178-199, 211-231, 304-313
Description: O dict de produto é montado campo a campo três vezes, o de usuário duas, e o bloco inteiro de montagem de pedido + itens está copiado entre `get_pedidos_usuario` e `get_todos_pedidos`.
Impact: Mudar um campo exige editar várias cópias; foi assim que `senha` ficou exposta nas duas de usuário.
Recommendation: P-12 — um serializer por entidade (`_produto_dict`, `_usuario_dict`, `_montar_pedidos`) nos models.
Verification: `grep -rn '"descricao": row\["descricao"\]' --include='*.py' --exclude-dir=.claude --exclude-dir=.venv . | wc -l` → 1; idem para `'"tipo": row\["tipo"\]'` → 1 e `'"preco_unitario":'` → 1; as respostas de GET /produtos, /produtos/busca, /produtos/1, /usuarios, /pedidos mantêm as chaves do baseline.

### [MEDIUM] Missing or inconsistent input validation (AP-15)
File: controllers.py:43-45, 87-90, 118-121, 153-158, 169-171, 195-201, 239-245
Description: `preco`/`estoque` são comparados sem checar tipo (string → TypeError 500, `NaN` passa); `float(preco_min)` sem tratamento; `dados.get(...)` sobre corpo `None` em `login` e `atualizar_status_pedido`; itens de pedido sem validação de `quantidade`; e-mail sem formato; status atualizado em pedido inexistente responde 200.
Impact: Entradas comuns derrubam a rota com 500; quantidade negativa cria pedido de total negativo e aumenta o estoque.
Recommendation: P-12 — validators em `src/controllers/validators.py` (tipos, números finitos, inteiros ≥ 1 para quantidade, regex de e-mail), `NotFoundError` para pedido inexistente.
Verification: admin POST /produtos {"nome":"Mouse","preco":"abc","estoque":1} → 400 (hoje 500); corpo bruto `{"nome":"Mouse","preco":NaN,"estoque":1}` → 400 (hoje 201); `"estoque":1.5` → 400; GET /produtos/busca?preco_min=abc → 400 (hoje 500); POST /login com corpo `null` → 400 (hoje 500); admin PUT /pedidos/1/status sem corpo → 400 (hoje 500); admin PUT /pedidos/9999/status {"status":"aprovado"} → 404 (hoje 200); joao POST /pedidos com `quantidade` -1, 0 e "x" → 400 e estoque inalterado (hoje -1 → 201); POST /usuarios com email "nao-e-email" → 400 (hoje 201).

### [MEDIUM] Missing or inconsistent input validation (AP-15)
File: database.py:27-34
Description: A tabela `usuarios` não tem restrição de unicidade em `email` e nada no código checa duplicidade.
Impact: Dois cadastros com o mesmo e-mail (ou variação de caixa) coexistem; o login passa a depender de qual linha o banco devolve primeiro.
Recommendation: P-12 — `CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email COLLATE NOCASE)` no boot (com saneamento de duplicatas pré-existentes), `IntegrityError` → 409.
Verification: 20 POST /usuarios concorrentes com "dup@x.com" alternando com "DUP@X.COM" → exatamente 1 × 201 e 19 × 409, `SELECT COUNT(*) FROM usuarios WHERE lower(email)='dup@x.com'` → 1; POST /usuarios com "ADMIN@LOJA.COM" → 409. Upgrade path: num banco criado pelo código original, após o boot refatorado o índice existe (`SELECT name FROM sqlite_master WHERE name='idx_usuarios_email'` → 1 linha) e o mesmo teste concorrente dá 1 × 201.

### [MEDIUM] Scattered or leaky error handling (AP-16)
File: app.py:77-78
Description: `executar_query` captura `Exception` e devolve `{"erro": str(e)}` com 500.
Impact: Mensagens internas do SQLite (nomes de tabelas, sintaxe) vazam ao cliente.
Recommendation: P-10 — handler central em `src/middlewares/error_handler.py`; a rota só levanta `ValidationError`.
Verification: `grep -nE "except|str\(e\)" app.py` → nenhum hit; admin POST /admin/query {"consulta":"inexistente"} → 400 {"erro":"Consulta não permitida","sucesso":false}.

### [MEDIUM] Scattered or leaky error handling (AP-16)
File: controllers.py:10-12, 21-22, 60-62, 95-96, 108-109, 125-126, 133-134, 143-144, 164-165, 185-186, 218-220, 226-227, 234-235, 254-255, 261-262, 291-292
Description: Cada um dos 16 handlers embrulha tudo em `try/except Exception` e devolve `jsonify({"erro": str(e)}), 500`.
Impact: Erros de validação viram 500, e o texto das exceções (SQL, tipos Python) chega ao cliente.
Recommendation: P-10 — handlers sem `try`; `AppError` → status próprio, exceção inesperada → 500 genérico com stack só no log; formato `{"erro": ...}` preservado.
Verification: G 'except Exception|str\(e\)' → nenhum hit; falha forçada (trigger `RAISE(ABORT,'forced')` em `pedidos`) num POST /pedidos → 500 `{"erro":"Erro interno do servidor","sucesso":false}`, "forced" ausente do corpo e presente no log; GET /rota-inexistente → 404 (não 500).

### [MEDIUM] Configuration in code instead of a config module (AP-18)
File: app.py:85, 88
Description: Host, porta e URL do banner (`"0.0.0.0"`, `5000`, `"http://localhost:5000"`) são literais no ponto de entrada.
Impact: Mudar porta ou interface exige editar código.
Recommendation: P-01 — `HOST`, `PORT` em `src/config/settings.py`.
Verification: `grep -rnE 'port=5000|localhost:5000|"0\.0\.0\.0"' --include='*.py' --exclude-dir=.claude --exclude-dir=.venv --exclude-dir=config .` → nenhum hit.

### [MEDIUM] Configuration in code instead of a config module (AP-18)
File: controllers.py:285-288
Description: `health_check` responde literais `"versao": "1.0.0"`, `"ambiente": "producao"`, `"db_path": "loja.db"`, `"debug": True`, sem relação com a configuração real.
Impact: O health mente sobre o ambiente (diz "producao" com debug ligado) e precisa ser editado à mão a cada mudança.
Recommendation: P-01 — `APP_VERSION` em `src/config/settings.py`, lido pelo controller de sistema; os demais campos saem (Decisão 5).
Verification: `grep -rnE '"producao"|"1\.0\.0"' --include='*.py' --exclude-dir=.claude --exclude-dir=.venv --exclude-dir=config .` → nenhum hit; GET /health e GET / mostram `versao` igual ao baseline.

### [MEDIUM] Configuration in code instead of a config module (AP-18)
File: database.py:5
Description: `db_path = "loja.db"` fixo no módulo de banco.
Impact: Não dá para apontar outro arquivo (teste, staging) sem editar código.
Recommendation: P-01 — `DATABASE_PATH` em `src/config/settings.py`, injetado no `Database`.
Verification: `grep -rnE 'loja\.db' --include='*.py' --exclude-dir=.claude --exclude-dir=.venv --exclude-dir=config .` → nenhum hit.

### [LOW] Magic numbers and strings (AP-19)
File: controllers.py:47-54, 242
Description: Limites `2` e `200` de nome, a lista de categorias e a lista de status aparecem inline nos handlers.
Impact: Regras de domínio espalhadas e repetidas; mudar um limite exige caçar literais.
Recommendation: P-14 — `NOME_MIN`, `NOME_MAX`, `CATEGORIAS_VALIDAS`, `STATUS_PEDIDO` em `src/models/constants.py`.
Verification: `grep -rnE 'len\(nome\) *[<>] *[0-9]|"informatica", "moveis"|\["pendente", "aprovado"' --include='*.py' --exclude-dir=.claude --exclude-dir=.venv --exclude=constants.py .` → nenhum hit.

### [LOW] Magic numbers and strings (AP-19)
File: models.py:247, 250, 253, 257-262
Description: Faixas de desconto `10000/0.1`, `5000/0.05`, `1000/0.02` e status `'pendente'`, `'aprovado'`, `'cancelado'` como literais dentro de `relatorio_vendas`.
Impact: Política comercial escondida em números soltos no model.
Recommendation: P-14 — `FAIXAS_DESCONTO` e constantes de status em `src/models/constants.py`, usadas por `src/services/relatorio_service.py`.
Verification: `grep -rnE 'faturamento > [0-9]|faturamento \* 0\.|status = .(pendente|aprovado|cancelado).' --include='*.py' --exclude-dir=.claude --exclude-dir=.venv --exclude=constants.py .` → nenhum hit; GET /relatorios/vendas → mesmos valores do baseline.

### [LOW] Poor naming (AP-20)
File: controllers.py:14, 56, 64, 98, 136, 160
Description: O parâmetro e as variáveis `id` sombreiam o builtin e não dizem de qual entidade são.
Impact: Leitura ambígua e builtin indisponível dentro das funções.
Recommendation: P-14 — `produto_id`, `usuario_id` (o caminho público da URL não muda).
Verification: `grep -rnE 'def [a-z_]+\((self, )?id\)|^\s+id = ' --include='*.py' --exclude-dir=.claude --exclude-dir=.venv .` → nenhum hit.

### [LOW] Poor naming (AP-20)
File: models.py:24, 54, 65, 89, 187, 191, 193, 219, 223, 225
Description: `cursor2`, `cursor3`, `prod` e parâmetros `id` nas funções de produto/usuário.
Impact: Nomes numerados e abreviados escondem o papel de cada variável.
Recommendation: P-14 — nomes de domínio (`produto_id`, `itens`, `produto`).
Verification: `grep -rnE 'cursor[23]\b|\bprod\b|def [a-z_]+\((self, )?id(,|\))' --include='*.py' --exclude-dir=.claude --exclude-dir=.venv .` → nenhum hit.

### [LOW] Unused imports and dead code (AP-21)
File: database.py:2
Description: `import os` nunca é usado.
Impact: Ruído e dependência aparente que não existe.
Recommendation: remover.
Verification: checagem com `ast` (cada nome importado é referenciado no próprio arquivo) sobre `app.py` e `src/**/*.py` → 0 não usados (hoje acusa `database.py: os`).

### [LOW] Unused imports and dead code (AP-21)
File: models.py:2
Description: `import sqlite3` nunca é usado.
Impact: Ruído e dependência aparente que não existe.
Recommendation: remover.
Verification: a mesma checagem com `ast` → 0 não usados (hoje acusa `models.py: sqlite3`).

### [LOW] Print-debugging instead of logging (AP-22)
File: app.py:56, 83-86
Description: `print("!!! BANCO DE DADOS RESETADO !!!")` e o banner `print("=" * 50)`.
Impact: Sem nível, sem timestamp, impossível filtrar ou redirecionar.
Recommendation: P-15 — `logging` configurado em `create_app`.
Verification: `grep -nE '\bprint\(' app.py` → nenhum hit; o log do reset aparece via logger com nível.

### [LOW] Print-debugging instead of logging (AP-22)
File: controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248, 250
Description: Todos os eventos (criação, login, erros, notificações simuladas) são `print(...)`.
Impact: Sem nível, sem timestamp, impossível filtrar; e-mails de login vão crus para stdout.
Recommendation: P-15 — `logger` por módulo; notificações via `NotificationService` que loga.
Verification: G '\bprint\(' → nenhum hit em todo o projeto.

### [LOW] Verbose control flow (AP-23)
File: controllers.py:200
Description: `if not itens or len(itens) == 0` repete a mesma condição.
Impact: Ruído de leitura.
Recommendation: P-14 — `if not itens`.
Verification: `grep -rnE 'len\(itens\) == 0' --include='*.py' --exclude-dir=.claude --exclude-dir=.venv .` → nenhum hit.

### [LOW] Verbose control flow (AP-23)
File: models.py:137, 146
Description: Acumulação manual `total = total + (produto["preco"] * item["quantidade"])` num loop.
Impact: Ruído de leitura onde um `sum()` basta.
Recommendation: P-14 — `sum(...)`.
Verification: `grep -rnE 'total = total \+' --include='*.py' --exclude-dir=.claude --exclude-dir=.venv .` → nenhum hit.

================================
Total: 41 findings
================================

## Decisions requiring approval
1. Autenticação por token Bearer — AP-11 exige credencial — default: POST /login passa a devolver também `token` (assinado com `itsdangerous`, 24h; com `SECRET_KEY` gerada no boot, tokens caem ao reiniciar). Públicas: GET /, GET /health, GET /produtos, GET /produtos/busca, GET /produtos/<id>, POST /usuarios, POST /login. Dono ou admin: GET /usuarios/<id>, GET /pedidos/usuario/<id>. Autenticado: POST /pedidos. Só admin: POST/PUT/DELETE /produtos, GET /usuarios, GET /pedidos, PUT /pedidos/<id>/status, GET /relatorios/vendas, POST /admin/reset-db, POST /admin/query. Sem token → 401 e sem permissão → 403.
2. Dono do pedido vem do token — AP-11 — default: em POST /pedidos, `usuario_id` passa a ser opcional (ausente = o próprio usuário); um não-admin que indicar outro usuário recebe 403; o admin pode indicar qualquer usuário. A antiga resposta 400 "Usuario ID é obrigatório" deixa de existir para quem está autenticado.
3. /admin/query não executa mais SQL livre — AP-04 — default: aceita `{"consulta": "<nome>"}` só da allow-list `produtos_sem_estoque`, `pedidos_por_status`, `vendas_por_produto` (leituras fixas e sem colunas de credencial); `{"sql": ...}` ou nome desconhecido → 400 "Consulta não permitida". A resposta mantém `dados` e `sucesso`.
4. /admin/reset-db só para admin — AP-04 — default: mesmo efeito (esvazia as quatro tabelas), mesma resposta.
5. Campos removidos de respostas — AP-01/AP-06/AP-18 — default: `senha` sai de GET /usuarios e GET /usuarios/<id>; GET /health perde `secret_key`, `db_path`, `debug` e `ambiente` (mantém `status`, `database`, `counts` e `versao`).
6. Hash de senha (scrypt via werkzeug) e senhas do seed — AP-01/AP-05 — default: num banco novo, admin/joao/maria recebem as senhas de `ADMIN_PASSWORD`/`JOAO_PASSWORD`/`MARIA_PASSWORD`, ou senhas geradas e exibidas uma vez no log do boot. Num banco existente, no boot: as três contas do seed que ainda estiverem com senha em texto puro recebem senha nova (pela variável ou gerada e exibida), e os padrões antigos deixam de funcionar; as demais senhas em texto puro viram hash no lugar, e esses usuários continuam entrando com a própria senha.
7. E-mail único e válido — AP-15 — default: índice único sem diferenciar maiúsculas de minúsculas; cadastro duplicado → 409 "Email já cadastrado"; formato inválido → 400. Num banco existente com duplicatas, a linha mais antiga fica e o e-mail das demais é renomeado para `duplicado-<id>+<email>`, com registro no log.
8. DELETE /produtos/<id> vira exclusão lógica (`ativo = 0`) — AP-10 — default: continua respondendo 200 e o produto some de GET /produtos, /busca e /produtos/<id> (que responde 404); não aceita mais pedidos; os pedidos antigos mantêm `produto_nome`.
9. Validação mais estrita — AP-14/AP-15 — default: as entradas listadas em AP-15 passam de 500/200/201 para 400; o PUT /produtos aplica as mesmas regras do POST; PUT /pedidos/<id>/status de pedido inexistente → 404; o mesmo produto repetido nos itens tem as quantidades somadas antes da checagem de estoque. As mensagens originais ficam onde já existiam.
10. Erros centralizados — AP-16 — default: o formato `{"erro": ...}` é mantido; erro inesperado → 500 `{"erro": "Erro interno do servidor", "sucesso": false}` com o detalhe só no log; 404/405 de rotas inexistentes continuam com a resposta nativa do Flask; health com falha no banco mantém `{"status": "erro", "detalhes": ...}` com mensagem genérica.
11. Padrões seguros do servidor — AP-12 — default: debug desligado, escuta em 127.0.0.1 (`HOST=0.0.0.0` só por opt-in), CORS só para as origens em `CORS_ORIGINS` (vazio por padrão = nenhuma origem cruzada). `python app.py` continua subindo sem nenhuma variável de ambiente.

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
