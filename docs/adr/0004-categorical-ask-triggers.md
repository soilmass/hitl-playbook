# 0004. Categorical ask triggers (not confidence-based)

Date: 2026-05-18

## Status

Accepted

## Context

For yellow-tier pauses (see [ADR-0002](./0002-three-tier-action-classification.md)), we evaluated three strategies for when the agent should ask:

1. **Model-judged confidence** — "ask when uncertain." Skill instructs the agent to call `AskUserQuestion` when it lacks confidence.
2. **Budget-driven** — ask every N tool calls or every X minutes regardless of content.
3. **Categorical** — an enumerated list of situations that trigger an ask (scope drift, architectural choice, irreversibility, etc.).

Confidence-based is appealing in theory but unreliable in practice: models are poorly calibrated on uncertainty and tend to under-ask under task pressure. Budget-driven is predictable but ignores actual risk — it asks at fixed intervals during safe work and skips asks during risky work.

## Decision

We will use **categorical triggers** as the primary mechanism, with a single budget-driven trigger as a safety-net fallback.

The categorical list, defined in [`../../plugins/autopilot/skills/autopilot/SKILL.md`](../../plugins/autopilot/skills/autopilot/SKILL.md):

1. Scope drift — next action would touch files or systems outside the briefed scope.
2. Architectural choice — picking between two or more non-trivial approaches a reasonable human might disagree on.
3. Ambiguous brief — task admits multiple plausible interpretations and the choice is load-bearing.
4. External effect — action sends a message, posts to an API, opens a PR, deploys, or costs money beyond model tokens.
5. Non-destructive irreversibility — committing, pushing a branch, creating a tag, publishing.
6. **Budget tick** — ~every 10 tool calls, surface a "still on track?" checkpoint (the single budget-driven trigger, acting as a safety net for risk that fits no category).

## Consequences

Easier:
- Predictable behavior — the human can anticipate when asks will happen.
- Auditable — the trigger list is enumerated, not implicit in model judgment.
- The agent cannot rationalize its way past a categorical trigger.

Harder:
- The trigger list is project-agnostic; some projects will need additions (e.g., "ask before touching the migrations directory").
- Categorical triggers don't catch novel risk that fits no category — the budget tick is the safety net for this, but it's coarse.

Constrains:
- Adding a new trigger category is a deliberate edit to `autopilot/SKILL.md`, not a runtime adjustment.
- Removing a trigger requires this ADR to be superseded by an explicit replacement.
