# Anti-pattern catalog

Phase 2 applies every entry below to every inventoried file. Each entry: severity, detection signals (concrete, grep-able where possible), and the playbook pattern that fixes it (`P-xx` in `refactoring-playbook.md`).

The grep hints are starting points; confirm every hit by reading the surrounding code, and look for the same shape in idioms the hint misses.

## Severity scale

- **CRITICAL**: security hole or total collapse of separation of concerns: exposes data, allows injection, or makes the code untestable as a whole.
- **HIGH**: strong MVC/SOLID violation that makes maintenance and testing hard: business rules in controllers/routes, hard-wired dependencies, mutable global state, writes that can leave data inconsistent.
- **MEDIUM**: standardisation, duplication, moderate performance: N+1 queries, missing validation, scattered error handling, deprecated APIs.
- **LOW**: readability: naming, magic numbers, dead imports, print-debugging.

When one site matches two entries, report it under the more severe one and mention the other in its Description.

---

## CRITICAL

### AP-01 Hardcoded credentials and secrets
- **Signals**: string literals assigned to names like `SECRET_KEY`, `password`, `pass`, `pwd`, `api_key`, `token`, `gatewayKey`, `smtp`, `dbPass`; literals starting `pk_live_`, `sk_`, `AKIA`; connection strings with `user:pass@`; config objects of literals in source.
- `grep -nEi "(secret|passw|pwd|api_?key|token|_key)\s*[:=]\s*['\"]" -r .`
- **Also**: a secret echoed back in a response (`"secret_key": ...` in a health check) is the same finding, raised.
- **Fix**: P-01.

### AP-02 SQL injection
- **Signals**: a query string built by concatenation or interpolation with any value that can come from a request: `"... WHERE id = " + str(id)`, `f"SELECT ... {x}"`, `` `SELECT ... ${x}` ``, `"... LIKE '%" + termo + "%'"`, `.format(` on SQL. Includes values cast with `str()`: casting does not sanitise.
- `grep -nE "(execute|query|run|get|all)\(\s*[\"'f\`].*(\+|\{|\$\{)" -r .` and `grep -nE "(SELECT|INSERT|UPDATE|DELETE).*\" *\+" -r .`
- **Fix**: P-02.

### AP-03 God class / God module
- **Signals**: one class or file that does three or more of: register routes, open the DB connection, create schema, run queries, apply business rules, format responses, call external services. A file over ~300 lines spanning several domains (products + users + orders). A class named `*Manager`, `*Handler`, `App*` with a `setupRoutes`-style method and SQL in its body.
- **Fix**: P-03.

### AP-04 Unprotected destructive or arbitrary-execution endpoint
- **Signals**: a route that executes SQL/code taken from the request body (`cursor.execute(dados["sql"])`, `eval`, `exec`); a route that wipes tables (`/admin/reset-db`, `DELETE FROM` with no `WHERE`) reachable with no authentication check.
- **Fix**: P-05 (removal or guard is a Phase 2 **decision**).

### AP-05 Plaintext or weak password storage
- **Signals**: password columns written straight from the request; `md5`, `sha1` without salt, `base64`, home-made loops (`badCrypto`) used as hashing; login implemented as `WHERE email = ? AND senha = ?` against the raw value; seed data with literal passwords stored as is.
- `grep -nEi "md5|sha1|base64|badCrypto|senha\s*=|password\s*=" -r .`
- **Fix**: P-04.

### AP-06 Sensitive data exposure
- **Signals**: serializers (`to_dict`, row → dict mappers, `res.json(user)`) that include `password`/`senha`/`pass`/hash fields; login or create responses returning the full user row; logs printing card numbers, passwords, tokens, or keys (`console.log(\`... ${cc} ... ${key}\`)`); raw exception text returned to clients (`str(e)`) on auth paths.
- **Fix**: P-05.

---

## HIGH

