# 0010. Task-type-specific autopilot commands

Date: 2026-05-18

## Status

Accepted

## Context

The original autopilot plugin shipped one entry point: `/autopilot <task>`. The base skill encodes generic yellow-tier triggers (scope drift, architectural choice, ambiguity, etc.) that apply to any task.

But different task types have different default failure modes and benefit from different default checkpoints. Examples:

- **Bug fixes** — the silent failure is fixing the symptom not the cause. The yellow-tier trigger missing from the generic list is "modifying production code without first reproducing the bug."
- **Refactors** — the silent failure is changing behavior accidentally. The missing trigger is "modifying tests in the same diff as the refactor."
- **Dependency updates** — the silent failure is auto-resolving conflicts or adding new top-level packages. Different red-tier than feature work.
- **Test work** — the silent failure is silently fixing production code to make a new test pass. Different scope discipline.
- **Chores** — the silent failure is letting mechanical work touch semantic code. Tighter scope guard.

A one-size-fits-all `/autopilot` either has too many triggers (over-asks on simple tasks) or too few (under-asks on specialized ones).

## Decision

We will ship six task-type-specific commands alongside the generic `/autopilot`:

| Command | Purpose | Key specialized trigger |
|---|---|---|
| `/autopilot-bugfix <brief>` | Reproduce → isolate → fix → regression test | Pause before non-test code edit if bug not reproduced |
| `/autopilot-refactor <brief>` | Restructure without changing behavior | Block test changes in same diff as refactor |
| `/autopilot-feature <brief>` | Build a scoped capability end-to-end | Pause after plan, before code; on architectural forks |
| `/autopilot-deps <brief>` | Bump/add/audit dependencies | Pause on major bumps, new top-level deps |
| `/autopilot-tests <brief>` | Add coverage without touching production | Block edits outside test dirs |
| `/autopilot-chore <brief>` | Mechanical maintenance | Block semantic edits when brief is format-only |

Each command file in [`../../plugins/autopilot/commands/`](../../plugins/autopilot/commands/) loads the base `autopilot` skill and adds task-type-specific:

- Additional yellow-tier checkpoints.
- Additional red-tier patterns (not enforced by hook — those stay generic — but instructed in the command body so the agent surfaces instead of acting).
- Handback emphasis (which sections to foreground).

The generic `/autopilot <task>` remains for tasks that don't fit a type, or for tasks where the user explicitly wants base behavior.

## Consequences

Easier:
- The user picks the right command for their task and gets appropriate-rate checkpoints out of the box.
- The base autopilot skill stays generic; specializations live in the command files, easy to add more later.
- Handback reports are task-appropriately structured (a bugfix handback foregrounds root cause, not new surface area).

Harder:
- 7 commands to maintain instead of 1. Each shares the base skill but has its own specialization text that can drift.
- Users must remember which command exists; a wrong choice gives wrong defaults. Mitigated by surfacing the list in `plugins/autopilot/README.md` and `/help`.

Constrains:
- Adding a new task type means a new command file; updating the spec for a type means editing one command file (not all).
- Specialized red-tier patterns are advisory (skill-enforced), not hook-enforced, because the hook regex is one global regex and can't be parameterized per command. If a specialized rule becomes load-bearing, it should be promoted to the hook (and probably also become a new ADR superseding part of [ADR-0006](./0006-hooks-as-sole-enforcement-layer.md)'s scope).
