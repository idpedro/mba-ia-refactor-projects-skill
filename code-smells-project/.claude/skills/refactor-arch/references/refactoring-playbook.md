# Refactoring playbook

Concrete transformations for Phase 3, keyed by `P-xx` (referenced from `anti-patterns.md`). Examples show Python/Flask and Node/Express; translate the same move to other stacks.

Each pattern keeps the HTTP contract unless the Phase 2 decisions say otherwise.

---

## P-01 Externalize configuration and secrets
Fixes AP-01, AP-12, AP-18.

**Before**
```python
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
app.run(host="0.0.0.0", port=5000, debug=True)
```
**After** — `src/config/settings.py`
```python
import os
import secrets

class Settings:
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5000"))
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "loja.db")
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")
```
```python
app.config.from_object(Settings)
CORS(app, origins=Settings.CORS_ORIGINS)
app.run(host=Settings.HOST, port=Settings.PORT, debug=Settings.DEBUG)
```
**Node**
```js
// before: const config = { dbPass: "senha_super_secreta_prod_123", paymentGatewayKey: "pk_live_...", port: 3000 };
// after: src/config/index.js
module.exports = {
  port: Number(process.env.PORT) || 3000,
  paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || '',
  dbPath: process.env.DB_PATH || ':memory:',
};
```
Add `.env.example` with every variable (no real values). The host default changes to `127.0.0.1` only if the decisions approved it; otherwise keep the original host but still read it from config.

---

## P-02 Parameterized queries
Fixes AP-02.

**Before**
```python
cursor.execute("SELECT * FROM produtos WHERE id = " + str(id))
query += " AND (nome LIKE '%" + termo + "%' OR descricao LIKE '%" + termo + "%')"
```
**After**
```python
cursor.execute("SELECT * FROM produtos WHERE id = ?", (id,))

clauses, params = ["1=1"], []
if termo:
    clauses.append("(nome LIKE ? OR descricao LIKE ?)")
    params += [f"%{termo}%", f"%{termo}%"]
if categoria:
    clauses.append("categoria = ?")
    params.append(categoria)
cursor.execute(f"SELECT * FROM produtos WHERE {' AND '.join(clauses)}", params)
```
The f-string only joins fixed clause text; every value goes through `params`. Node: `db.get("SELECT * FROM users WHERE id = ?", [id])`. ORMs: use filter expressions, never `text()` with interpolation.

---

## P-03 Split a God class / module by layer and domain
Fixes AP-03.

**Before** — one class does schema, routing, SQL and rules
```js
class AppManager {
  constructor() { this.db = new sqlite3.Database(':memory:'); }
  initDb() { /* CREATE TABLE ... INSERT seeds */ }
  setupRoutes(app) {
    app.post('/api/checkout', (req, res) => { /* 50 lines: SQL + payment + enrollment */ });
    app.get('/api/admin/financial-report', (req, res) => { /* nested queries */ });
  }
}
```
**After**
```js
// src/database/connection.js   — opens the db, exposes promisified run/get/all
// src/database/schema.js       — CREATE TABLE + seeds
// src/models/course.model.js   — findActiveById(id)
// src/models/user.model.js     — findByEmail(email), create(...), deleteById(id)
// src/services/payment.service.js — charge(card, amount)
// src/controllers/checkout.controller.js — checkout(input): orchestrates the use case
// src/routes/checkout.routes.js — router.post('/api/checkout', ...)
// src/app.js — composition root wiring all of the above
```
Move code verbatim first, boot, then improve it inside its new home. Split by domain (one model/controller per entity) when a file spans several domains.

---

## P-04 Hash passwords with a real KDF
Fixes AP-05.

