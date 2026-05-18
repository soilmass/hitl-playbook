# HITL Framework

**Status:** v0.1 — initial draft (2026-05-18).
**Extends:** [`../standards/12-agents.md`](../standards/12-agents.md). Standard 12 is necessary but not sufficient for HITL as a methodology.
**Implemented by:** [`../plugins/autopilot/`](../plugins/autopilot/) — see [`autopilot-plugin.md`](./autopilot-plugin.md).

---

## Why this framework exists

The playbook's standard 12 covers what to put in `AGENTS.md` and how to review agent PRs at merge time. It does not address the *in-task* loop where a human supervises an agent making decisions step-by-step.

"Review the PR" is too coarse a HITL surface — by the time the diff lands, every silent decision has already been made. HITL as a methodology needs procedures for the in-task gates, not just the merge gate.

This framework defines those procedures. It treats the human's attention as the scarce resource and the agent's autonomy as the default; asks are surgical, structured, and rare.

---

## The seven components

### 1. Action classification

Every action the agent takes falls into one of three tiers:

- **Green — proceed silently.** Reads, in-scope edits, tests, lints, subagent spawns.
- **Yellow — pause via structured question.** Scope drift, architectural choice, ambiguity, external effect, irreversibility, budget tick.
- **Red — hard-stopped.** Destructive ops; agent surfaces to human and cannot work around the stop.

Each tier has a different enforcement layer:

| Tier | Layer | Failure if bypassed |
|---|---|---|
| Green | Skill (advisory) | Over-asking habituates the human to skip prompts |
| Yellow | Skill (advisory) | Under-asking ships silent decisions in the diff |
| Red | Hook (binding) | Destructive action ships |

See [ADR-0002](./adr/0002-three-tier-action-classification.md).

### 2. Checkpoint mechanics

Yellow-tier pauses use **structured questions exclusively** — never prose. Prose questions degrade the HITL surface: free-text replies get re-parsed wrong, options are implicit, no visual distinction from narration.

Every checkpoint follows a fixed format:

1. One-line status preamble (past tense) in the surrounding message.
2. A concrete, specific question — not "should I proceed?".
3. 2–4 options, each with a label (≤5 words) and a one-line consequence.
4. Recommended option first, marked "(Recommended)".

See [ADR-0003](./adr/0003-askuserquestion-as-exclusive-hitl-surface.md) and the canonical templates in [`../plugins/autopilot/skills/checkpoint-format/SKILL.md`](../plugins/autopilot/skills/checkpoint-format/SKILL.md).

### 3. Pairing-mode vocabulary

Three named modes so the team has shared language for "what kind of work is this":

- **Pair** — real-time, every action confirmed. Human leads; agent assists.
- **Supervised** — agent works autonomously, pauses at categorical checkpoints. Default for autopilot.
- **Autonomous-with-PR** — agent ships a PR without checkpoints; human reviews at merge. Standard 12's territory.

The mode is named at task start. Mismatched expectations between human and agent on the mode is the most common source of HITL friction — the human thought it was supervised; the agent ran autonomous.

### 4. Briefing and handback protocol (bidirectional)

Briefing (human → agent) follows standard 12's checklist: what to build, stack context, conventions, hard rules, where to verify, acceptance criteria.

Handback (agent → human) at task end follows the format in [`../plugins/autopilot/skills/handback/SKILL.md`](../plugins/autopilot/skills/handback/SKILL.md):

- **Done / Blocked:** headline.
- **Changed:** behavior changes only, with `file:line`.
- **Skipped:** noticed but didn't do, with reason.
- **Assumed:** load-bearing assumptions made without asking.
- **Verify before merging:** concrete spots to re-check.
- **Open questions:** what you'd ask if the loop continued.

The **Assumed** section is the audit trail for silent decisions. Without it, the human cannot tell what was decided without a checkpoint. It is the most load-bearing field in the whole protocol.

### 5. Verification-efficiency playbook

Reviewing agent output is a different skill than reviewing human PRs. Agents fail differently:

- Confidently hallucinated APIs and imports.
- Scope creep ("I also cleaned up X while I was there").
- Fabricated comments that misstate what the code does.
- Sycophantic acceptance of bad direction.
- Claimed verification that didn't happen (the agent says it ran the tests but didn't).

Recommended verification approach for agent PRs:

