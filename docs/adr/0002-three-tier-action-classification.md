# 0002. Three-tier action classification (green/yellow/red)

Date: 2026-05-18

## Status

Accepted

## Context

Autonomous-with-checkpoints HITL requires the agent to decide, action-by-action, whether to proceed silently, pause for human input, or refuse and surface. Naive approaches fail:

- "Ask when uncertain" — models are poorly calibrated on uncertainty and tend to under-ask under task pressure.
- "Ask before everything" — trains the human to rubber-stamp; no real signal.
- A binary ask/proceed split provides no surface for truly destructive ops that should never proceed without explicit human action.

We need three behaviors, not two, with different enforcement layers per behavior.

## Decision

We will classify every action into one of three tiers, each enforced at the appropriate layer:

- **Green — proceed silently.** Reads, edits within briefed scope, tests, lints, subagent spawns, non-mutating git ops. The skill defines the list; the agent acts without confirmation.

- **Yellow — pause via `AskUserQuestion`.** Scope drift, architectural choices, ambiguity, external effects, non-destructive irreversibility, budget ticks. The skill defines categorical triggers (see [ADR-0004](./0004-categorical-ask-triggers.md)); the agent invokes `AskUserQuestion` with structured options (see [ADR-0003](./0003-askuserquestion-as-exclusive-hitl-surface.md)).

- **Red — hard-stopped by hook.** Destructive ops (`rm -rf`, force-push, publish, drop table, writes outside `cwd`). PreToolUse hook exits non-zero; agent surfaces to human and cannot work around (see [ADR-0006](./0006-hooks-as-sole-enforcement-layer.md)).

Enforcement layer per tier:

| Tier | Layer | Bypass failure mode |
|---|---|---|
| Green | Skill (advisory) | Over-asks → user ignores prompts |
| Yellow | Skill (advisory) | Under-asks → silent decisions in diff |
| Red | Hook (binding) | Destructive action ships |

## Consequences

Easier:
- Predictable behavior — the human knows what categories of action will pause them.
- Auditable — the skill text enumerates exactly what's in each tier.
- The agent cannot talk itself out of red-tier hooks.

Harder:
- The green-tier list must be exhaustive enough to cover normal work, or the agent stalls on permission prompts (defeating autonomy).
- The yellow-tier categorical list is opinionated; categories that don't fit a project need to be added explicitly.

Constrains:
- New tools and operations must be classified before they're used in autopilot mode.
- The autopilot plugin's hook regex must keep pace with new red-tier patterns.
