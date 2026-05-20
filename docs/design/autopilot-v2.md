# autopilot v2 — from-scratch design

**Status:** design draft (2026-05-19). Not implemented. Companion to [ADR-0018](../adr/0018-rebuild-from-lessons-learned.md).

**Audience:** future-Edison or a contributor picking this up. v1 (`plugins/autopilot/` at v0.3.0) is the working prototype. v2 is what you'd build if you started over today, knowing what v1 taught.

**Constraint:** this is a design doc, not a migration plan. v1 stays in production. v2 either ships as a parallel `plugins/autopilot-v2/` (cutover later) or is selectively backported. That decision is deferred.

---

## What v1 got right (keep)

These are not "good enough" — they're proven by ≥18 baselines and survived audit. Carry forward verbatim:

- **Three-tier action model** (green/yellow/red) per [ADR-0002](../adr/0002-three-tier-action-classification.md). The taxonomy held up across 10 fixtures and many real tasks.
- **`AskUserQuestion` as exclusive HITL surface** per [ADR-0003](../adr/0003-askuserquestion-as-exclusive-hitl-surface.md). Prose questions never resurfaced as a need.
- **Handback format**: `Done / Changed / Skipped / Assumed / Verify-before-merging / Open-questions`. The `Assumed:` field is the load-bearing audit trail for silent decisions. Hit 100% pass rate across the canonical baseline.
- **Categorical triggers, not confidence-based** per [ADR-0004](../adr/0004-categorical-ask-triggers.md). Confidence thresholds drift; categories are auditable.
- **Hooks as the sole enforcement layer for destructive ops** per [ADR-0006](../adr/0006-hooks-as-sole-enforcement-layer.md). Skill text the model can override is not enforcement.
- **Verifier subagent** for second-opinion code review. Fixture 10 confirmed it catches real bugs (SQL injection trap).
- **`additionalContext` stdout JSON for soft nudges** per [ADR-0015](../adr/0015-pretool-hook-stderr-invisibility.md). Stderr is invisible; this is the working channel.
- **Per-criterion bootstrap-CI gating** per [ADR-0017](../adr/0017-rigorous-criteria-methodology.md). The composite-score era is over; don't go back.
- **State-tracked-at-tool-layer pattern** (the writes-since-last-skill counter for decision-log). The breakthrough that turned a documented Class B gap into a 100% Class A trigger. Generalize this aggressively.

## What v1 got wrong (change)

Each item is anchored in an observed cost from session 2026-05-19 (and prior).

### 1. Skill-text-only triggers are a tax, not a feature

**v1 reality:** triggers split A (hook-detectable) vs B (brief-content-only) per [ADR-0016](../adr/0016-mechanism-vs-skill-text-triggers.md). Class B triggers depend on the model noticing trigger conditions in the brief. Their **trigger-fire rate** caps around 30–57% on Sonnet (Haiku ignores them entirely). Observed *criteria-pass* rates can be higher because v1's criteria reward fall-back handback discipline (`Assumed:` section enumerates the silent decision) — but a passing criterion from fall-back is not the same as the trigger firing. Today's verification of fixture 06 (ambiguity): 0/3 trigger fires, 3/3 fall-back-handback passes, scored as 3/4 per run. The trigger is functionally broken; the fall-back is masking it in the composite.

**Cost:** every iteration on Class B triggers was wasted motion. Strengthening skill text didn't move the ceiling. The bimodal variance (0/3 today, 75-100/3 yesterday) means no statistical signal at affordable n.

**v2 change:** drop skill-text-only triggers from the enforcement layer entirely. They become *advisory notes in the handback template* — the `Assumed:` section is required to enumerate every load-bearing assumption the agent made without asking, which covers the same ground (and is actually empirically reliable: 100% pass on the canonical baseline). The trigger taxonomy becomes:

  - **Yellow-A** (tool-layer detectable): keep, with hook nudge via `additionalContext`.
  - **Yellow-hybrid** (state-tracked, e.g. decision-log): keep, generalize.
  - **Yellow-B → Assumed:** brief-content-only conditions become items the agent must enumerate in handback, not interruption points.

Net effect: the methodology stops promising what it can't deliver. The published baseline becomes structurally honest.

### 2. Skill text + hook config drift apart

**v1 reality:** `skills/autopilot/SKILL.md` describes triggers; `hooks/guard.mjs` implements detection. They evolved separately. Today's audit found 4 doc-drift points across 5 files from a single PR (PR-8) — the eval scorer changed, downstream docs didn't notice.

**v2 change:** single source of truth at `plugins/autopilot-v2/triggers/*.json`. Each trigger declares:

```json
{
  "id": "irreversibility",
  "class": "A",
  "detection": {
    "type": "bash_pattern",
    "patterns": ["git push", "rm -rf", "npm publish"]
  },
  "checkpoint_template": "checkpoint-format/irreversible.md",
  "advisory_text": "About to <verb> <object> — irreversible.",
  "fixture_id": "05-irreversibility"
}
```

