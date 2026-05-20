# 0018. Treat v1 as a prototype; capture the v2 design

Date: 2026-05-19

## Status

Accepted (as decision to document v2; v2 implementation is deferred).

## Context

The autopilot plugin reached v0.3.0 with a working eval harness ([ADR-0017](./0017-rigorous-criteria-methodology.md)) and a documented baseline. Over the course of ~20 dogfood rounds and one audit pass, a coherent set of architectural lessons emerged that don't fit cleanly into incremental ADRs:

- **Skill-text-only triggers cap at 30–57 mean** ([ADR-0016](./0016-mechanism-vs-skill-text-triggers.md)). Iteration on them is a tax.
- **Skill text and hook config drift** because they're independent files describing the same rules.
- **Criteria written by the skill author confirm the skill author's assumptions** (the fixture-04 recovery: 67→100 mean from independent substring expansion, no agent code change).
- **Self-review is structurally inadequate** (P0 caught today by independent audit, missed by author review).
- **Defaults didn't enforce the methodology** (canonical baseline captured at n=3 vs documented `min_runs: 10` for Class B).
- **Doc surface > code surface** (17 ADRs + 4 long-form docs + READMEs produced 4 drift findings in a single audit pass).
- **The eval is a degraded proxy for the product** (`--print` mode breaks `AskUserQuestion` per [ADR-0014](./0014-askuserquestion-print-mode-limitation.md); the canonical baseline measures something the real plugin doesn't do).
- **Judge calibration is too expensive to bootstrap** (PR-7 of ADR-0017 sat blocked the entire session on 30–45 min of human labeling that never happened).

Each individual lesson could be a small ADR. Cumulatively they describe a different plugin — one whose architecture would be meaningfully different if started over today. Patching v1 to match would be larger than building v2.

A request was raised to capture the architecture v1 would have if rebuilt from scratch with these lessons in hand.

## Decision

1. **Treat v0.3.0 as the prototype.** It works, it shipped, it produced the lessons. It stays in production. No deprecation timeline.

2. **Capture the v2 design as `docs/design/autopilot-v2.md`** — a written architecture informed by the lessons, with explicit *keep / change / drop* lists anchored to observed costs. This is the document a future contributor (or future-Edison) would read to understand what to build.

3. **Defer the build-or-not decision.** Three migration paths are sketched (backport-by-backport, parallel v2 plugin, in-place rewrite) but no commitment is made. The trigger for any of them is a concrete pain point that v1's architecture would make hard to fix.

4. **No new ADRs for individual v2 lessons.** They're captured in the design doc with their evidence (commit refs, session dates, baseline numbers). ADRs are for decisions whose reason would be lost; the v2 design doc is that record.

5. **One acceptance condition for v2 if it ships:** the per-criterion pass-rate must equal or beat v1's published 94.7 at equal-or-stricter `n`, with no `UNDERRUN_SKIPPED` results. If v2 doesn't measurably improve on the baseline that motivated it, the rebuild failed.

## Consequences

Easier:

- v1 can stop accreting partial fixes for architectural problems (skill-text trigger ceiling, criteria-self-bias structural enforcement). Those go into the v2 design doc as "fixed in v2 design" rather than driving more v1 churn.
- The lessons stay captured in a form a contributor can act on, not just sympathetic to.
- Future sessions can reference the design doc instead of re-deriving the lessons from baseline JSONs and ADR archaeology.

Harder:

- The doc has to stay current as more is learned. If we discover a new lesson in v1, the v2 design should be updated, not a fresh ADR written.
- v1 and v2 (if built) may diverge in user-facing behavior in ways that need a CHANGELOG migration note. Cross that bridge if we build v2.
- A new contributor sees two architectures and may build for the wrong one. Mitigation: `CONTRIBUTING.md`'s "Before you start" reading list explicitly tags v2 as "a design, not a commitment" (this commit).

Constrains:

- The v2 design doc supersedes individual ADRs that the new design obsoletes. When v2 ships, those ADRs get `Status: Superseded by v2 design / ADR-0018` headers, not deletion. (Predicted candidates: [ADR-0010](./0010-task-type-specific-commands.md) on per-task commands, parts of [ADR-0011](./0011-eval-harness-design.md) already-superseded composite-scoring rationale, and the Class B half of [ADR-0016](./0016-mechanism-vs-skill-text-triggers.md).)
- Any future ADR proposing a change to v1's architecture should first check whether v2 design already addresses it. If yes, the question is "do we do this in v1 or just wait for v2" rather than "what should we do."
- Cost: ~1 hour to write the design doc + this ADR. Compared to incremental ADRs for each lesson (~30 min × 8 = 4 hours of accumulated documentation debt), this is cheaper and more coherent.

## What this ADR is NOT

- A commitment to build v2.
- A criticism of v1. v1's correctness is exactly what made the lessons findable.
- A roadmap. The design doc has a *sketch* of migration paths, not a chosen one.

The decision is: **we now have enough evidence to know what v2 should be, and we will preserve that evidence in a form the next builder can use.** Whether and when v2 ships is a separate decision.