**Before**
```python
self.password = hashlib.md5(pwd.encode()).hexdigest()
```
```js
function badCrypto(pwd) { /* base64 loop */ }
```
**After** — Python (ships with Flask via Werkzeug)
```python
from werkzeug.security import generate_password_hash, check_password_hash

def set_password(self, raw):
    self.password = generate_password_hash(raw)

def check_password(self, raw):
    return check_password_hash(self.password, raw)
```
**Node** (built-in `crypto`)
```js
const crypto = require('crypto');

function hashPassword(raw) {
  const salt = crypto.randomBytes(16).toString('hex');
  const hash = crypto.scryptSync(raw, salt, 64).toString('hex');
  return `${salt}:${hash}`;
}

function verifyPassword(raw, stored) {
  const [salt, hash] = stored.split(':');
  const candidate = crypto.scryptSync(raw, salt, 64);
  return crypto.timingSafeEqual(candidate, Buffer.from(hash, 'hex'));
}
```
Login by plaintext comparison in SQL (`WHERE email = ? AND senha = ?`) becomes: fetch by email, then `check_password`. Hash seed passwords at seed time. Existing persisted hashes stop matching: re-seed, or keep a legacy-format fallback, per the approved decision.

---

## P-05 Remove sensitive data from responses, logs and open endpoints
Fixes AP-04, AP-06.

**Before**
```python
def to_dict(self):
    return {"id": self.id, "email": self.email, "password": self.password}
```
```python
return jsonify({"status": "ok", "secret_key": "minha-chave-super-secreta-123", "db_path": "loja.db"})
```
```js
console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`);
```
**After**
```python
def to_dict(self):
    return {"id": self.id, "email": self.email}
```
```python
return jsonify({"status": "ok", "database": "connected"})
```
```js
logger.info(`Processing card ending ${card.slice(-4)}`);
```
Dangerous admin endpoints keep their route and require the admin role through P-16:
```python
@admin_bp.post("/admin/reset-db")
@require_admin
def reset_db():
    return jsonify(admin_controller.reset_database()), 200
```
Role from the request body: ignore it on public sign-up (`role = "user"`).

---

## P-06 Move business rules out of routes into controllers/services
Fixes AP-07.

**Before**
```python
def criar_pedido():
    dados = request.get_json()
    ...
    resultado = models.criar_pedido(usuario_id, itens)
    print("ENVIANDO EMAIL: Pedido " + str(resultado["pedido_id"]) + " criado")
    print("ENVIANDO SMS: Seu pedido foi recebido!")
    return jsonify({"dados": resultado, "sucesso": True}), 201
```
**After**
```python
# src/views/pedido_routes.py
@pedido_bp.post("/pedidos")
def criar_pedido():
    resultado = pedido_controller.criar(request.get_json(silent=True))
    return jsonify({"dados": resultado, "sucesso": True, "mensagem": "Pedido criado com sucesso"}), 201

# src/controllers/pedido_controller.py
class PedidoController:
    def __init__(self, pedido_model, notification_service):
        self.pedidos = pedido_model
        self.notifications = notification_service

    def criar(self, dados):
        payload = validar_pedido(dados)            # raises ValidationError
        resultado = self.pedidos.criar(payload["usuario_id"], payload["itens"])
        self.notifications.pedido_criado(resultado["pedido_id"], payload["usuario_id"])
        return resultado
```
Same move for rules like discount tiers, payment approval, overdue computation and report aggregation: they land in a controller or service method the route calls in one line.

---

## P-07 Dependency injection through a composition root
Fixes AP-08.

**Before**
```python
# models.py
from database import get_db
def get_todos_produtos():
    db = get_db()
```
**After** — Flask app factory
```python
# src/app.py
def create_app(settings=Settings):
    app = Flask(__name__)
    app.config.from_object(settings)
    db = Database(settings.DATABASE_PATH)
    db.init_schema()

    produtos = ProdutoModel(db)
    app.register_blueprint(build_produto_routes(ProdutoController(produtos)))
    register_error_handlers(app)
    return app
```
```python
# src/views/produto_routes.py
def build_produto_routes(controller):
    bp = Blueprint("produtos", __name__)

    @bp.get("/produtos")
    def listar():
        return jsonify({"dados": controller.listar(), "sucesso": True}), 200

    return bp
