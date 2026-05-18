---
description: Autopilot for refactors. Restructure without changing behavior. Pauses before touching public APIs or changing tests alongside production code.
argument-hint: <refactor description + explicit no-behavior-change assertion>
---

Enter autopilot mode for a refactor. Load the `autopilot` skill, then apply these refactor-specific rules:

**Task type:** refactor (no behavior change)

**Brief:** $ARGUMENTS

## Refactor-specific checkpoints (yellow)

Pause via AskUserQuestion when:

- The change would alter a public API, exported signature, serialized format, or external contract.
- The existing test suite doesn't cover the code being refactored. Offer to add characterization tests first.
- About to delete code that has no callers but is exported. Confirm with the human (might be public API used outside the repo).

## Refactor-specific red additions

Do not (without asking):

- Modify tests in the same diff as the refactor. A test change alongside a refactor is a behavior-change smell.
- `git mv` chains that lose file history. Use plain rename + edit so blame is preserved.
- Change snapshot fixtures (snapshots encode behavior; if they need changing, the refactor changed behavior).

## Refactor-specific handback emphasis

- **Before/after:** structural diff (counts, file moves, signature shifts).
- **Test results:** same suite must be green pre- and post-refactor. Report both.
- **No-behavior-change assertion:** explicit statement, named tests that prove it.
- **API surface touched:** every exported symbol whose shape changed (should be none for a pure refactor).
- **Reversion plan:** in one line, how to revert if reviewers want.

Proceed.