### AP-07 Business logic in the controller / route (fat controller)
- **Signals**: a route handler that, beyond parsing the request and shaping the response, computes prices, discounts, totals, status transitions, stock changes, payment decisions (`cc.startsWith("4") ? "PAID" : "DENIED"`), overdue rules, or report aggregation. Notification side effects (`print("ENVIANDO EMAIL ...")`) inline in the handler. Handlers longer than ~40 lines.
- **Fix**: P-06.

### AP-08 Tight coupling / no dependency injection
- **Signals**: handlers or models calling a module-level singleton (`get_db()` from anywhere, `db = new sqlite3.Database(...)` in a constructor, `new Service()` inside a handler); no app factory (`create_app`) or composition root; layers importing concrete infrastructure from each other in both directions; a service class that is defined but never wired in.
- **Fix**: P-07.

### AP-09 Mutable global state
- **Signals**: module-level variables mutated at runtime: `global x`, `let cache = {}` / `let total = 0` exported and written, a shared connection with `check_same_thread=False`, in-memory lists on a service instance (`self.notifications = []`) acting as storage.
- `grep -nE "^\s*global |^let |^var " -r .`
- **Fix**: P-08.

### AP-10 Non-atomic multi-step writes and orphaned data
- **Signals**: several dependent `INSERT`/`UPDATE`/`DELETE` statements with no transaction (an order inserted, then items, then stock in separate commits; enrollment then payment in nested callbacks); a validation loop that returns mid-way after some writes; deleting a parent row while children stay (`DELETE FROM users` leaving enrollments/payments, or a response that admits "ficaram sujos"); stock decremented without re-checking it inside the same transaction.
- **Fix**: P-11.

### AP-11 Missing authentication / authorization
- **Signals**: admin or destructive routes with no auth check; routes that list or change users, orders or other per-user data reachable anonymously (`GET /usuarios`, `PUT /pedidos/<id>/status`); fake tokens (`'fake-jwt-token-' + id`); role taken from the request body on user creation (`role = data.get('role')` letting anyone self-register as admin); any client able to change another user's data; an auth guard that exists but is disabled by default (`AUTH_REQUIRED=0`).
- **Fix**: P-16, enforced by default. The Phase 2 decision covers which routes stay public and how clients authenticate; enforcement itself is never optional.

### AP-12 Debug mode and unsafe defaults in the entry point
- **Signals**: `debug=True` / `DEBUG = True` combined with `host="0.0.0.0"` (the Werkzeug debugger allows remote code execution); `CORS(app)` with no origin list; config values that should differ per environment written as literals.
- **Fix**: P-01. The fixed defaults are all three of: debug off, bind to `127.0.0.1` (exposing the server on every interface is an explicit `HOST=0.0.0.0` opt-in), and an explicit CORS origin list. The finding stays open while any of them still defaults to the unsafe value.

---

## MEDIUM

### AP-13 N+1 queries
- **Signals**: a query inside a loop over the results of another query: `for row in rows: cursor.execute(...)`, `for t in tasks: User.query.get(t.user_id)`, `forEach(c => db.all(...))`, `len(u.tasks)` on a lazy relationship per user, `.count()` per category inside a loop; also several `COUNT(*)` queries that one `GROUP BY` would answer.
- **Fix**: P-09.

### AP-14 Duplicated logic
- **Signals**: the same validation block, serializer, or rule copied into two or more places: identical `if "nome" not in dados` sequences in create and update; a manual dict built field by field when the model already has `to_dict()`; the overdue rule written out in four routes; status/role lists repeated as literals; a helper (`process_task_data`, `VALID_STATUSES`) that exists but is ignored.
- **Fix**: P-12.

### AP-15 Missing or inconsistent input validation
- **Signals**: request fields used without type or presence checks (`dados.get("status")` on a `None` body, `int(request.args["x"])` that raises 500 on bad input, `priority < 1` on a string); update endpoints that skip the checks create endpoints do; a validated email regex in one route and none in another.
- **Fix**: P-12.

### AP-16 Scattered or leaky error handling
- **Signals**: `try/except Exception` wrapping every handler; bare `except:`; `return jsonify({"erro": str(e)}), 500` exposing internals; callbacks that ignore `err`; errors answered with `res.send("Erro DB")` as plain text in a JSON API; no central error handler or middleware.
- **Fix**: P-10.