```
**Node**
```js
// src/app.js
const db = createConnection(config.dbPath);
await initSchema(db);
const courseModel = new CourseModel(db);
const checkoutController = new CheckoutController({ courseModel, userModel, paymentService });
app.use(checkoutRoutes(checkoutController));
app.use(errorHandler);
```
For Flask-SQLAlchemy, `db = SQLAlchemy()` plus `db.init_app(app)` inside `create_app()` is the accepted pattern; inject services into controllers.

---

## P-08 Replace mutable global state
Fixes AP-09.

**Before**
```js
let globalCache = {};
function logAndCache(key, data) { globalCache[key] = data; }
module.exports = { globalCache, totalRevenue };
```
**After**
```js
// src/services/cache.service.js
class CacheService {
  constructor() { this.store = new Map(); }
  set(key, value) { this.store.set(key, value); }
  get(key) { return this.store.get(key); }
}
module.exports = CacheService;
// one instance created in app.js and injected where needed
```
Python: replace `global db_connection` with a `Database` object created in `create_app()` and passed to models; replace in-memory lists used as storage with a table, or keep them on an injected instance when persistence is out of scope.

---

## P-09 Eliminate N+1 queries
Fixes AP-13.

**Before**
```python
for row in pedidos:
    cursor.execute("SELECT * FROM itens_pedido WHERE pedido_id = " + str(row["id"]))
    for item in cursor.fetchall():
        cursor.execute("SELECT nome FROM produtos WHERE id = " + str(item["produto_id"]))
```
**After** — one JOIN, grouped in memory
```python
rows = db.execute("""
    SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,
           i.produto_id, i.quantidade, i.preco_unitario, pr.nome AS produto_nome
    FROM pedidos p
    LEFT JOIN itens_pedido i ON i.pedido_id = p.id
    LEFT JOIN produtos pr ON pr.id = i.produto_id
    ORDER BY p.id
""").fetchall()

pedidos = {}
for r in rows:
    pedido = pedidos.setdefault(r["id"], {
        "id": r["id"], "usuario_id": r["usuario_id"], "status": r["status"],
        "total": r["total"], "criado_em": r["criado_em"], "itens": [],
    })
    if r["produto_id"] is not None:
        pedido["itens"].append({
            "produto_id": r["produto_id"],
            "produto_nome": r["produto_nome"] or "Desconhecido",
            "quantidade": r["quantidade"],
            "preco_unitario": r["preco_unitario"],
        })
return list(pedidos.values())
```
**SQLAlchemy**
```python
from sqlalchemy.orm import joinedload
tasks = db.session.scalars(
    db.select(Task).options(joinedload(Task.user), joinedload(Task.category))
).unique().all()
```
**Counts** — one `GROUP BY` instead of one query per status
```python
counts = dict(db.session.execute(
    db.select(Task.status, db.func.count()).group_by(Task.status)
).all())
pending = counts.get("pending", 0)
```

---

## P-10 Centralized error handling
Fixes AP-16.

**Before**
```python
def buscar_produto(id):
    try:
        ...
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
```
**After** — `src/middlewares/error_handler.py`
```python
import logging
from flask import jsonify

logger = logging.getLogger(__name__)

class AppError(Exception):
    status = 500
    def __init__(self, message):
        super().__init__(message)
        self.message = message

class ValidationError(AppError): status = 400
class NotFoundError(AppError): status = 404
class ForbiddenError(AppError): status = 403

def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify({"erro": err.message, "sucesso": False}), err.status

    @app.errorhandler(HTTPException)        # from werkzeug.exceptions
    def handle_http_error(err):
        return jsonify({"erro": err.description, "sucesso": False}), err.code

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        logger.exception("Unhandled error")
        return jsonify({"erro": "Erro interno do servidor", "sucesso": False}), 500
