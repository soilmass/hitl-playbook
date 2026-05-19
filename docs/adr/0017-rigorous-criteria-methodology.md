# 0017. Rigorous criteria methodology — per-criterion binary scoring, bootstrap-CI gating, judge calibration

Date: 2026-05-19

## Status

Accepted

## Context

The autopilot plugin's eval harness (`evals/run.py`, 10 fixtures, 3 mechanism-fixed Class A triggers, 2 persistent Class B gaps) has been running for ~20 dogfood rounds. The methodology — a 4-metric weighted composite (`appropriate_ask_rate * 0.4 + (1-false_block_rate) * 0.3 + (1-silent_decision_rate) * 0.2 + handback_completeness * 0.1`) scored to a 0–100 composite — produced useful empirical signal but has serious confounds that increasingly limit further iteration.

Audit during planning surfaced **10 confound sources** in the current scoring:

1. n=3 ±20 variance band vs 5-point merge gate (mismatch — gate fires on noise)
2. `AskUserQuestion` calls counted as evidence of caution even though they auto-fail in `--print` mode ([ADR-0014](./0014-askuserquestion-print-mode-limitation.md))
3. Regex classifier (`_classify_ask` in `run.py`) brittle on question wording; misclassifies based on keyword position
4. Hook block (`is_error: true`) conflated with intentional gating — could be Claude Code permission system, not the plugin
5. Handback substr check passes on empty content ("Done: nothing" still matches "Done:")
6. Sonnet judge variance unquantified; no inter-rater reliability against humans
7. Fixture `expected_asks` undocumented as aspirational (plugin *should* ask) vs empirical (observed asking)
8. Tool calls treated as independent; no temporal validation (ask AFTER action counts the same as ask BEFORE)
9. Setup commands run with `check=False`; silent failures (e.g., `git init` not running) corrupt downstream scoring
10. Cost decoupled from composite; a regression with 10x cost spike still "passes"

**8 decision points the current methodology cannot distinguish** when a score moves: plugin behavior actually changed vs fixture testing the wrong thing vs classifier missed an ask vs noise from low n vs model variability vs hook-block source vs ask timing vs assumption-was-actually-documented.

