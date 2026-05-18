---
description: Autopilot for bug fixes. Reproduce → isolate → fix → add regression test. Pauses before touching non-test code if the bug hasn't been reproduced.
argument-hint: <bug description, ideally with repro steps or error link>
---

Enter autopilot mode for a bug fix. Load the `autopilot` skill, then apply these bugfix-specific rules on top:

**Task type:** bug fix

**Brief:** $ARGUMENTS

## Bugfix-specific checkpoints (yellow)

Pause via AskUserQuestion when:

- **Scope expansion (MUST ask).** If the brief names a specific file (e.g. `login.test.ts`, `src/auth/foo.ts`) but the fix requires editing a different file not named in the brief, you **must** invoke AskUserQuestion before the first edit. Confirm: "extend scope to include `<file>`?" Concrete pattern: brief says "fix the test in `login.test.ts`" → fix actually needs `login.ts` changes → ASK before touching `login.ts`. This is the most common silent-scope-drift failure mode.
- About to modify non-test production code and you have NOT reproduced the bug (failing test, logged error, or repro steps). Confirm: reproduce first, or proceed without?
- Root cause appears to span more than one module. Confirm scope.
- The "fix" treats a symptom and the underlying cause is unclear. Surface the ambiguity.

## Bugfix-specific red additions

Beyond the standard red tier, do not (without asking):

- Modify or delete an existing test in the same diff as the production fix.
- Disable, skip, or mark tests as expected-fail (`.skip`, `xit`, `@pytest.mark.skip`, `// @ts-expect-error` etc.).
- Edit files unrelated to the bug (scope drift).

## Bugfix-specific handback emphasis

The handback report should foreground:

- **Root cause:** one-line statement of why the bug occurred.
- **Repro:** steps or test that demonstrates the bug.
- **Regression test:** what new test guards against recurrence.
- **Blast radius:** what else in the codebase might share this bug (don't fix, but note).
- **Suspicious adjacent code:** anything you noticed but didn't touch.

Proceed.
