---
description: Autopilot for mechanical maintenance. Formatting, renames, config sync, doc updates. Pauses if mechanical work reveals real bugs.
argument-hint: "<chore task: run prettier on X, rename Y, sync configs, etc.>"
---

Enter autopilot mode for chore work. Load the `autopilot` skill, then apply these chore-specific rules:

**Task type:** mechanical maintenance (zero behavior change)

**Brief:** $ARGUMENTS

## Chore-specific checkpoints (yellow)

Pause via AskUserQuestion when:

- The mechanical change reveals a real bug or type error. Don't "fix" it as part of the chore — surface it.
- A rename crosses a package boundary or affects an exported symbol.
- Budget tick: every ~5 tool calls (more aggressive than default; chores sprawl).

## Chore-specific red additions

Do not (without asking):

- Edit logic in `.ts`/`.py`/`.js`/`.go`/`.rs` function bodies when the brief is doc/format-only. Whitespace and reordering within unchanged logic is fine; semantic edits are not.
- Bump CHANGELOG or version numbers.
- Touch CI/CD configuration.
- Edit anything in `node_modules/`, `dist/`, `build/`, `target/`, or other generated/vendored directories.

## Chore-specific handback emphasis

- **File count + category breakdown:** "47 files: 31 formatting, 12 renames, 4 config sync."
- **Zero behavior change confirmation:** explicit statement + the test command run.
- **Auto-fixer disagreements:** anywhere prettier/eslint/ruff/etc. wanted a change you didn't apply, and why.
- **Skipped exceptions:** files where the brief would apply but you chose not to (generated, vendored, license headers, etc.).

Proceed.
