# Project analysis

Heuristics for Phase 1. Each fact in the summary comes from a file you opened, never from a guess based on the project name.

## Scope of the source inventory

Count files the application executes. Exclude: `.claude/`, `.git/`, `node_modules/`, `venv/`, `.venv/`, `__pycache__/`, lockfiles, `*.db`, `api.http`, `README.md`. Include seed and migration scripts (they touch the schema) and empty `__init__.py` files only if they contain code.

```bash
find . -type f \( -name '*.py' -o -name '*.js' -o -name '*.ts' -o -name '*.rb' -o -name '*.go' -o -name '*.java' -o -name '*.php' \) \
  -not -path '*/node_modules/*' -not -path '*/.claude/*' -not -path '*/venv/*' -not -path '*/.venv/*' | xargs wc -l
```

## Language and framework

The manifest is the source of truth; imports confirm it.

| Manifest | Language | Framework signal |
|---|---|---|
| `requirements.txt`, `pyproject.toml`, `Pipfile` | Python | `flask` → Flask, `django` → Django, `fastapi` → FastAPI |
| `package.json` | JavaScript / TypeScript (`tsconfig.json` or `typescript` dep) | `express`, `fastify`, `@nestjs/core`, `koa` in `dependencies` |
| `go.mod` | Go | `gin-gonic/gin`, `labstack/echo`, `net/http` |
| `pom.xml`, `build.gradle` | Java/Kotlin | `spring-boot-starter-web` |
| `composer.json` | PHP | `laravel/framework`, `slim/slim` |
| `Gemfile` | Ruby | `rails`, `sinatra` |

Report the framework version as pinned in the manifest (`flask==3.1.1`, `"express": "^4.18.2"`). List the remaining runtime dependencies on the `Dependencies` line.

## Database

| Signal | Database / access style |
|---|---|
| `import sqlite3`, `require('sqlite3')`, `sqlite:///` | SQLite, raw driver or URI |
| `':memory:'` | SQLite in memory: data resets on every boot |
| `flask_sqlalchemy`, `sqlalchemy` | SQLAlchemy ORM |
| `pg`, `psycopg2`, `postgres://` | PostgreSQL |
| `mysql`, `pymysql`, `mysql2` | MySQL |
| `mongoose`, `pymongo` | MongoDB |

Tables come from `CREATE TABLE` statements, `__tablename__`, or model class names. List every one.

## Architecture classification

Pick the one that fits and justify it in one clause:

- **Monolithic**: routing, SQL, and business rules share files; no layer boundaries (one class registering routes and running queries is the strongest signal).
- **Partially layered**: folders such as `models/`, `routes/`, `services/` exist, but layers leak: routes run queries or hold business rules, services are unused, helpers duplicate model logic.
- **Layered (MVC or similar)**: each layer only calls the one below it.

A project that looks organised still gets audited at full depth; partial layering usually hides fat routes and duplicated logic.

## Domain

Infer from table names, route prefixes and seed data, then name it in a few words with its main entities: `E-commerce API (produtos, pedidos, usuários)`, `LMS API with checkout (courses, enrollments, payments)`, `Task Manager API (tasks, users, categories)`.

## Summary block

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <language + runtime version if pinned>
Framework:     <framework + version>
Dependencies:  <other runtime deps, comma-separated>
Domain:        <domain (main entities)>
Architecture:  <classification — one-clause justification>
Source files:  <N> files analyzed (~<total> lines)
DB tables:     <table1, table2, ...>
Endpoints:     <N> routes
Start command: <command that boots the app>
================================
```

Follow it with the endpoint inventory as a list: `METHOD path → file:line`.

## Runtime and baseline

Used by Phase 3 to boot the app and capture the baseline. Keep environments outside the repo's tracked files.

| Stack | Install | Boot |
|---|---|---|
| Python | `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` (`.venv/` is gitignored) | the command from the project README, typically `.venv/bin/python app.py` |
| Node | `npm install` | `npm start` |

- Run the server in the background, wait until the port answers (`curl -s -o /dev/null localhost:<port>/` in a short retry loop), then send requests.
- Port: read it from the code. If it is taken, stop your own earlier server first; check with `ss -ltnp | grep <port>`.
- Payloads: reuse `api.http`, README examples or seed data when present. Otherwise craft the smallest valid body from the handler's validation code. Hit each endpoint once with a valid request; for create endpoints also note the created id so later requests (GET by id, PUT, DELETE) target real rows.
- Order matters: run reads first, then creates, updates, and destructive calls (DELETE, reset) last.
- Persistent SQLite files (`loja.db`, `tasks.db`, `instance/`): delete them before each boot so baseline and validation start from the same seed. If the project has a seed script, run it after boot exactly as its README says.
- Record per endpoint: `METHOD path → status, top-level keys (and keys of the first item for lists)`.
