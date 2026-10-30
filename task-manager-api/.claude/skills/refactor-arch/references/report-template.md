# Audit report template

Phase 2 prints this verbatim structure. Phase 3 step 1 saves the same text to `reports/`.

## Rules

- Findings sorted CRITICAL → HIGH → MEDIUM → LOW; inside a severity, by catalog ID.
- `File:` is `path:line`, `path:start-end`, or several comma-separated sites (`models.py:28, 92, 110`). Paths relative to the project root. Every line number was re-checked in step 3 of Phase 2.
- `Summary` counts equal the number of `###` findings per severity; `Total` equals their sum.
- `Description` names the concrete code (the variable, the query, the function), not the category in general.
- `Recommendation` names the playbook pattern (`P-xx`) and the target file in the new layout.
- Deprecated API findings name the modern replacement in `Recommendation`.

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
- An endpoint that executes arbitrary SQL or wipes data: default is to keep the route and gate it behind an `ADMIN_ENABLED`-style config flag that defaults off, returning `403`.
- Password hash format changing (existing stored passwords stop matching unless re-seeded or verified with a legacy fallback).
- Error bodies normalised to one JSON shape.
- Request or response field renames (default: keep the original names).

An empty list is printed as `1. None — the refactor preserves every observable response.`