```
The `HTTPException` handler matters: without it the catch-all turns Flask's own 404/405 into 500. Keep the error key the project already uses (`erro`, `error`). Handlers drop their `try/except` and raise `NotFoundError(...)` instead.

**Node**
```js
// src/middlewares/errorHandler.js
module.exports = (err, req, res, next) => {
  const status = err.status || 500;
  if (status === 500) console.error(err);
  res.status(status).json({ error: status === 500 ? 'Internal server error' : err.message });
};
// routes: wrap async handlers so rejections reach it
const asyncHandler = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);
```
Express 4 does not forward rejected promises on its own, hence `asyncHandler`. If a route originally answered plain text (`res.send("Curso não encontrado")`), keep the same status code; changing the body format is a decision.

---

## P-11 Atomic writes and flattened callbacks
Fixes AP-10.

**Before** — four nested callbacks, no transaction
```js
db.run("INSERT INTO enrollments ...", [userId, cid], function (err) {
  self.db.run("INSERT INTO payments ...", [this.lastID, course.price, status], function (err) {
    self.db.run("INSERT INTO audit_logs ...", [...], (err) => { res.json(...); });
  });
});
```
**After** — promisified driver + transaction
```js
// src/database/connection.js
const run = (db, sql, params = []) => new Promise((resolve, reject) =>
  db.run(sql, params, function (err) { err ? reject(err) : resolve({ lastID: this.lastID, changes: this.changes }); }));
const get = (db, sql, params = []) => new Promise((resolve, reject) =>
  db.get(sql, params, (err, row) => (err ? reject(err) : resolve(row))));
const all = (db, sql, params = []) => new Promise((resolve, reject) =>
  db.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows))));

async function transaction(db, work) {
  await run(db, 'BEGIN');
  try { const result = await work(); await run(db, 'COMMIT'); return result; }
  catch (err) { await run(db, 'ROLLBACK'); throw err; }
}
```
```js
// src/controllers/checkout.controller.js
const enrollmentId = await transaction(db, async () => {
  const { lastID } = await run(db, 'INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)', [userId, courseId]);
  await run(db, 'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)', [lastID, course.price, 'PAID']);
  await run(db, "INSERT INTO audit_logs (action, created_at) VALUES (?, datetime('now'))", [`Checkout curso ${courseId} por ${userId}`]);
  return lastID;
});
```
**Python sqlite3** — validate everything first, then write inside one transaction
```python
with self.db.connection:   # commits on success, rolls back on exception
    cur = self.db.connection.execute(
        "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, 'pendente', ?)", (usuario_id, total))
    pedido_id = cur.lastrowid
    for item in itens:
        self.db.connection.execute(
            "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
            (pedido_id, item["produto_id"], item["quantidade"], precos[item["produto_id"]]))
        self.db.connection.execute(
            "UPDATE produtos SET estoque = estoque - ? WHERE id = ?", (item["quantidade"], item["produto_id"]))
```
Orphans: delete children before the parent inside the same transaction (or declare `ON DELETE CASCADE`; SQLite needs `PRAGMA foreign_keys = ON`).

In-memory SQLite (`':memory:'`) with a promisified API: every `await` must use the **same** `Database` instance, and the server must start listening only after schema and seeds have resolved.

---

## P-12 Single validator and serializer per entity
Fixes AP-14, AP-15.

**Before** — copied into create and update
```python
if "nome" not in dados: return jsonify({"erro": "Nome é obrigatório"}), 400
if "preco" not in dados: return jsonify({"erro": "Preço é obrigatório"}), 400
if preco < 0: return jsonify({"erro": "Preço não pode ser negativo"}), 400
```
**After** — `src/controllers/validators.py` (or `src/validators/`)
```python
CATEGORIAS_VALIDAS = ("informatica", "moveis", "vestuario", "geral", "eletronicos", "livros")

def validar_produto(dados):
    if not isinstance(dados, dict):
        raise ValidationError("Dados inválidos")
    for campo, label in (("nome", "Nome"), ("preco", "Preço"), ("estoque", "Estoque")):
        if campo not in dados:
            raise ValidationError(f"{label} é obrigatório")
    if not isinstance(dados["preco"], (int, float)) or dados["preco"] < 0:
        raise ValidationError("Preço não pode ser negativo")
    ...
    return {
        "nome": dados["nome"], "descricao": dados.get("descricao", ""),
        "preco": dados["preco"], "estoque": dados["estoque"],
        "categoria": dados.get("categoria", "geral"),
    }
