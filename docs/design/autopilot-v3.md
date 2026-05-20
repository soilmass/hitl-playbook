# autopilot v3 — prospective design

**Status:** prospective draft (2026-05-19). Written before v2 has accumulated empirical data. Revise after v2 has 10+ baselines.

**Audience:** future-Edison after v2 has been used in real tasks for ≥2 weeks, and any contributor reading this should treat each section's confidence as the disclaimer says.

---

## Read this first

This document violates a principle stated in ADR-0018: *don't spec v3 before v2 has produced its lessons.* It is here because it was explicitly requested in the same session that produced v2.

**Confidence scale used below:**

- **HIGH (H)**: predicted from v1's measured gaps that v2 explicitly defers (e.g., hook test corpus port). High likelihood the lesson holds.
- **MEDIUM (M)**: predicted from architectural smell in v2 that we can already see (e.g., the reviewer agent is per-task but cross-task patterns may emerge).
- **LOW (L)**: speculation about the Claude Code platform, ecosystem dynamics, or use cases we haven't observed.

**The whole document should be re-evaluated after**:
1. v2 has shipped its canonical baseline (`evals-v2/results/v2-canonical-*.json`).
2. v2's reviewer agent has been used on ≥10 real diffs and its findings have been catalogued.
3. v2 has been used in ≥5 distinct task types beyond the eval suite.

Sections marked **L** in particular should NOT drive implementation work until v2 supplies signal.

---

## Predicted v2 lessons → v3 changes

### v3-1. Trigger registry needs schema versioning (HIGH)

**Predicted v2 lesson**: someone will want to add a new trigger field (e.g., `dry_run_pattern` to detect `--dry-run` variants of irreversible commands). v2's `loadTriggers()` validates required fields (`id`, `class`, `detection.type`) but silently accepts any extra keys, so a typo'd or experimental field can ship and have no effect. Three months later, half the triggers have the field and half don't, and nothing surfaced the divergence.

**v3 change**: `triggers/$schema.json` (JSONSchema). Loader validates every file against it. Unknown fields are rejected, not silently accepted. Schema version bumps require a migration script under `tools/migrations/`.

### v3-2. Single-machine state counters don't survive `claude` session resumption (HIGH)

**Predicted v2 lesson**: `.claude/autopilot-logs/<session>.dlog-writes` lives in the project dir but tied to `CLAUDE_CODE_SESSION_ID`. When a user resumes a session via `claude --continue`, the session ID stays but the working tree may have moved on (rebase, branch switch). The counter then represents writes-since-last-dlog from a now-irrelevant timeline.

**v3 change**: counter state keyed by `(session_id, git_HEAD)` tuple instead of session_id alone. Counters re-initialize when HEAD changes. Old counter files prune on a 24h schedule.

### v3-3. Mechanism track separate from behavior track (HIGH)

**Predicted v2 lesson**: v2 ships `evals-v2/run.py` as a single track that costs $3-15 per run. People won't run it on every PR; drift will accumulate between baselines. v1 had the same problem (the canonical was captured pre-PR-8 and stayed valid only because no plugin code changed in the interim).

**v3 change**: the v2 design doc (`docs/design/autopilot-v2.md` section "The eval is not the product") names this split as a v2 goal but defers implementation. v3 ships it:
- `evals-v3/mechanism/` — cheap, deterministic, **runs in CI on every PR**. Tests: hook regex compilation + match cases (the 88-case corpus from v1, ported), triggers-roundtrip, transcript replay through the scorer over a cached transcript fixture.
- `evals-v3/behavior/` — expensive, real `claude` invocations. **Runs weekly via a scheduled GitHub Action**, not on every PR. Produces a dashboard, not a merge gate.
- The merge gate is mechanism-track only. Behavior track raises an issue if it drifts past CI threshold.

### v3-4. The reviewer agent is per-task; cross-task patterns will emerge (MEDIUM)

**Predicted v2 lesson**: v2's `reviewer.md` runs once per diff. After ~20 invocations, certain finding categories will repeat (e.g., "you forgot to update CHANGELOG", "you added a fixture without `criteria_author`"). Per-invocation cost rises because the reviewer re-derives the same checks.

