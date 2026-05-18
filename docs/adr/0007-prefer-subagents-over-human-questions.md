# 0007. Prefer subagents over human questions when the answer is researchable

Date: 2026-05-18

## Status

Accepted

## Context

In autopilot mode, every human question costs:

- The human's attention (the scarce resource HITL is trying to economize).
- Latency (the agent blocks until the human responds).
- Trust budget (too many asks habituate the human to skip-clicking).

Many questions the agent might ask have answers that are *researchable* — they exist in the codebase, in docs, or on the web. Asking the human is the wrong tool when a subagent could find the answer. The human's judgment is the scarce resource; their ability to grep is not.

## Decision

The autopilot plugin ships two subagents that the main agent invokes *in preference to* asking the human:

- **`scout`** — research agent. Find code, docs, or external info; return a focused synthesis. Tools: Read, Grep, Glob, WebFetch, WebSearch, Bash. Used instead of asking the human "what does X do?" or "where is Y defined?". Defined at [`../../plugins/autopilot/agents/scout.md`](../../plugins/autopilot/agents/scout.md).

- **`verifier`** — read-only second opinion. Tools: Read, Grep, Glob, Bash. Used before committing to an approach, or to verify completed work against a brief. Used instead of asking the human "is this approach correct?". Defined at [`../../plugins/autopilot/agents/verifier.md`](../../plugins/autopilot/agents/verifier.md).

Subagent invocations are green-tier (no confirmation required). The `autopilot/SKILL.md` instructs the agent to spawn a subagent when the question could be answered by reading more code or running a search.

The triage rule: **ask the human for judgment; ask a subagent for facts.**

## Consequences

Easier:
- The human is only asked when their *judgment* is genuinely needed, not when they could have been replaced by a search.
- Main context stays focused on decisions, not exploration (subagents have their own context).
- The verifier provides a second opinion without round-tripping the human.

Harder:
- Spawning subagents costs tokens. Heavy use during research-heavy tasks increases token spend.
- A wrong subagent answer that the main agent trusts is a silent failure mode. Mitigated by: handback report must flag assumptions made on subagent output.

Constrains:
- The subagent fleet (`scout`, `verifier`) is the load-bearing alternative to asking the human. Adding new subagents requires updating `autopilot/SKILL.md` to point at them so the main agent knows to prefer them.
- Subagents are read-only / research-only by design. If a subagent ever needs write access, this ADR should be revisited — write-capable subagents change the trust model significantly.

## Amendment — 2026-05-18

Implementation correction (decision unchanged). The original [`autopilot/SKILL.md`](../../plugins/autopilot/skills/autopilot/SKILL.md) referenced subagents using `[[verifier]]` / `[[scout]]` syntax. Verification against Claude Code docs revealed that `[[name]]` is the *skills* linking format; subagents are invoked either by description-match (auto-delegation) or explicit `@agent-name` mention. The skill has been updated to use `@agent-scout` / `@agent-verifier` mentions, which force delegation reliably.

This amendment does not change the decision — subagents are still preferred over human questions for researchable answers. It corrects the wiring that made the preference unreachable.

See also [ADR-0008](./0008-context-management-strategy.md) for *when* to spawn vs. read directly.