```
Both create and update call `validar_produto`, keeping the original messages so error bodies match the baseline. For serialization, the model's `to_dict()` is the single source; routes stop building dicts by hand and add computed fields (`overdue`) from a model method:
```python
def to_dict(self, include_overdue=False):
    data = {...}
    if include_overdue:
        data["overdue"] = self.is_overdue()
    return data
```
The flag keeps each endpoint's keys identical to the baseline: routes that returned `overdue` pass `include_overdue=True`, the rest keep the plain shape.

---

## P-13 Replace deprecated APIs
Fixes AP-17. Use the table in `anti-patterns.md`.

**Before**
```python
created_at = db.Column(db.DateTime, default=datetime.utcnow)
user = User.query.get(user_id)
```
**After**
```python
from datetime import datetime, timezone

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)   # naive UTC, same as the stored values

created_at = db.Column(db.DateTime, default=utcnow)
user = db.session.get(User, user_id)
```
Strip `tzinfo` when the column stores naive datetimes, so comparisons with existing rows (`due_date < now`) keep working and `str(created_at)` keeps its format.
```js
// before
const b = new Buffer(pwd);
// after
const b = Buffer.from(pwd);
```

---

## P-14 Named constants, clear names, plain control flow
Fixes AP-19, AP-20, AP-23.

**Before**
```python
if faturamento > 10000:
    desconto = faturamento * 0.1
elif faturamento > 5000:
    desconto = faturamento * 0.05

def is_admin(self):
    if self.role == 'admin':
        return True
    else:
        return False
```
```js
let u = req.body.usr; let e = req.body.eml; let cid = req.body.c_id;
```
**After**
```python
FAIXAS_DESCONTO = ((10000, 0.10), (5000, 0.05), (1000, 0.02))   # (faturamento mínimo, taxa)

def calcular_desconto(faturamento):
    for minimo, taxa in FAIXAS_DESCONTO:
        if faturamento > minimo:
            return faturamento * taxa
    return 0

def is_admin(self):
    return self.role == ROLE_ADMIN
```
```js
const { usr: name, eml: email, pwd: password, c_id: courseId, card } = req.body;
```
Request field names (`usr`, `eml`) stay as the public contract; only internal variables get renamed.

---

## P-15 Structured logging instead of print
Fixes AP-22.

**Before**
```python
print("Produto criado com ID: " + str(id))
print("ENVIANDO EMAIL: Pedido " + str(pedido_id))
```
**After**
```python
import logging
logger = logging.getLogger(__name__)

logger.info("Produto criado id=%s", id)
```
```python
# src/app.py inside create_app()
logging.basicConfig(level=settings.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
```
Simulated side effects (`print("ENVIANDO SMS...")`) move to a `NotificationService` whose methods log; the controller calls the service. Node: a tiny `logger.js` wrapping `console` with levels is enough when the project has no logging dependency.

---

## P-16 Authentication enforced by default
Fixes AP-11 (and the access side of AP-04).

The guard is on in the default configuration. No environment variable switches it off: a missing secret makes protected routes reject every request (fail closed), never accept them.

**Route policy** (state it in the Phase 2 decisions):
- Public: login, sign-up, health/index, and read-only catalog listings meant for anonymous visitors (e.g. `GET /produtos`).
- Authenticated: everything else that reads or changes data.
- Owner or admin: routes scoped to one user (`/usuarios/<id>`, `/pedidos/usuario/<id>`, `/users/<user_id>`).
- Admin only: listings of every user or order, status changes, reports, destructive and admin routes.
- `401` when the token is missing or invalid, `403` when the user lacks the role or ownership. Both go through the central error handler (P-10).

**Before**
```python
@user_bp.route('/login', methods=['POST'])
def login():
    ...
    return jsonify({'token': 'fake-jwt-token-' + str(user.id)})

@app.route("/usuarios", methods=["GET"])
def listar_usuarios():          # anyone can list every user
    ...
```
**After** (Flask): signed tokens with `itsdangerous`, which ships with Flask. `src/middlewares/auth.py`:
```python
from functools import wraps
from flask import current_app, g, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from src.errors import ForbiddenError, UnauthorizedError

def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="auth")

