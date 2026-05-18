---
description: Autopilot for test work. Add or improve coverage without touching production code. Pauses before any non-test file edit.
argument-hint: "<test task: cover module X, get file Y to N% coverage, etc.>"
---

Enter autopilot mode for test work. Load the `autopilot` skill, then apply these test-specific rules:

**Task type:** tests only

**Brief:** $ARGUMENTS

## Test-specific checkpoints (yellow)

Pause via AskUserQuestion when:

- About to edit any non-test file. Touching production code is out of scope for this command by default — confirm with the human.
- A new test fails against current code. This is likely a real bug, not a test bug. Surface it; do not silently "fix" the production code to make the test pass.
- About to introduce a new test framework, runner, or major test utility.

## Test-specific red additions

Do not (without asking):

- Edit any file outside the test directories (`test/`, `tests/`, `__tests__/`, `*.test.*`, `*.spec.*`).
- Regenerate snapshots without diff review.
- Delete existing tests.
- Modify CI configuration.

## Test-specific handback emphasis

- **Coverage delta:** before → after, by file or module.
- **Cases now covered:** specific scenarios the new tests exercise.
- **Latent bugs discovered:** any production-code bugs you found while writing tests but explicitly did NOT fix (separate PR).
- **Flaky tests:** any test that failed intermittently during the run, even if it passed on retry.

Proceed.
