# 0001. Extend playbook with HITL patterns

Date: 2026-05-18

## Status

Accepted

## Context

The playbook's 12 standards cover developer-side procedures generally. Standard 12 (AI Agent Collaboration) treats agents as one operational concern: it covers what to put in `AGENTS.md` and how to review agent PRs at merge time. It does not address the *in-task* loop where a human supervises an agent making decisions step-by-step.

As agent autonomy increases (Claude Code, Cursor, autonomous coding agents), the gap is no longer hypothetical:

- Agents make architectural choices silently between checkpoints.
- "Review the PR" is too coarse a HITL surface — by then the silent decisions are already made.
- Teams lack shared vocabulary for "which mode is this work in" — pair? supervised? autonomous?
- Agent instruction files (`CLAUDE.md`, `AGENTS.md`, skills, hooks) are themselves software but aren't versioned, tested, or rolled back like software.

Standard 12 is necessary but not sufficient for human-in-the-loop development as a methodology.

## Decision

We will extend the playbook with a Human-in-the-Loop (HITL) framework that defines the in-task supervision loop. The framework lives at [`../hitl-framework.md`](../hitl-framework.md) and is implemented by the autopilot plugin at [`../../plugins/autopilot/`](../../plugins/autopilot/).

Scope of the framework:

1. Action classification — every action falls into a green/yellow/red tier.
2. Checkpoint mechanics — when and how the agent pauses for human input.
3. Pairing-mode vocabulary — named modes (pair, supervised, autonomous-with-PR).
4. Briefing and handback protocol — bidirectional structured handoffs.
5. Verification-efficiency playbook — how humans review agent output fast.
6. Agent-instructions-as-code — versioning, testing, rolling back `AGENTS.md` and skills.
7. Failure recovery and postmortem — agent-specific failure modes; rollback path.

Deferred for v0.1:
- Eval / measurement loop (revisit at v0.2 once we have ≥3 plugin iterations to compare).
- Cost / budget governance (revisit when token spend becomes load-bearing).
- Human-side onboarding (revisit when team grows beyond one).

## Consequences

Easier:
- A written methodology to point new collaborators (human or agent) at.
- Decisions about how to interact with agents become explicit, not improvised.
- The autopilot plugin has a written contract to implement against.

Harder:
- More documentation to maintain alongside the playbook's 12 standards.
- A second framework adjacent to standard 12 creates a "which to read first" question — resolved by treating HITL as an opt-in extension; standard 12 remains the entry point for projects that don't run high-autonomy agent workflows.

Constrains:
- Future autopilot-plugin work must align with the framework or supersede this ADR.
- New HITL tooling (other plugins, scripts, hooks) should adopt the framework's vocabulary.
