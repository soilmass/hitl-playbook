# 0012. Cost/budget governance via tool-call counter

Date: 2026-05-18

## Status

Accepted

## Context

Long autopilot runs can run away — an agent stuck in a retry loop will burn through tokens, time, and patience without ever surfacing. Without a budget mechanism, the only failsafe is the human noticing the session has gone too long.

Candidate signals to track:

- **Token counts** — most direct cost measure, but transcript JSON `usage` parsing from a hook is fragile and tokens are an Anthropic-side concept.
- **Wall-clock time** — captures "stuck thinking" but noisy.
- **Tool calls** — strong proxy for both cost and progress; what actually runs away in pathological loops.
- **Files modified** — scope signal, not cost signal.
- **External API spend** — out of scope for a generic plugin.

Enforcement design space:

- A 4th tier (green/yellow/red/budget)? Fractures the model — every decision now has more dimensions.
- Hard-stop only? Loses chance to redirect mid-run.
- Soft + hard thresholds? Best of both: warn at soft, block at hard.

## Decision

We will track **tool-call count** as the primary budget unit, with two thresholds enforced by the existing hook layer:

- **Yellow at 50 tool calls** — `pretool-budget` hook prints a stderr warning instructing the agent to surface a `still-on-track?` checkpoint via `AskUserQuestion`. Non-blocking (exit 0). Fires exactly once at the threshold.

- **Red at 150 tool calls** — `pretool-budget` hook exits 2 with `"budget exceeded. Hand back to human."`. Identical mechanism to destructive-op block.

Both thresholds overridable via `AUTOPILOT_BUDGET_YELLOW` / `AUTOPILOT_BUDGET_RED` env vars.

Counter state: `$CLAUDE_PROJECT_DIR/.claude/autopilot-logs/<session-id>.budget` — single-integer file, incremented in `posttool-log`. No daemon, no IPC.

Surfacing:
- `/budget` command — prints counter, breakdown by tool, elapsed time, status (green/yellow/red).
- Handback report includes a one-line `Budget:` field.

**Budget is a transverse concern, not a 4th tier.** Budget exhaustion *triggers* an existing tier:
- Soft (yellow): fires a yellow checkpoint, reusing the established `AskUserQuestion` surface ([ADR-0003](./0003-askuserquestion-as-exclusive-hitl-surface.md)) and counting as the "budget tick" trigger in [ADR-0004](./0004-categorical-ask-triggers.md)'s categorical list.
- Hard (red): fires a red block, identical to destructive-op enforcement ([ADR-0006](./0006-hooks-as-sole-enforcement-layer.md)).

Defaults (50 / 150) align with: Anthropic's published SWE-bench Verified runs averaging 30–50 tool calls per resolved task; Claude Code public traces clustering at 80–120 turns before natural handback. 150 gives headroom for legitimately large tasks while catching runaways.

Not tracked in v0.1: token counts (transcript parsing fragility), wall-clock time (noise), external API spend (out of scope).

## Consequences

Easier:
- Runaway sessions hard-stop before consuming unbounded resources.
- The "budget tick" trigger now has a concrete implementation, not just text in the skill.
- Users can tune their own thresholds via env vars without code changes.

Harder:
- One more file in `.claude/autopilot-logs/` per session.
- The yellow warning only fires *once* (at the exact threshold). If the agent ignores it on the next tool call, the warning is gone until red. Deliberate — repeated warnings on every subsequent call would be noise.
- The 50/150 defaults are calibrated for general coding tasks; teams with different workflows will tune. The env-var override means no plugin update needed.

Constrains:
- Adding wall-clock or token tracking is a future extension, not in v0.1.
- The `/budget` command depends on file layout under `.claude/autopilot-logs/`; if [ADR-0009](./0009-audit-trail-mechanism.md) changes the layout, `/budget` must update.
