# MVC target architecture

The layout Phase 3 produces. In an HTTP API there is no HTML: the **View** is the routing and presentation layer (route table + response serialization).

## Layers

| Layer | Owns | Never contains |
|---|---|---|
| **Config** | Every environment-dependent value, read from env vars with safe dev defaults | Logic |
| **Model** | Data shape, persistence (queries / ORM), invariants of a single entity (`is_overdue`, `set_password`), serialization to a public dict | HTTP objects (`request`, `req`, `res`), response codes |
| **Controller** | Use-case flow: validate input, call models (and services), decide the outcome, raise domain errors | SQL, route registration, `jsonify`/`res.json` formatting details |
| **Service** (optional) | Cross-entity business rules or external side effects (payment, email, reports) a controller calls | HTTP objects |
| **View / Routes** | URL → controller mapping, request parsing, status codes, response shape | SQL, business rules |
| **Middleware** | Centralized error handling, request logging, auth guards | Business rules |
| **Composition root** | Builds config, DB, services, controllers; wires routes; starts the server | Anything else |

**Dependency direction**: Routes → Controllers → (Services) → Models → DB. Nothing points upward. Controllers receive their collaborators (DB session, services) from the composition root rather than importing global singletons.

Use services when a rule spans entities or talks to the outside world; a single-entity CRUD controller calling the model directly is fine.

## Target layouts

Name modules after the project's domain (`produto_model.py`, `course.model.js`) and keep the project's naming language.

### Python / Flask

```
<project>/
├── app.py                      # entry point kept so `python app.py` still works: from src.app import create_app
└── src/
    ├── __init__.py
    ├── app.py                  # create_app(): composition root
    ├── config/settings.py
    ├── database.py             # connection / db object, init_db(app), seed
    ├── models/<entity>_model.py
    ├── controllers/<entity>_controller.py
    ├── services/<name>_service.py
    ├── views/<entity>_routes.py  # Blueprints
    └── middlewares/error_handler.py
```

### Node / Express

```
<project>/
├── package.json                # "start" script points to the new entry
└── src/
    ├── app.js                  # composition root: builds db, controllers, routers, listens
    ├── config/index.js
    ├── database/{connection.js,schema.js,seed.js}
    ├── models/<entity>.model.js
    ├── controllers/<entity>.controller.js
    ├── services/<name>.service.js
    ├── routes/<entity>.routes.js   # express.Router()
    └── middlewares/errorHandler.js
```

### Already partially layered projects

Keep what is sound; move what leaks. Typical moves:

- `routes/` that run queries and hold rules → thin views plus new `controllers/` (and `services/` for reports and notifications).
- `utils/helpers.py` holding validation → `validators/` or controller-level schemas; delete the helpers nobody calls.
- Model serializers already present (`to_dict`) become the single serializer; delete the hand-built copies in routes.
- Config literals in `app.py` → `config/settings.py`, loaded by an app factory.

Keep the original module paths importable when other scripts depend on them (e.g. `seed.py` importing `from app import app, db`): either update those scripts in the same move or leave a thin re-export.

## Rules

- **Contract preserved**: same paths, methods, status codes, request fields and response keys as the baseline, except approved decisions.
- **Entry point clear**: the original start command boots the refactored app.
- **Config externalized**: secrets come only from the environment; provide `.env.example` listing every variable. Non-secret defaults (port, db path) may have in-code defaults inside the config module only.
- **Error handling centralized**: one handler maps domain errors (`NotFoundError` → 404, `ValidationError` → 400, unknown → 500 with a generic message, details logged).
- **No new runtime dependencies** unless a finding cannot be fixed without one; prefer what the stack already ships (`werkzeug.security`, Node `crypto`, `logging`).

## Completion block

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
<tree of the new layout, source files only>

## Findings resolved
<n>/<total> — unresolved: <AP-xx: reason, or "none">

## Validation
  ✓ Application boots without errors (<start command>)
  ✓ All endpoints respond correctly (<n>/<n> match baseline; deviations: <approved decisions or "none">)
  ✓ Zero CRITICAL/HIGH anti-patterns remaining (signals re-run)
================================
```

A line that did not pass is printed with `✗` and the reason.
