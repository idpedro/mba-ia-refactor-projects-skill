# Audit report template

Phase 2 prints this verbatim structure. Phase 3 step 1 saves the same text to `reports/`.

## Rules

- Findings sorted CRITICAL → HIGH → MEDIUM → LOW; inside a severity, by catalog ID.
- `File:` is `path:line`, `path:start-end`, or several comma-separated sites (`models.py:28, 92, 110`). Paths relative to the project root. Every line number was re-checked in step 3 of Phase 2.
- `Summary` counts equal the number of `###` findings per severity; `Total` equals their sum.
- `Description` names the concrete code (the variable, the query, the function), not the category in general.
- `Recommendation` names the playbook pattern (`P-xx`) and the target file in the new layout.
- Deprecated API findings name the modern replacement in `Recommendation`.
- `Verification` is required on every finding; see the next section.

## Verification

`Verification` turns the finding's Impact into checks that **fail on the current code and pass after Phase 3**. Phase 3 runs every one of them and is not done until all pass.

- Cover every harm the Impact names. If the Impact says users can "read, change, reassign and delete" others' data, there is one check for each verb.
- Name the identity for every HTTP check: anonymous, regular user, a *different* regular user, admin. Access findings always include the case "user A acting on user B's record".
- Prefer behaviour over code shape: a request and its expected status and body, a query on the stored value, a restart, a forced failure mid-write, a count of queries, the address the server listens on. A grep that must return no hits is enough only for findings about code shape (dead imports, naming, magic numbers, deprecated calls).
- Write each check so anyone can run it: `METHOD path` + identity + body → expected result; `SQL` → expected value; `grep -nE "<pattern>" <paths>` → no hits.

Examples by catalog entry (adapt names and routes to the project):

| Entry | Checks that prove the Impact is gone |
|---|---|
| AP-01 | grep for the literal secret and for literal defaults in config and seeds → no hits; a response that echoed it no longer contains it |
| AP-02 | the injection payload (`' OR '1'='1`, `%' --`) at each injected parameter → no extra rows, login `401`; values with quotes are stored and read back intact |
| AP-03, AP-07, AP-08 | the module/handler named in the finding no longer exists or no longer contains the rule or SQL quoted in Description; the rule is reachable from its new home (the endpoint still returns the baseline result) |
| AP-04 | anonymous → `401`, regular user → `403`; as admin, free-form SQL/code in the request → `400` and nothing executed |
| AP-05 | the stored value of a seeded and of a new password starts with the hash prefix (`scrypt:`, `pbkdf2:`, `salt:hash`); login with the right password works, with the wrong one `401` |
| AP-06 | every response the finding names lacks the field; the log line the finding names no longer shows the value |
| AP-09 | the AP-09 grep → no hits of the kind reported; when persisted: write, restart the server, read it back |
| AP-10 | force a failure between the steps (invalid second item, rejected payment) → no partial rows; delete the parent → no orphan children |
| AP-11 | anonymous → `401`; regular user on admin routes → `403`; user A reading, changing, reassigning or deleting user B's record, or creating one owned by B → `403`; the owner on their own record → baseline status |
| AP-12 | the server listens on `127.0.0.1` (`ss -ltnp`); debug off in the boot log; a cross-origin preflight from an unlisted origin gets no `Access-Control-Allow-Origin` |
| AP-13 | count the SQL statements one request runs (driver trace or ORM echo) → constant, not one per row |
| AP-14, AP-15 | the invalid inputs the finding names → `400` with a message on every endpoint that accepts them (create and update alike) |
| AP-16 | an unexpected error → `500` with a generic message and the detail only in the log |
| AP-17 | grep for the deprecated call → no hits; the app runs with deprecation warnings turned into errors where the stack supports it |
| AP-19 – AP-23 | grep for the literal, name or import → no hits |

## Template

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: <project-dir>
Stack:   <Language> + <Framework> (<database>)
Files:   <N> analyzed | ~<total> lines of code

## Summary
CRITICAL: <n> | HIGH: <n> | MEDIUM: <n> | LOW: <n>

## Findings

### [CRITICAL] <Anti-pattern name> (AP-xx)
File: <path:lines>
Description: <what the code does, citing the concrete identifiers>
Impact: <what breaks or who can exploit it>
Recommendation: <P-xx — the change, and where the code lands>
Verification: <checks that fail now and must pass after Phase 3; see "Verification">

### [HIGH] ...

================================
Total: <n> findings
================================

## Decisions requiring approval
1. <behaviour change> — <why> — default: <what Phase 3 does if you answer y>
2. ...

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

## Decisions

List each refactor whose effect a client can observe, with the default you will apply on `y`. Typical entries:

- A field removed from responses (password hash, secret key, db path).
- An endpoint that executes SQL or code from the request, or wipes data: keep the route and require the admin role (P-16); anonymous requests get `401`, authenticated non-admins `403`. Free-form SQL or code from the request is never executed, not even for admins: the route runs only queries from a fixed allow-list (P-05).
- Authentication (P-16): the public routes (login, sign-up, health/index, public catalog reads), how clients get a token, and which routes need the admin role or ownership. Enforcement is on by default; this decision shapes it and never turns it off.
- Password hash format changing (existing stored passwords stop matching unless re-seeded or verified with a legacy fallback).
- Seeded accounts: their passwords come from environment variables named in `.env.example` (or are generated and printed once by the seed step), never from literals in code or docs.
- Error handling centralised: keep the body format and messages clients already receive; only leaks and inconsistencies change.
- Request or response field renames (default: keep the original names).

An empty list is printed as `1. None — the refactor preserves every observable response.`