### AP-17 Deprecated APIs
Flag every use and recommend the modern equivalent. Check the installed framework version before calling something deprecated; versions in the manifest decide.

| Deprecated | Modern equivalent | Notes |
|---|---|---|
| `datetime.utcnow()`, `datetime.utcfromtimestamp()` | `datetime.now(timezone.utc)` | Deprecated in Python 3.12. Also as SQLAlchemy `default=datetime.utcnow` |
| `Model.query.get(id)` (SQLAlchemy `Query.get`) | `db.session.get(Model, id)` | Legacy since SQLAlchemy 2.0; Flask-SQLAlchemy 3.x warns |
| `Model.query.get_or_404(id)` | `db.get_or_404(Model, id)` | Flask-SQLAlchemy 3.x |
| `@app.before_first_request` | run setup in `create_app()` | Removed in Flask 2.3 |
| `flask.json.JSONEncoder`, `app.json_encoder` | `app.json = CustomJSONProvider(app)` | Removed in Flask 2.3 |
| `from flask import escape, Markup` | `from markupsafe import escape, Markup` | Removed in Flask 3.0 |
| `new Buffer(x)` | `Buffer.from(x)` / `Buffer.alloc(n)` | Node, deprecated DEP0005 |
| `require('body-parser').json()` | `express.json()` | Built in since Express 4.16 |
| `req.param('x')` | `req.params.x` / `req.query.x` / `req.body.x` | Removed in Express 5 |
| `res.send(status)`, `res.json(status, body)` | `res.status(code).send(...)` / `.json(...)` | Removed in Express 5 |
| `app.del(...)` | `app.delete(...)` | Removed in Express 5 |
| callback-style DB APIs nested 3+ levels | `async/await` over a promisified driver | Not removed, but superseded; report with AP-10 or AP-16 when it hides bugs |
| `var` | `const` / `let` | Legacy JS |

- `grep -nE "utcnow|\.query\.get\(|before_first_request|new Buffer|body-parser|req\.param\(|app\.del\(" -r .`

### AP-18 Configuration in code instead of a config module
- **Signals**: DB path, port, URLs, SMTP host, feature flags as literals spread across modules (`db_path = "loja.db"`, `port: 3000` inside a utils file, `'sqlite:///tasks.db'` in `app.py`). Distinct from AP-01: these are not secrets, but they block per-environment configuration.
- **Fix**: P-01.

---

## LOW

### AP-19 Magic numbers and strings
- **Signals**: unexplained literals in business rules: discount tiers `10000 / 0.1`, priority bounds `1..5`, length limits `200`, `4`, status strings compared inline (`'done'`, `'PAID'`), `'#000000'`, loop counts (`10000`).
- **Fix**: P-14.

### AP-20 Poor naming
- **Signals**: one- or two-letter names for domain values (`u`, `e`, `p`, `cc`, `cid`, `t`, `c`, `d`), cryptic request fields (`usr`, `eml`, `pwd`, `c_id`), misleading names (`badCrypto`, `logAndCache` doing two things), `cursor2`/`cursor3`, mixed languages within one module.
- **Fix**: P-14 (rename internals freely; renaming request/response fields is a contract change and needs a **decision**).

### AP-21 Unused imports and dead code
- **Signals**: imported names never referenced (`import os, sys, json, time` with none used; `totalRevenue` exported and never read); functions or services never called; commented-out blocks.
- Python: `grep -n "^import\|^from" file` then grep each name. Node: same with `require`.
- **Fix**: delete.

### AP-22 Print-debugging instead of logging
- **Signals**: `print(...)` / `console.log(...)` as the only logging, banners (`print("=" * 50)`), notification side effects simulated with `print`.
- **Fix**: P-15.

### AP-23 Verbose control flow
- **Signals**: `if cond: return True else: return False`; nested `if` pyramids three levels deep for one boolean (`is_overdue`); `type(x) == list` instead of `isinstance`; `x = x + 1` in counting loops that `sum()`/`count` replaces.
- **Fix**: P-14.
