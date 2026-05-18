# <slug>

- **Date:** YYYY-MM-DD
- **Run:** <branch / PR / commit reverted>
- **Plugin version:** <autopilot vX.Y.Z>
- **Time to fill:** target ≤ 15 min

## What shipped

One paragraph. What the brief was, what the agent did, what broke.

## Category (pick one)

- [ ] **A. Plugin under-gated** — should have paused at yellow/red, didn't.
- [ ] **B. Plugin over-gated** — asked so often the prompts were ignored.
- [ ] **C. User judgment** — yellow checkpoint fired correctly; user accepted wrong option.
- [ ] **D. Model failure** — guardrails were correct; the model still produced a bad change.

## Trace

- **Brief given:**
- **Silent decisions the agent made:** (cross-reference `.claude/autopilot-logs/<session>.md`)
- **Checkpoint that should have fired:**
- **Why it didn't:** (missing regex / wrong tier / no matching trigger / N/A)
- **Audit trail link:** `.claude/autopilot-logs/<session-id>.{md,jsonl}`

## Follow-up (at least one box required)

- [ ] **New categorical trigger** in `plugins/autopilot/skills/autopilot/SKILL.md` — describe:
- [ ] **New red-tier regex** in `plugins/autopilot/hooks/guard.mjs` — pattern:
- [ ] **New subagent check** in `plugins/autopilot/agents/verifier.md` (or new agent) — purpose:
- [ ] **New ADR** superseding `adr/NNNN-...` — decision:
- [ ] **Eval task added** in `evals/tasks/` to catch this regression — task ID:
- [ ] **No action — accepted risk.** Justification:

## Playbook updates

- [ ] Added case study to `AGENTS.md` (if the project has one)
- [ ] Bumped plugin version (if A or B)
- [ ] Added regression entry to `evals/tasks/`
- [ ] Updated postmortem index in `docs/postmortems/README.md`
