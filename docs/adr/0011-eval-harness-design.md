# 0011. Eval harness for measuring plugin changes

Date: 2026-05-18

## Status

Accepted

## Context

Changes to the autopilot skill, hook regex, or subagent definitions can shift agent behavior in non-obvious ways. Without measurement, we ship blind — a new yellow-tier trigger might over-fire on common workflows; a regex tightening might false-block branch names. The HITL framework ([`../hitl-framework.md`](../hitl-framework.md)) originally listed "eval / measurement loop" as deferred. Re-evaluating, the deferral was wrong — the eval harness is the only mechanism that tells us whether plugin changes improve or degrade outcomes.

Constraints for the design:

- Solo developer; no infrastructure budget; no platform fees.
- Must be runnable locally in <5 min.
- Must produce comparable scores across plugin versions.
- Light enough to run before each merge (not quarterly).

## Decision

We will ship a lightweight Python eval harness under [`../../evals/`](../../evals/):

- **8 representative task fixtures** (`evals/tasks/*.yaml`) covering the trigger taxonomy: pure-green (over-asking detection), scope-drift bait, architectural fork, ambiguous brief, external effect, irreversible, researchable-not-askable, handback exercise. *(v0.1 ships 3; the user grows to 8 as they hit edge cases.)*

- **4 metrics** scored per task:
  - `appropriate_ask_rate` — correct asks / expected asks
  - `false_block_rate` — hook-blocked actions that should have passed
  - `silent_decision_rate` — expected asks that didn't fire
  - `handback_completeness` — structure + `Assumed` discipline, scored by Sonnet judge

- **Composite score** (0–100): `0.4*appropriate_ask + 0.3*(1-false_block) + 0.2*(1-silent_decision) + 0.1*handback`.

- **Ground truth = hardcoded fixtures + LLM judge.** Deterministic checks (regex over transcript + tool log) cover ~80% of scoring. The Sonnet judge only scores handback quality — pinned prompt template in [`../../evals/judge_prompt.md`](../../evals/judge_prompt.md) for cross-version comparability.

- **Tooling: hand-rolled Python.** ~250 LOC in [`../../evals/run.py`](../../evals/run.py). No framework. Stdlib + `pyyaml` + `anthropic`. Driver stubbed to `claude -p --output-format stream-json`.

- **Output:** `evals/results/<version>-<ts>.json` (gitignored). Markdown diff renderer is a future addition.

- **Merge gate (future):** no metric regresses >5 points vs. last version; aggregate score must not drop. CI integration is a follow-up.

## Consequences

Easier:
- Plugin changes have empirical justification, not vibes.
- Regressions caught before merge.
- Eval set doubles as a regression suite — every new postmortem (per [`../postmortems/`](../postmortems/)) adds a task that locks the fix.

Harder:
- Each plugin change now has a verification step. For a casual tweak this feels heavy.
- The driver stub depends on the user wiring up their local `claude -p` invocation; the harness ships scoring but not execution.
- Sonnet judge has cost (negligible at this scale — 8 tasks × 3 runs × ~$0.001 each).

Constrains:
- New yellow-tier triggers need eval coverage (a task that *should* trip the new trigger). Otherwise the trigger ships untested.
- Removing a trigger or relaxing a regex requires updating the eval fixtures that depend on the old behavior — supersede the fixture or mark it deprecated.
- The Sonnet judge prompt is load-bearing; changes to it invalidate cross-version comparisons. Pin in repo; supersede with new ADR if changed.