`guard.mjs` consumes the JSON for detection. `skills/autopilot/SKILL.md` is *generated* from the same JSON (build step in the marketplace bundle). The two cannot drift because they're projections of one source.

### 3. Eval criteria written by skill author = circular self-confirmation

**v1 reality:** I wrote the skill text AND the `expected_asks` substrings. Fixture 04 capped at 67 mean. Independent reviewer expanded the substrings → 100 mean. No agent code changed. The criteria-self-bias section in CONTRIBUTING was added after this incident.

**v2 change:** **criteria authorship is a tracked metadata field**. Each fixture declares `criteria_author:` separately from `skill_author:`. CI fails if they're the same name (configurable allowlist for solo-maintainer mode, but the warning fires every run). For substring criteria, a `criteria_review` field records the independent reviewer who expanded the substring set. The criteria-self-bias section becomes structural, not aspirational.

### 4. Self-review is structurally inadequate

**v1 reality:** I personally reviewed `evals/run.py` after PR-8. Found 0 issues. An independent auditor (general-purpose sub-agent) caught the P0 — a deleted function with a live call site — in one pass over the same file. Same pattern recovered fixture 04. Frequency this session: 2 catches the author missed.

**v2 change:** `evals-v2/auditor.py` (the v1 `evals/audit.py` renamed and promoted) is no longer optional or "step 5 in CONTRIBUTING." It runs in CI on every PR. Author cannot self-merge if VERDICT=FAIL. Cost: $0.10–0.30 per audit on Sonnet — orders of magnitude less than the P0s it catches.

### 5. Defaults didn't enforce the methodology

**v1 reality:** ADR-0017 said Class B fixtures need `min_runs:10`. The runner default was `--runs 1`. The README example used `--runs 3`. CONTRIBUTING said `--runs 3`. The published "v2 canonical 94.7" was captured at n=3 — below the documented minimum for 02/03/06. The methodology was correct; the defaults were lying.

**v2 change:** defaults ARE the contract. `--runs` has no default in v2; the runner reads `min_runs` from each fixture and enforces it. The harness refuses to write a `*-canonical-*.json` file unless every fixture met its declared minimum. (v1 commit `49a0e15` ships a weaker version of this: `--runs` defaults to 3, and under-running a fixture records an `UNDERRUN_SKIPPED` entry rather than refusing the whole output file. v2 tightens both.)

### 6. Doc surface > code surface

**v1 reality** (at v0.3.0 + ADR-0017): 17 ADRs + `hitl-framework.md` + `autopilot-plugin.md` + CHANGELOG + CONTRIBUTING + 3 READMEs + MARKETPLACE-SUBMISSION + judge/README + standards/12-agents. Today's audit found doc drift in 4 of those files from a single code change. (This very document and ADR-0018 push the count further; the lesson stands.)

**v2 change:** ruthlessly smaller doc surface. Heuristic from the memory-system principle: *if it's derivable from current code, don't write it down.*

  - **Keep as docs:** `README.md` (1 page: what + install + first task), `design/autopilot-v2.md` (this file), `CHANGELOG.md`, `postmortems/`.
  - **Collapse:** `hitl-framework.md` + `autopilot-plugin.md` → a single `architecture.md` derived from code structure where possible.
  - **Most v1 ADRs become code comments.** Only decisions whose REASON would otherwise be lost remain as ADRs. Predicted v2 ADR count: 5–6, not 17.
  - **Auto-generated where possible:** the trigger list in `architecture.md` is generated from `triggers/*.json`. Diff stays small; drift becomes impossible.

### 7. The eval is not the product

**v1 reality:** the canonical baseline runs `claude --print`, which breaks `AskUserQuestion` per [ADR-0014](../adr/0014-askuserquestion-print-mode-limitation.md). The plugin's main mechanism is degraded in the only mode the eval can run. We're scoring a proxy.

**v2 change:** two-track evaluation.

  - **Mechanism track** (cheap, deterministic, runs on every PR): tests `guard.mjs` patterns directly + replays cached transcripts through the scorer. No `claude` invocations. Cost ~$0. Catches: hook regressions, scorer regressions, doc-drift, trigger-registry consistency.
  - **Behavior track** (expensive, probabilistic, runs weekly or on-demand): full `claude -p` baseline against fixtures. Cost ~$10 at correct n. Catches: model-behavior shifts, real-world plugin effects.

CI gates on mechanism-track for PRs. Behavior track produces dashboard signal, not merge gates.

### 8. Judge calibration is too expensive to bootstrap

**v1 reality:** PR-7 has sat blocked the entire session because nobody has 30–45 min to label 20 transcripts. The `judge_binary` infrastructure exists, no fixture uses it.

**v2 change:** if a criterion can't be evaluated without an LLM judge, ask whether it should exist at all. The handback discipline that PR-7 was meant to score subjectively is already adequately covered by binary `handback_section` + `require_nonempty_after_marker`. Judge use stays a future option, not a structural dependency.

### 9. Cost discipline lived in operator habit

