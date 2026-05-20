---
description: Enter autopilot v2 mode. Proceed without asking on safe ops; pause at registry-driven yellow triggers; hard-stop on destructive ops. Single command — task type is inferred from the brief.
argument-hint: <task description>
---

Enter autopilot v2 mode and execute the following task:

$ARGUMENTS

Load and follow the `autopilot` skill (generated from `triggers/*.json`). Use `checkpoint-format` for any pauses. Produce a `handback` report when done or blocked.

## Before starting

1. **Restate** the task in one line so the human can catch a misread.
2. **Classify** the task by its first noun/verb. Apply the matching addendum below (one). If the brief doesn't match any cleanly, default to feature behavior.
3. **Surface blockers first.** If there are foreseeable ambiguities a checkpoint would resolve, ask now via AskUserQuestion *before* any work.
4. Otherwise, proceed.

## Task-type addenda (single-file conditional, replaces v1's 6 commands)

The task type is *not* declared by the command name in v2; it's inferred from the brief. Apply the addendum whose conditions match. ADR-0010 is superseded by this collapse — see docs/design/autopilot-v2.md "What we drop".

### Bugfix (brief contains: bug, fix, broken, regression, error, crash)
- **Before any non-test edit**, confirm you can reproduce the bug. If not, surface an AskUserQuestion before changing production code.
- Do not edit tests in the same diff as the production fix unless explicitly authorized. Tests guard the fix; modifying them simultaneously hides regressions.

### Refactor (brief contains: refactor, restructure, clean up, reorganize, rename)
- Pause via AskUserQuestion before changing any public API surface — exported function signatures, public class methods, schema migrations.
- Do not edit tests in the same diff. Refactor is behavior-preserving by definition; the existing tests are the contract.

### Feature (brief contains: add, build, implement, create, new) — default
- After producing your initial plan and before writing code, pause via AskUserQuestion if any architectural fork is foreseeable (new top-level dep, new route, new env var, new schema column).
- Enumerate every load-bearing assumption made without asking, in the `Assumed:` section of handback.

### Deps (brief contains: upgrade, bump, update dep, install)
- Pause via AskUserQuestion before any major-version bump or new top-level dependency.
- Surface unexpected lockfile churn (>20 lines outside the named dep) before committing.

### Tests (brief contains: test, coverage, spec)
- Block production edits unless explicitly authorized in the brief. Adding a test must not silently fix the bug it documents.

### Chore (brief contains: format, lint, rename file, move, cleanup)
- Block semantic edits when the brief is format-only. A rename PR with logic changes is two PRs.
- More aggressive budget ticks: surface at budget yellow even if the operation looks small.
