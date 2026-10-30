---
name: refactor-arch
description: Analyse, audit and refactor a backend project to the MVC pattern in three phases (analysis, audit report with confirmation gate, refactor with validation). Stack-agnostic.
disable-model-invocation: true
---

# refactor-arch

Three sequential phases over the project in the current working directory. Phases 1 and 2 are **read-only**: the first file you write is in Phase 3, after the human answers `y`.

Every claim you print carries evidence: a finding cites `file:line` you read yourself, a validation line cites a request you actually sent. Write report prose (Description, Impact, Recommendation) in the language of the project's README; keep the block headers in English as shown in the templates.

## Phase 1 — Analysis

1. Read [`references/project-analysis.md`](references/project-analysis.md) and follow its heuristics.
2. Build the **source inventory**: every source file the app runs, with its line count. Read each one in full.
3. Build the **endpoint inventory**: every route as `METHOD path → handler file:line`, including routes registered outside the main router (inline `@app.route`, `app.add_url_rule`, `app.get(...)` inside classes).
4. Print the `PHASE 1: PROJECT ANALYSIS` block from `project-analysis.md`.

Done when every inventoried file has been read end to end and the endpoint count matches a grep of the route-registration calls.

## Phase 2 — Audit

1. Read [`references/anti-patterns.md`](references/anti-patterns.md) and [`references/report-template.md`](references/report-template.md).
2. Sweep: apply **every** catalog entry to **every** inventoried file. One finding per distinct occurrence site; occurrences of the same anti-pattern in one file group into one finding listing all lines.
3. Verify each `file:line` with `grep -n` or by re-reading the line before it enters the report.
4. Print the report exactly in the template's format, findings sorted CRITICAL → HIGH → MEDIUM → LOW.
5. Print the **decisions** section from the template: every refactor that will change observable behaviour (a removed field, a disabled endpoint, a new hash format), so the human approves it explicitly.
6. Ask `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]` and end your turn.

Done when every catalog entry has been checked against every file, and the question is the last thing you printed. On `n`, stop. On any other answer, treat it as edits to the decisions and ask again.

## Phase 3 — Refactoring

1. **Save the report.** Write the Phase 2 report verbatim to `reports/audit-<project-dir>.md` at the git repository root (create `reports/` if missing).
2. **Baseline.** Before touching code, boot the original app and send one request per endpoint in the inventory, following the "Runtime and baseline" section of `project-analysis.md`. Record status code and response keys in a scratch file outside the project (`/tmp/refactor-arch-<project-dir>/baseline.md`). This baseline is the contract Phase 3 preserves.
3. **Plan.** Read [`references/mvc-guidelines.md`](references/mvc-guidelines.md) and [`references/refactoring-playbook.md`](references/refactoring-playbook.md). Pick the target layout for this stack, then map every finding to the playbook pattern that resolves it. A finding with no pattern gets a one-line fix plan of its own.
4. **Refactor** in small moves: config first, then models, controllers, views/routes, error handling, composition root. Boot the app after each move and fix breakage before the next one.
5. **Validate** against the baseline, on a fresh database:
   - the app boots with the project's original start command, no errors in the log;
   - every endpoint returns the baseline status code and response keys, or differs only as an approved decision;
   - re-run the detection signals of every CRITICAL and HIGH finding: each comes back empty.
6. **Clean up**: stop every server you started; delete runtime artefacts the validation created (database files, `__pycache__`), leaving only files that belong in the repo.
7. Print the `PHASE 3: REFACTORING COMPLETE` block from `mvc-guidelines.md`.

Done when all three validation bullets pass. A failing bullet sends you back to step 4; report any you could not make pass as `✗` with the reason, never as `✓`.
