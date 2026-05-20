---
name: autopilot
description: High-autonomy operating mode. Proceed by default; pause via AskUserQuestion at categorical yellow-tier triggers; respect hook blocks on destructive ops.
---

# autopilot (v2)

**GENERATED FROM `triggers/*.json` — do not hand-edit.** Regenerate via `node tools/gen-skill.mjs`. See [ADR-0018](../../../../docs/adr/0018-rebuild-from-lessons-learned.md) for why.

## Operating model

- **Green (default): proceed silently.** Reads, in-scope edits, tests, lints, subagent spawns.
- **Yellow: pause via `AskUserQuestion`.** Fires when the hook injects an `AUTOPILOT TRIGGER [<id>]:` line via `additionalContext`, OR when you recognize the trigger conditions yourself. Use the templates in `checkpoint-format/SKILL.md`.
- **Red: hard-stopped by the hook.** You will see `AUTOPILOT_GATE: blocked ...` on stderr. Do not retry; surface to the human in handback.

Class-B (brief-content-only) triggers from v1 are deliberately absent. Their function is subsumed by the `Assumed:` section of handback per `handback/SKILL.md`: enumerate every load-bearing decision you made without asking.

## Yellow-tier triggers (registry-generated)

### `irreversibility` (class A)

About to do something irreversible (push, force-push, publish, rm -rf, prod deploy). Pause and confirm.

**Detection**: Bash command matches one of 10 regex pattern(s) in `triggers/01-irreversibility.json`.

**On fire**: About to run an irreversible operation. Per autopilot:checkpoint-format, surface an AskUserQuestion with the specific command, options including a cancel path, before proceeding.

### `budget-tick` (class A-hybrid)

Approaching the per-session tool-call budget. Surface a budget checkpoint so the human can extend or hand back.

**Detection**: state counter `tool-calls` over tools [*]; yellow=50, red=150.

**On fire**: Tool-call budget at or near the yellow threshold. Per autopilot:checkpoint-format, surface a budget AskUserQuestion offering: extend budget by N, hand back now, or continue without ticking again.

### `decision-log` (class A-hybrid)

Multiple edits/writes have happened since the last decision-log entry. Invoke the decision-log skill to record the silent decision contemporaneously.

**Detection**: state counter `writes-since-dlog` over tools [Edit, Write, NotebookEdit]; threshold=3.

**On fire**: 3+ edits since last decision-log entry. Before the next edit, invoke the autopilot:decision-log skill to record the load-bearing decision behind this batch.

## Handback

End every task with the format in `handback/SKILL.md`. The `Assumed:` section is load-bearing — it is the audit trail for every silent decision you made without firing a trigger.
