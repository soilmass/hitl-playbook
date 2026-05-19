# 13 — Human-in-the-Loop (HITL) Agent Supervision

**Purpose:** when an AI agent runs long-horizon work autonomously, the human stays in the loop at *categorical decision points* — not at every tool call (too noisy) and not only at the final PR (too late). Standard 12 covers AI agent collaboration at the brief and review level; this standard covers the in-task supervision loop.
**Anchors:** vendor-specific autonomous-agent docs (Claude Code skills/hooks, Cursor rules, GitHub Copilot Workspace) · `evals.dev` and [`princeton-nlp/SWE-bench`](https://github.com/princeton-nlp/SWE-bench) for measurement patterns · [Anthropic's prompt-engineering guide](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering) (categorical-instruction framing).
**Tier:** Operations

---

## Why this procedure exists

"Review the PR" is too coarse a HITL surface for autonomous agents. By the time the diff lands, every silent decision is already made and the human has to reverse-engineer the agent's reasoning to know what to verify.

The opposite extreme — pair-mode confirmation on every action — also breaks down. Agents that ask before every tool call train the human to skip-click, and the meaningful asks get lost in noise.

The right surface is *in-task gates at categorical decision points*. The agent proceeds silently on routine work, pauses for structured input at branch points the human cares about, and is hard-blocked from destructive operations regardless of what the brief said.

**Failure modes when this procedure is missing:**

- Agents make architectural choices silently and the human discovers them only when reading the diff.
- Agents over-ask on routine work; the human habituates to ignoring all prompts.
- Agents destroy state (`rm -rf`, force-push, drop tables) when they think the brief authorized it.
- Teams have no shared vocabulary for "what supervision mode is this work under" and end up with mismatched expectations between human and agent.
- Agent operating instructions (rules, skills, hooks) are tweaked without measurement; nobody knows if a change improved or regressed behavior.

---

## The standard

### The three-tier action model

Every action the agent takes falls into one of three tiers. Classify before acting:

- **Green — proceed silently.** Reads, edits within briefed scope, tests, lints, research subagent spawns, non-mutating git ops. The agent has authority; the human does not see these.

- **Yellow — pause for structured input.** Scope drift, architectural choice between materially different approaches, ambiguous brief, external effect (sends to user/API/Slack/etc.), non-destructive irreversibility (commit, push, tag, publish), budget tick (every N tool calls, surface a "still on track?"). The agent invokes a structured-question mechanism and waits.

- **Red — hard-stopped.** Destructive operations (`rm -rf`, force-push, `npm publish`, `gh pr merge`, drop/truncate, `--no-verify`, writes outside the project directory, sends to external services). The agent's tooling refuses the operation; it surfaces the request and the human runs it themselves or explicitly authorizes.

Each tier has a different enforcement layer:

| Tier | Enforcement | Failure if missing |
|---|---|---|
| Green | Skill/rules (advisory) | Over-asking habituates human to skip prompts |
| Yellow | Skill/rules (advisory) | Silent decisions ship in the diff |
| Red | Hook (binding) | Destructive action ships |

### Categorical yellow-tier triggers

Don't ask agents to "ask when uncertain." Models are poorly calibrated on uncertainty and tend to under-ask under task pressure. Enumerate the triggers:

1. **Scope drift** — next action would touch files or systems outside the briefed scope.
2. **Architectural choice** — picking between two or more non-trivial approaches a reasonable human might disagree on.
3. **Ambiguous brief** — task admits multiple plausible interpretations and the choice is load-bearing.
4. **External effect** — action sends a message, posts to an API, opens a PR, deploys, or costs money beyond model tokens.
5. **Non-destructive irreversibility** — committing, pushing a branch, creating a tag, publishing a draft.
6. **Budget tick** — periodic "still on track?" surface, ideally ~every 10 tool calls.

These six are the load-bearing set. Projects can add more (e.g., "before touching the migrations directory") but should not remove these.

### Trigger-class enforcement

Categorical triggers split into two enforcement classes based on whether they're detectable at the tool-invocation layer:

**Class A — tool-input or aggregated-state detectable.** Examples: `budget_tick` (counter), `irreversibility` for `git commit`/`push` (pattern in command), `external_effect` for known endpoints (URL pattern), `decision-log skipped` (counter of writes since last log invocation). These should be enforced by hooks that inject context into the agent's next decision — not by skill-text alone, which the agent rationalizes away.

**Class B — brief-content only.** Examples: `architectural_choice`, `ambiguity`. These require understanding the brief's content, not the next tool call. Skill-text is the only lever and it has a ceiling — accept bimodal reliability and document the limit.

Empirically: Class A triggers with hook nudges reach ≥90% honor rate on capable models; Class B with skill-text-only reaches ~30-60% bimodal regardless of how strong the skill text is.

### The structured-question requirement

When the agent pauses at a yellow trigger, it must use a *structured question* mechanism (Claude Code's `AskUserQuestion`, Cursor's prompt UI, custom labeled-options tool), not free prose. Required format:

1. One-line status preamble (past tense): *"Read auth.ts and noted the existing session-token flow."*
2. The question — concrete and specific, not "should I proceed?"
3. 2–4 options, each with a short label (≤5 words) and a one-line consequence description.
4. Recommended option first, marked as such.

Prose questions degrade the HITL surface: free-text replies get re-parsed wrong, options are implicit, no visual distinction from narration, the human starts skimming.

### Handback protocol

When the agent completes a task (or is blocked), it produces a structured handback:

```
**Done:** <one-line summary>           (or Blocked: <what's stuck>)

**Changed:** <file:line — behavior changes only>
**Skipped:** <noticed but didn't do, with reason>
**Assumed:** <load-bearing assumptions made without asking — flag for review>
**Verify before merging:** <concrete spots to re-check; not "review the diff">
**Open questions:** <what you'd ask if the loop continued>
**Audit trail:** <pointer to the per-session log if one exists>
```

The **Assumed** section is the load-bearing audit trail for silent decisions made during the run. Reviewers verify those first.

### Agent-instructions-as-code

The agent's skills, rules, hooks, and subagent definitions are *software*. Treat them like software:

- Version-controlled in the same repo as the code they govern.
- Reviewed via PR.
- Changes documented in commit messages and ADRs (for significant rules).
- Revertable: if a new rule causes bad behavior, revert the rule.
- **Measurable.** Before merging any change to agent operating instructions, run an eval that scores the new behavior against a baseline. See "Eval discipline" below.

### Eval discipline

A change to a skill, rule, or hook can shift every future task the agent runs. You can't ship changes blind.

Minimum viable eval setup:

- A small set of *task fixtures* (5–10) covering the categorical triggers — each fixture has a brief, optional setup files, and expected behaviors (asks fire, hooks block, handback sections present).
- A *runner* that invokes the agent non-interactively against each fixture and captures the transcript.
- A *scorer* that compares observed behavior to expected: how often did the agent ask appropriately, how often did the hook fire, did the handback have the required structure.
- A *baseline* snapshot of scores at the current version. Run before and after every plugin change; diff them.

Recommended scoring shape (composite of four metrics, weights configurable):

- `appropriate_ask_rate` — expected yellow asks that actually fired
- `false_block_rate` — hook-blocked actions that should have passed
- `silent_decision_rate` — expected yellow asks that did NOT fire
- `handback_completeness` — required sections present + Assumed field non-empty when applicable

Statistical caveats: n=3 runs per fixture is the practical minimum; variance band is ±20 composite points. For decisions at the 5-point margin, run n=10.

### Failure recovery and postmortems

When an agent change ships and breaks something:

1. **Revert first.** Roll back the offending change. Don't fix forward under pressure.
2. **Postmortem** with category — was the plugin under-gated (should have caught), over-gated (caused agent to ignore prompts), user judgment (yellow fired correctly, user accepted wrong), or model failure (guardrails fine, model still produced bad output)?
3. **Drive a concrete follow-up.** New categorical trigger, new red-tier pattern, new subagent check, ADR superseding a previous one, or "no action — accepted risk."
4. **Add a regression fixture** to the eval set that would catch this specific failure.

Postmortems live in a `docs/postmortems/` directory, append-only, indexed by date.

---

## PROJECT-SPECIFIC — fill these in

```markdown
## Supervision mode for this project

[Pick one as the default: pair / supervised / autonomous-with-PR.]

## Yellow-tier triggers (project-specific additions to the standard 6)

- <e.g., "Before touching the migrations/ directory">
- <e.g., "Before changing any file in src/auth/">

## Red-tier patterns (additions to the destructive baseline)

- <e.g., "Any kubectl apply against prod context">
- <e.g., "Any write to .env.production">

## Eval set location

- Path: <e.g., evals/tasks/>
- Runner: <e.g., python3 evals/run.py>
- Baseline: <e.g., evals/results/baseline-canonical.json>

## Recommended model

- <e.g., Sonnet — Haiku reduces trigger compliance per our internal eval>

## Audit log location

- <e.g., .claude/autopilot-logs/<session-id>.{jsonl,md}>
```

---

## Cross-references

- [`12-agents.md`](./12-agents.md) — covers agent collaboration at the brief and PR-review level; this standard extends it with in-task supervision.
- [`03-code-review.md`](./03-code-review.md) — agent PRs are reviewed via the same process; this standard reduces what humans must verify by surfacing assumptions in the handback.
- [`10-security.md`](./10-security.md) — the red-tier destructive list overlaps the security threat model; coordinate the two.
- [`11-adrs.md`](./11-adrs.md) — significant changes to agent operating instructions get ADRs.

External implementation reference: this repo's [`docs/hitl-framework.md`](../docs/hitl-framework.md) (project methodology) and [`plugins/autopilot/`](../plugins/autopilot/) (working implementation for Claude Code with eval harness at [`evals/`](../evals/)).

---

## Maintenance cadence

- **Per eval regression:** investigate before the next plugin merge; either accept the regression with a documented reason or roll back the change.
- **Per shipped postmortem (`docs/postmortems/`):** ensure the follow-up landed (new trigger / regex / fixture / ADR).
- **Per quarter:** re-run the canonical eval baseline; update the baseline snapshot in `evals/README.md`.
- **On framework upgrade** (new agent model, new harness version): re-baseline and check for behavior shifts; document significant changes in the changelog.
- **Owner:** the team's tech lead or designated agent-operations owner.