**v3 change**: `reviewer/checks/*.md` — checkable categories that v3 packages with the agent. Each check is a short prompt with examples of the failure mode and a one-line "what to do if you find it." The reviewer reads applicable checks plus the diff. Two benefits: (a) finding categories that recur become structural rather than re-derived, (b) the catalog is editable as new failure modes are observed.

This is the same pattern as v2's `triggers/*.json` registry, applied to a different surface.

### v3-5. Memory of failures > memory of features (MEDIUM)

**Predicted v2 lesson**: `postmortems/` exists in v1 but is barely populated. v2 doesn't change this. The reviewer agent and the trigger registry both encode "what to do right" — neither encodes "what we learned from doing it wrong."

**v3 change**: `postmortems/` becomes structurally important. Each postmortem is a YAML file with: failure mode, root cause, fix, **test added to prevent recurrence**. Last field is the critical one — every postmortem produces a regression test in `evals-v3/mechanism/`. The reviewer agent reads recent postmortems as context.

This makes the postmortem directory the actual driver of v3's mechanism track over time. The eval suite grows from failures, not from imagination.

### v3-6. Multi-session continuity (MEDIUM)

**Predicted v2 lesson**: real autopilot use spans multiple `claude` sessions on the same task (interrupted by lunch, by a meeting, by switching machines). v2's audit log + decision-log are per-session; the second session can't see the first session's decisions without rereading the markdown manually.

**v3 change**: `autopilot-state/` (per-project, gitignored by default but committable for shared work). Aggregates decision-log entries across sessions for the same git branch + task. A new session reads this on `session-start` and prepends recent decisions to its context.

### v3-7. Plugin-template repo (LOW)

**Predicted v2 lesson** (speculation): the registry-driven architecture is generalizable. Other plugins might want it. v3 could extract the pattern to a `claude-plugin-template/` repo with the registry loader, audit gate, and reviewer agent as a starting kit.

This is real if and only if: (a) at least one other plugin author finds v2's architecture useful, AND (b) extracting it is cheaper than them copying it. Neither is observable today.

### v3-8. Hook events the platform doesn't have yet (LOW)

**Predicted v2 lesson**: Claude Code may introduce hook events v3 should consume — `SubagentStart`, `SubagentEnd`, `ContextCompaction`, etc. v3 changes here depend on what the platform actually ships in 2026.

**Action**: none today. Watch the Claude Code changelog; add to v3 only when the events exist.

---

## What v3 keeps from v2 unchanged

The architectural decisions in v2 that are predicted to outlast it:

- **Triggers as JSON registry** — single source of truth pattern.
- **Generated SKILL.md** — never hand-edit, always regenerate.
- **Class B as `Assumed:` discipline** — brief-content-only conditions don't get enforced triggers; they get enumerated.
- **Hook stays the sole RED enforcement layer.**
- **One task command, not six.**
- **`--runs` required, no default.**
- **Per-criterion bootstrap CI gating.**
- **Reviewer agent at PR boundary.**
- **`AUTOPILOT_GATE:` stderr marker.**

If v2 produces empirical pressure against any of these, that becomes a v3 ADR — but it would be surprising; these are downstream of measurable v1 problems.

---

## What v3 explicitly does NOT spec

Anything that would require v2 to teach us first:

- Specific cost numbers for the mechanism vs behavior split.
- Specific threshold values for the registry schema.
- Specific check categories for the reviewer (depends on what v2 reviewer actually flags repeatedly).
- Whether `autopilot-state/` should be per-project or per-user.
- Whether v3 should be a hard cutover from v2 or another parallel install.

These are decisions where guessing now produces wrong answers. v2 has to run first.

---

## Acceptance for this document

This document is "ready to act on" when:

1. v2 has accumulated ≥10 baseline runs against real plugin changes (not just smoke tests).
2. The reviewer agent has produced ≥30 findings catalogued by category.
3. At least one of the **HIGH**-confidence predictions has been empirically confirmed.
4. The user has revised this document with annotations marking which predictions held vs. didn't.

Until then, treat each section as **a hypothesis to test**, not **a feature to build**.

---

## What this document is NOT

- A roadmap.
- A commitment to ship v3 at any point.
- An admission that v2 is insufficient. v2 may turn out to be the right architecture forever; v3 may never need to ship.

It IS a written form of the questions v2 is asked to answer, so the next iteration can be designed from evidence instead of repeating the same discovery work.