def issue_token(user_id):
    return _serializer().dumps({"uid": user_id})

def _current_user():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise UnauthorizedError("Token ausente")
    try:
        data = _serializer().loads(header[7:], max_age=current_app.config["TOKEN_MAX_AGE"])
    except (BadSignature, SignatureExpired):
        raise UnauthorizedError("Token inválido")
    user = current_app.extensions["user_model"].get_by_id(data["uid"])
    if user is None:
        raise UnauthorizedError("Token inválido")
    return user

def require_auth(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        g.current_user = _current_user()
        return view(*args, **kwargs)
    return wrapper

def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        g.current_user = _current_user()
        if g.current_user["tipo"] != "admin":
            raise ForbiddenError("Acesso restrito a administradores")
        return view(*args, **kwargs)
    return wrapper

def require_self_or_admin(param):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            g.current_user = _current_user()
            if g.current_user["id"] != kwargs[param] and g.current_user["tipo"] != "admin":
                raise ForbiddenError("Acesso negado")
            return view(*args, **kwargs)
        return wrapper
    return decorator
```
```python
@bp.post("/login")
def login():
    user = controller.login(request.get_json(silent=True))   # 401 on bad credentials
    return jsonify({"dados": user, "token": issue_token(user["id"]), "sucesso": True}), 200

@bp.get("/usuarios")
@require_admin
def listar_usuarios():
    return jsonify({"dados": controller.listar(), "sucesso": True}), 200
```
Use the project's own field names for the role (`tipo`, `role`) and keep the login response keys from the baseline, adding `token`.

**After** (Express, no new dependency): HMAC-signed tokens with `crypto`. `src/middlewares/auth.js`:
```js
const crypto = require('crypto');
const { UnauthorizedError, ForbiddenError } = require('../errors');

function sign(payload, secret) {
    const body = Buffer.from(JSON.stringify({ ...payload, exp: Date.now() + 86400000 })).toString('base64url');
    const mac = crypto.createHmac('sha256', secret).update(body).digest('base64url');
    return `${body}.${mac}`;
}

function verify(token, secret) {
    const [body, mac] = (token || '').split('.');
    if (!body || !mac) throw new UnauthorizedError('Token ausente');
    const expected = crypto.createHmac('sha256', secret).update(body).digest('base64url');
    if (mac.length !== expected.length || !crypto.timingSafeEqual(Buffer.from(mac), Buffer.from(expected))) {
        throw new UnauthorizedError('Token inválido');
    }
    const payload = JSON.parse(Buffer.from(body, 'base64url').toString());
    if (payload.exp < Date.now()) throw new UnauthorizedError('Token expirado');
    return payload;
}

const requireAuth = (secret) => (req, res, next) => {
    try {
        req.user = verify((req.get('Authorization') || '').replace(/^Bearer /, ''), secret);
        next();
    } catch (err) { next(err); }
};

const requireAdmin = (secret) => (req, res, next) =>
    requireAuth(secret)(req, res, (err) => {
        if (err) return next(err);
        return req.user.role === 'admin' ? next() : next(new ForbiddenError('Acesso restrito a administradores'));
    });

module.exports = { sign, requireAuth, requireAdmin };
```
A project with no login route and only admin routes to protect (e.g. a public checkout plus an admin report) can use a static admin token from config instead, compared with `crypto.timingSafeEqual`. When the token is unset the admin routes answer `401`/`403` to everyone.

**Seeds and validation**: keep a seeded admin whose credentials are documented in the README, so the baseline and validation steps can log in, send `Authorization: Bearer <token>` to protected routes, and confirm that the same routes answer `401` without it.

