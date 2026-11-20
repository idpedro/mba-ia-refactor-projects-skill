# code-smells-project

API de E-commerce em Python/Flask usada como entrada do desafio `refactor-arch`, refatorada para MVC.

## Como rodar

```bash
pip install -r requirements.txt
python app.py
```

A aplicação sobe em `http://127.0.0.1:5000` sem nenhuma variável de ambiente. O banco SQLite (`loja.db`) é criado automaticamente no primeiro boot, com produtos e usuários de exemplo.

### Contas de exemplo

O seed cria `admin@loja.com` (admin), `joao@email.com` e `maria@email.com` (clientes). As senhas vêm de `ADMIN_PASSWORD`, `JOAO_PASSWORD` e `MARIA_PASSWORD`; se não estiverem definidas, o boot gera senhas aleatórias e as exibe **uma única vez** no log. Num banco criado pela versão anterior, o boot migra as senhas para hash (scrypt) e substitui as senhas padrão antigas dessas três contas.

### Configuração

Todas as variáveis são opcionais; veja `.env.example`. Por padrão: debug desligado, escuta só em `127.0.0.1` (`HOST=0.0.0.0` para expor), nenhuma origem CORS liberada (`CORS_ORIGINS`), e `SECRET_KEY` gerada no boot (os tokens deixam de valer ao reiniciar).

## Autenticação

`POST /login` devolve `token`; envie-o como `Authorization: Bearer <token>`.

| Acesso | Rotas |
|---|---|
| Público | `GET /`, `GET /health`, `GET /produtos`, `GET /produtos/busca`, `GET /produtos/<id>`, `POST /usuarios`, `POST /login` |
| Autenticado | `POST /pedidos` (o dono é o usuário do token; admin pode informar `usuario_id`) |
| Dono ou admin | `GET /usuarios/<id>`, `GET /pedidos/usuario/<id>` |
| Admin | `POST/PUT/DELETE /produtos`, `GET /usuarios`, `GET /pedidos`, `PUT /pedidos/<id>/status`, `GET /relatorios/vendas`, `POST /admin/reset-db`, `POST /admin/query` |

`POST /admin/query` aceita `{"consulta": "<nome>"}` com um destes nomes: `produtos_sem_estoque`, `pedidos_por_status`, `vendas_por_produto`. SQL livre não é executado.

## Estrutura

```
app.py                  # ponto de entrada (python app.py)
src/
├── app.py              # create_app(): composition root
├── config/settings.py  # configuração via ambiente
├── database.py         # conexão por requisição, schema, migrações, seed
├── errors.py           # erros de domínio
├── models/             # persistência (produto, usuario, pedido, sistema) e constantes
├── controllers/        # casos de uso e validação
├── services/           # notificações e relatório de vendas
├── views/              # blueprints (rotas)
└── middlewares/        # auth e tratamento central de erros
```