1. Trust the handback's **Done** line; verify it.
2. Verify every **Assumed** entry — these are the silent decisions you're auditing.
3. Spot-check **Changed** entries at the `file:line` level.
4. Re-run anything the agent *claimed* it ran.

The plugin's `verifier` subagent provides programmatic second-opinion verification before commitment, reducing the load on the human reviewer.

### 6. Agent-instructions-as-code

`AGENTS.md`, `CLAUDE.md`, skills, hooks, and subagent definitions are software. Treat them like software:

- Version-controlled in the same repo as the code they govern.
- Reviewed via PR.
- Changes documented in commit messages and ADRs (for significant rules).
- Revertable: if a new rule causes bad behavior, revert the rule, not just the bad output.

This is the highest-leverage component. A change to the agent's operating instructions shifts every future task; treating that change casually is the same mistake as casually editing production code.

### 7. Failure recovery and postmortem

When an agent change ships and breaks something:

1. **Revert first.** Roll back the offending change. Don't fix forward under pressure.
2. **Postmortem.** Use [`postmortems/TEMPLATE.md`](./postmortems/TEMPLATE.md). 4-category classification (under-gated / over-gated / user judgment / model failure) drives the follow-up.
3. **Update.** Add the failure mode to `AGENTS.md`'s case studies. If the cause is in the autopilot plugin (missed regex, wrong tier classification), update the plugin and bump its version (per [ADR-0011](./adr/0011-eval-harness-design.md) — add a regression eval task too).
4. **Backfill an ADR if the fix represents a new decision.**

Active postmortem index: [`postmortems/README.md`](./postmortems/README.md).

---

## Promoted from deferred (now shipping)

Originally deferred at v0.1, promoted on 2026-05-18 after the gap-analysis sweep:

- **Eval harness** ([ADR-0011](./adr/0011-eval-harness-design.md)) — at [`../evals/`](../evals/). Composite score with 4 metrics; runs in <5 min.
- **Cost / budget governance** ([ADR-0012](./adr/0012-cost-budget-via-tool-call-counter.md)) — tool-call counter with yellow (50) / red (150) thresholds, hook-enforced. `/budget` command for status.
- **Audit trail** ([ADR-0009](./adr/0009-audit-trail-mechanism.md)) — PostToolUse JSONL log + `decision-log` skill + `/autopilot-review` command.

## Still deferred

- **Human-side onboarding for HITL.** Team is one person; revisit when it grows.

When any deferred component activates, it gets its own ADR and a section here.

---

## Decisions

See [`adr/`](./adr/). Numbered in order. Append-only per [`../standards/11-adrs.md`](../standards/11-adrs.md) — to change a decision, supersede it with a new ADR.

| # | Decision |
|---|---|
| [0001](./adr/0001-extend-playbook-with-hitl-patterns.md) | Extend playbook with HITL patterns |
| [0002](./adr/0002-three-tier-action-classification.md) | Three-tier action classification (green/yellow/red) |
| [0003](./adr/0003-askuserquestion-as-exclusive-hitl-surface.md) | AskUserQuestion as the exclusive HITL surface |
| [0004](./adr/0004-categorical-ask-triggers.md) | Categorical ask triggers (not confidence-based) |
| [0005](./adr/0005-both-entry-modes-for-autopilot.md) | Both entry modes for autopilot (slash command + env var) |
| [0006](./adr/0006-hooks-as-sole-enforcement-layer.md) | Hooks as the sole enforcement layer for destructive ops |
| [0007](./adr/0007-prefer-subagents-over-human-questions.md) | Prefer subagents over human questions when researchable |
| [0008](./adr/0008-context-management-strategy.md) | Context management strategy for autopilot |
| [0009](./adr/0009-audit-trail-mechanism.md) | Audit trail mechanism (hook + decision log) |
| [0010](./adr/0010-task-type-specific-commands.md) | Task-type-specific autopilot commands |
| [0011](./adr/0011-eval-harness-design.md) | Eval harness for measuring plugin changes |
| [0012](./adr/0012-cost-budget-via-tool-call-counter.md) | Cost/budget governance via tool-call counter |
| [0013](./adr/0013-cross-platform-node-helper.md) | Cross-platform Node helper for hooks |

---

## Maintenance

- **Per autopilot plugin version:** confirm this framework still aligns with what the plugin actually does.
- **Per significant agent failure:** add to component 7 examples; update relevant skills.
- **Quarterly:** re-evaluate the deferred components.
- **Owner:** Edison Steele.