**v1 reality:** `--max-budget-usd` is per-task. There's no session-wide cap. A typo (`--filter 0` matching all 10 fixtures) was a 10× cost surprise. Total session: ~$65, comfortably within budget but only because I was watching.

**v2 change:** `--budget-usd` is a session-wide cap on the harness driver, defaulting to $5. Refuses to start a new fixture if remaining budget < estimated cost for that fixture. The `--filter` footgun is already fixed in v1 (commit `49a0e15`); ships in v2 from day one.

---

## v2 target layout

```
plugins/autopilot-v2/
├── README.md                       # 1 page
├── .claude-plugin/plugin.json      # 1.0.0
├── triggers/                       # SINGLE SOURCE OF TRUTH
│   ├── 01-irreversibility.json
│   ├── 02-budget.json
│   ├── 03-decision-log.json        # state-tracked pattern
│   └── ...
├── hooks/
│   └── guard.mjs                   # reads triggers/*.json
├── skills/
│   ├── autopilot/SKILL.md          # GENERATED from triggers/
│   ├── handback/SKILL.md           # unchanged from v1
│   └── checkpoint-format/SKILL.md  # unchanged from v1
├── agents/
│   ├── verifier.md                 # unchanged
│   └── reviewer.md                 # NEW: built-in audit role
├── commands/
│   ├── autopilot.md                # ONE task command, not 6
│   ├── autopilot-review.md         # session-utility, kept from v1
│   ├── budget.md                   # session-utility, kept from v1
│   └── checkpoint.md               # session-utility, kept from v1
└── test/
    └── triggers-roundtrip.sh       # JSON → skill text → hook regex consistency

evals-v2/
├── design.md                       # 2 pages
├── runner.py                       # cleaner inheritance of v1's run.py
├── auditor.py                      # promoted to first-class CI gate
├── fixtures/
│   └── *.yaml                      # v2 schema only; criteria_author tracked
├── mechanism-track/                # cheap, runs every PR
│   ├── hook-patterns.sh
│   └── transcript-replay.py
└── behavior-track/                 # expensive, weekly
    └── baseline.py

docs/
├── README.md
├── design/autopilot-v2.md          # this file
├── architecture.md                 # generated where possible
├── adr/                            # ~5-6 ADRs, not 17
└── postmortems/                    # actively reviewed every release
```

## What we drop

- **`commands/autopilot-{bugfix,refactor,feature,deps,tests,chore}.md`** — six task-type commands that mostly differ in lengthy preambles. Empirically, the per-type guidance lives better as conditional blocks in a single `commands/autopilot.md` keyed off the brief's first paragraph. [ADR-0010](../adr/0010-task-type-specific-commands.md) gets superseded. The remaining session-utility commands (`autopilot-review.md`, `budget.md`, `checkpoint.md`) are kept in v2 — they're orthogonal to task type and proved useful in real sessions.
- **The Sonnet "judge_completeness" plumbing** — replaced by binary structural criteria + the auditor for cross-cutting concerns. PR-7 work product becomes optional infrastructure, not on the critical path.
## What we keep but reframe

- **`autopilot-logs/<session>.jsonl` PostToolUse audit trail** — kept in v2, but reframed: it's a debugging surface, not a methodology surface. Real failure review happens in `postmortems/`.

## Migration path (sketch — not commitment)

Three plausible paths, in order of cost:

1. **Backport-by-backport.** Cherry-pick each v2 change into v1 incrementally. Lowest risk, slowest, leaves you with v1's architectural debt forever. Done piece-by-piece during normal iteration.
2. **Parallel v2 plugin.** Build `plugins/autopilot-v2/` alongside; users opt in by installing v2. Cut over the canonical baseline once v2 reaches parity. Medium risk, medium cost. ~2 weeks.
3. **In-place rewrite.** Replace `plugins/autopilot/` content. Hard cutover. Highest disruption, fastest closure. Don't recommend without a freeze on real-user-facing changes for 2–3 weeks.

No decision required from this doc. The decision is "we now know what v2 should look like; choose a path when one becomes urgent."

## Acceptance for v2 (when it ships)

A v2 baseline is acceptable iff:
- Every yellow trigger has class A or A-hybrid detection (no skill-text-only triggers).
- `triggers/*.json` round-trips: build step generates skill text identical to the committed version; hook regex parses without error.
- `evals-v2/auditor.py --since main` returns PASS on the diff.
- Every fixture meets its declared `min_runs`; no `UNDERRUN_SKIPPED` in the canonical results file.
- `criteria_author` ≠ `skill_author` for every fixture (or appears on the solo-maintainer allowlist with timestamp).
- Aggregate per-criterion pass-rate ≥ v1's published 94.7 at equal-or-stricter n.

If any of those fail, the rebuild has gone backward. Don't ship.

---

## What this document is NOT

- A commitment to build v2.
- A criticism of v1. v1 worked. It shipped value. It exposed exactly the lessons captured here. That is what v1 was for.
- The full migration plan. That's a future PR if/when the cutover decision happens.

It IS a written form of what we learned, structured so a future contributor (or future-Edison after months away) can build the right thing without re-deriving the lessons.
