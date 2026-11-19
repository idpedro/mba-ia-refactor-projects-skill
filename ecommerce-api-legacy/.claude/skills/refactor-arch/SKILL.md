---
name: refactor-arch
description: Analyse, audit and refactor a backend project to the MVC pattern in three phases (analysis, audit report with confirmation gate, refactor with validation). Stack-agnostic.
disable-model-invocation: true
---

# refactor-arch

Three sequential phases over the project in the current working directory. Phases 1 and 2 are **read-only**: the first file you write is in Phase 3, after the human answers `y`.

Every claim you print carries evidence: a finding cites `file:line` you read yourself, a validation line cites a request you actually sent. A finding counts as fixed only when the harm its **Impact** describes can no longer happen; code that merely moved, a guard that is off, or a grep that no longer matches is not a fix. Write report prose (Description, Impact, Recommendation) in the language of the project's README; keep the block headers in English as shown in the templates.

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
4. Write each finding's **`Verification:`** line, following the rules in `report-template.md`: concrete checks derived from its Impact, which fail on the current code and must pass after Phase 3.
5. Print the report exactly in the template's format, findings sorted CRITICAL → HIGH → MEDIUM → LOW.
6. Print the **decisions** section from the template: every refactor that will change observable behaviour (a removed field, a protected endpoint, a new hash format), so the human approves it explicitly. A decision chooses *how* a finding is fixed and what clients will observe, never *whether* it is fixed: every finding, whatever its severity, gets a fix that is active under the default configuration. "Deferred", "out of scope", "not implemented" and "off unless a flag is set" are not available as defaults. The original start command keeps booting with **no environment variable set**: a missing signing key is generated at boot, a missing seeded password is generated and printed once, and any other missing secret disables only the feature that needs it (fail closed). No decision makes an environment variable mandatory for the app to start. Every route in the endpoint inventory keeps answering: a dangerous route is fixed by protecting or restricting it (admin role, an allow-list instead of free-form input, validated input), and stays in the app.
7. Ask `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]` and end your turn.

Done when every catalog entry has been checked against every file, every finding has a `Verification:` line, and the question is the last thing you printed. On `n`, stop. On any other answer, treat it as edits to the decisions and ask again; an edit that would leave a finding unfixed gets an alternative fix proposed in its place. A finding stays open only if the human explicitly drops it after seeing the alternative; Phase 3 then lists it as "dropped by the human".

## Phase 3 — Refactoring

1. **Save the report.** Write the Phase 2 report verbatim, as plain Markdown with no surrounding code fence, to `reports/<name>.md` at the git repository root (create `reports/` if missing). `<name>` is `audit-project-1` for `code-smells-project`, `audit-project-2` for `ecommerce-api-legacy`, `audit-project-3` for `task-manager-api`, and `audit-<project-dir>` for any other project.
2. **Baseline.** Before touching code, boot the original app and send one request per endpoint in the inventory, following the "Runtime and baseline" section of `project-analysis.md`. Record status code and response keys in a scratch file outside the project (`/tmp/refactor-arch-<project-dir>/baseline.md`). This baseline is the contract Phase 3 preserves.
3. **Plan.** Read [`references/mvc-guidelines.md`](references/mvc-guidelines.md) and [`references/refactoring-playbook.md`](references/refactoring-playbook.md). Pick the target layout for this stack, then map every finding to the playbook pattern that resolves it. A finding with no pattern gets a one-line fix plan of its own. When the stack has no layout or example in the references, apply the same move with the framework's own idioms (its app/settings structure, its auth mechanism, its run command).
4. **Refactor** in small moves: config first, then models, controllers, views/routes, error handling, composition root. Boot the app after each move and fix breakage before the next one.
5. **Validate** against the baseline, on a fresh database:
   - the app boots with the project's original start command and **no environment variables set**, no errors in the log; for the remaining checks you may set the variables from `.env.example` (seeded passwords, admin token) to log in;
   - every endpoint returns the baseline status code and response keys (sending credentials where the route now requires them), or differs only as an approved decision;
   - every check in every finding's `Verification:` line passes. Run them for real (requests with each identity the check names, queries on the stored data, restarts, greps) and record the command and its result for each.
6. **Clean up**: stop every server you started; delete runtime artefacts the validation created (database files, `__pycache__`), leaving only files that belong in the repo.
7. Print the `PHASE 3: REFACTORING COMPLETE` block from `mvc-guidelines.md`.

Done when all three validation bullets pass. A failing check sends you back to step 4. The skill ends with every finding's Verification passing; a check you could not make pass is printed as `✗` with the reason, the refactor is reported as incomplete, and it is never shown as `✓`.