External research surfaced 8 principles from mature eval frameworks (Inspect AI dataset/solver/scorer separation, METR epochs for bimodal behavior, OpenAI HealthBench analytic-over-holistic, binary > Likert for LLM judges, Gwet's AC2 ≥ 0.7 for judge calibration, paired bootstrap CI > absolute scores, fixture-vs-system separation via no-plugin baseline, actionable criteria with 1:1 failure→remediation).

The user framing: *"find correct criteria to base the output on to figure out how to fix the input and the system."* The current composite cannot distinguish input failures (brief/fixture defects) from system failures (plugin code) from measurement failures (judge drift). Every iteration round produces signal entangled with noise.

## Decision

We will replace the weighted composite with a **flat list of binary per-criterion checks**, each tagged with `target_artifact` (the single file to open when the criterion fails) and `class` (A / A-hybrid / B per ADR-0016). Composite remains as a reporting summary but never gates merges.

The full methodology shift is implemented across 8 PRs (see `/home/edo/.claude/plans/do-it-again-by-enchanted-adleman.md` for the implementation playbook):

1. **Fixture schema scaffolding** — add `criteria`, `tests_class`, `target_artifacts`, `min_runs`, `aspirational` keys to fixture YAMLs.
2. **Scorer v2 dual-write** — per-criterion checks in `evals/scorer/criteria.py`; results JSON gains `schema_version: 2` alongside `composite_v1` for back-compat.
3. **Temporal validation + hook-block classifier** — ask-before-action checking; `AUTOPILOT_GATE:` stderr marker distinguishes intentional gates from permission denials.
4. **Noise-floor baseline + fixture health pre-check** — `--baseline-mode noplugin` flag, fixtures whose with-plugin vs no-plugin delta CI crosses zero get auto-quarantined.
5. **Statistical machinery** — Wilson CIs, paired bootstrap (10k resamples) on Δp̂, effect-size floor (|Δ| ≥ 0.15) replaces 5-point absolute rule.
6. **Judge calibration** — `evals/judge/{rubrics,labels,calibration}` infrastructure; rubrics binary-only; gate judge use on Gwet's AC2 ≥ 0.7 against ≥20 human labels.
7. **Migrate handback to calibrated binary rubrics** — drop substr+judge blending; each handback section is its own binary criterion.
8. **Deprecate v1 schema** after 2 baselines collected under v2.

**North-star principle** (the acceptance test for the upgrade itself): every metric value must be traceable to exactly one of (a) a fixture/brief defect, (b) a specific skill/hook/command file, or (c) judge/scorer drift. If a score moves and you can't name the file to open, the criterion is wrong.

## Consequences

Easier:
- Diagnostic loop is mechanical: read failing criteria → list of `target_artifact` files to open → 1:1 remediation.
- Future iteration rounds produce actionable signal instead of noise-entangled signal.
- Test-design failures (broken fixtures) are surfaced separately from system failures (broken plugin) via the noise-floor pre-check.
- Cross-version comparison gets statistical rigor; the 5-point heuristic gate is replaced by paired bootstrap CI on effect-size.

Harder:
- Implementation cost: ~2-3 weeks across 8 PRs + ~$15-25 in eval spend for re-baselines and calibration runs. Break-even after ~5-10 future iteration rounds (currently ~weekly at $1-3 each).
- Judge calibration adds a labeling burden (20+ human-judged transcripts per rubric, per significant rubric change). Mitigation: cap calibrated rubrics at 5; rely on binary substring criteria for the rest.
- Fixture authoring is more verbose — per-criterion specification instead of one-line `expected_asks: [<categories>]`.
- Dual-write transition period requires running both v1 and v2 scoring; cost slightly higher during transition.

Constrains:
- New fixtures MUST declare criteria with `target_artifact`. A fixture with no `target_artifact` is by definition non-actionable.
- New trigger types MUST be classified (A / A-hybrid / B per ADR-0016) and have a corresponding criterion in at least one fixture.
- Judge rubrics MUST be binary; Likert and fractional fallback are removed. A judge that cannot answer yes/no with AC2 ≥ 0.7 is treated as uncalibrated and that criterion is reported as skipped, not failed.
- The "5-point regression" rule from [ADR-0011](./0011-eval-harness-design.md) is superseded. Going forward, regressions are flagged on per-criterion Δp̂ CI excluding zero AND effect size ≥ 0.15.

## Related work

- [ADR-0011](./0011-eval-harness-design.md) — the original eval design; this ADR supersedes its merge-gate rule.
- [ADR-0014](./0014-askuserquestion-print-mode-limitation.md) — print-mode AskUserQuestion limit (the eval measures intent only).
- [ADR-0015](./0015-pretool-hook-stderr-invisibility.md) — additionalContext stdout mechanism; relevant to the `AUTOPILOT_GATE:` stderr marker introduced for block classification (different channel, different purpose).
- [ADR-0016](./0016-mechanism-vs-skill-text-triggers.md) — Class A / A-hybrid / B trigger classification; PR-1's fixture schema makes this explicit per fixture.

## Why now, not earlier

Earlier rounds (commits `7996f34` through `c20e789`) produced enough empirical findings (e.g., the budget-tick mechanism going 30 → 96.7) that the composite scoring was clearly tracking real signal. But the more recent rounds (e.g., `92f7a2f` showing 03/04/07 "regressions" of -20+ alongside the genuine 05 improvement of +23) increasingly mixed real signal with noise the methodology couldn't disambiguate. The decision-log mechanism at v0.3.0 (`ac14c27`) used per-fixture probes rather than the canonical baseline precisely because the composite was no longer trusted at the individual-task level. That was the signal that the methodology had hit its useful range.
