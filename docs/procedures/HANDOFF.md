# Handoff — procedural workflow buildout

**Status:** Plan approved, execution not yet started. Directory `docs/procedures/` exists but contains only this handoff. Whoever picks this up should be able to start writing the first doc within 5 minutes of reading this.

**Date:** 2026-05-20.
**Plan file:** `/home/edo/.claude/plans/do-it-again-by-enchanted-adleman.md` (full version with rationale).

---

## What this work is

Build a comprehensive, written procedure for AI-agent-driven development at senior-engineer quality. The 5-phase loop:

```
plan → build → surface issues → fix → audit → repeat
```

The methodology already exists in this repo, scattered across ~18 ADRs, 3 design docs, the autopilot-v2 plugin's agents + skills, the evals harness's auditor + scorer, and conventions held only in the maintainer's head. The job is **codification** — pull the threads into a coherent set of phase-by-phase docs a contributor could read cold.

User's exact phrasing: *"comprehensively and to the degree of 20 year long developers."*

## Why now

Today's session (2026-05-20) finished the v3 hardening pass that empirically validated the methodology:

- 5 parallel worker agents in isolated worktrees, all 5 landed PRs (#1–#5, all merged to main)
- Auditor caught real P0s the author missed (`_classify_ask` deletion, namespace mismatch, compare-runs path bug, budget-tick lifecycle)
- Final-gate canonical re-baseline: **82.1% → 87.4%** (+5pts), $5.52
- Unit 1's budget-tick wiring fix contributed +4 of those 5 points (0/5 → 4/5 → 9/10 ask rate)

The procedure DOC writes down what those 5 worker PRs implicitly proved.

## Decisions already made (via AskUserQuestion)

1. **Form factor:** multiple phase-specific docs in `docs/procedures/`, NOT a single standards doc, NOT a loadable skill.
2. **Scope:** generalize beyond autopilot. Each doc has an "Adopting in your project" section. Autopilot is the worked example, not the API.
3. **Execution strategy:** sequential authoring (single voice), NOT `/batch` parallel writers. Cross-references stay live; one cohesive voice.
4. **Order:** `00-principles.md` first (informs the others) → `README.md` (index) → `01-plan.md` through `06-repeat.md` in loop order → ADR-0019 → CONTRIBUTING.md pointer.

## The 8 docs to write

Each doc follows this structure (~3-4 pages each):

1. **What this phase IS** — one paragraph.
2. **Principles** — 3-5 bullets, stated generically.
3. **The procedure** — numbered steps; what artifacts to use; what acceptance gates apply.
4. **Acceptance gates** — when is this phase done? What proves it?
5. **Common failure modes** — what goes wrong; how to recognize each; how to recover.
6. **Worked example from the autopilot work** — concrete walk-through.
7. **Adopting in your project** — generalization; what's Claude-Code-specific vs project-agnostic.

| File | One-line description | Inventory gap it closes |
|---|---|---|
| `README.md` | Index, 5-phase diagram, 20-year-dev quality bar, when NOT to use | — |
| `00-principles.md` | Cross-cutting principles + evidence + how-to-apply | #2 (cost discipline), #4 (evidence-backed scope) |
| `01-plan.md` | Plan-mode → AskUserQuestion → `/batch` decomposition | #1 (plan-mode flow), #4 (evidence framework) |
| `02-build.md` | Worktree isolation, single-source-of-truth, subagent delegation, worker prompt template | #5 (poll-vs-spawn) |
| `03-surface-issues.md` | Per-criterion binary scoring, reviewer agent, P0/P1/P2, criteria-self-bias mitigation | #6 (criteria-author CI), #7 (architectural invariants) |
| `04-fix.md` | Eval-driven workflow, target_artifact 1:1 mapping, diagnostic loop, postmortem-to-test | #3 (diagnostic loop), #8 (postmortem loop closure first half) |
| `05-audit.md` | Self-review is structurally inadequate; reviewer vs auditor; verifier; mechanism vs behavior track | #7 (invariants explained) |
| `06-repeat.md` | Final-gate re-baseline, Wilson CI, paired bootstrap, effect-size floor, canonical acceptance | #8 (postmortem loop closure second half) |

## The 8 inventory gaps (full text)

These are patterns USED in the current workflow but not documented as procedure. Each gap maps to a target doc above:

1. **Plan-mode + AskUserQuestion scope discipline** — used in ADR-0018 framing but no step-by-step doc.
2. **Cost discipline at session scope** — `--max-budget-usd` documented per-task; session-wide and `--filter` footgun mitigation aren't.
3. **Diagnostic loop mechanics** — ADR-0017 names it; no explicit walkthrough.
4. **Evidence-backed scope discipline** — ADR-0018 frames it; no enumeration of what qualifies as evidence vs speculation.
5. **Poll vs spawn discipline** — Monitor tool docs discuss it; not in playbook procedure.
6. **`criteria_author ≠ skill_author` CI enforcement** — mentioned in CONTRIBUTING + v2 fixture YAMLs; no CI rule written.
7. **`triggers-roundtrip` + `scorer-sync` invariants** — exist as shell scripts; what they enforce / how to read failures isn't documented.
8. **Postmortem → follow-up → capability-add loop** — `postmortems/README.md` says follow-ups must ship; no procedure for deciding what KIND of follow-up (new trigger? new regex? new subagent? new ADR?).

## Load-bearing artifacts to cite (don't modify; reference)

| Path | What the docs cite it for |
|---|---|
| `docs/adr/0017-rigorous-criteria-methodology.md` | Per-criterion methodology, north-star principle |
| `docs/adr/0018-rebuild-from-lessons-learned.md` | Evidence-backed scope philosophy |
| `docs/adr/0014-askuserquestion-print-mode-limitation.md` | Why eval ≠ product; behavior-track motivation |
| `docs/adr/0016-mechanism-vs-skill-text-triggers.md` | Class A/A-hybrid/B taxonomy; mechanism > instruction |
| `docs/adr/0011-eval-harness-design.md` | Statistical machinery (Wilson, bootstrap, effect-size floor) |
| `docs/design/autopilot-v2.md` | Worked example of evidence-anchored design doc |
| `evals-v2/auditor.py` | Reviewer-as-CLI implementation |
| `plugins/autopilot-v2/agents/reviewer.md` | Reviewer-as-agent prompt |
| `plugins/autopilot-v2/agents/verifier.md` | Verifier (10-point check) subagent |
| `plugins/autopilot-v2/triggers/$schema.json` | Single-source-of-truth registry pattern |
| `plugins/autopilot-v2/tools/gen-skill.mjs` | Generated-from-config artifact pattern |
| `evals-v2/test/scorer-sync.sh` | Architectural-invariant-as-test pattern |
| `evals-v2/run.py` | Eval runner with `min_runs` enforcement |
| `evals-v3/mechanism/replay.py` | Mechanism-track CI implementation |
| `plugins/autopilot-v2/test/run-hook-tests.sh` | 90-case regression suite as procedure example |
| `CONTRIBUTING.md` | Existing workflow doc — gets a pointer added at the end |

## First step for whoever picks this up

1. Read the approved plan in full: `/home/edo/.claude/plans/do-it-again-by-enchanted-adleman.md`.
2. Update `evals-v2/README.md` with the post-v3-hardening canonical baseline numbers (87.4% aggregate, $5.52, +5pts vs pre-hardening). This is one short commit. Currently the README still shows 82.1% from before the hardening pass.
3. Begin writing `docs/procedures/00-principles.md` per the order in the plan. Use the principle list in the plan as the section structure; for each principle, pull evidence directly from session commits (look at `git log` since `b95ff9b` for the v3 work; before that for v2 + ADR-0017).
4. Run `python3 evals-v2/auditor.py` after each phase doc commits. Expect to iterate 2-3 rounds per doc based on session patterns.

## Open questions (judgment calls for whoever picks this up)

- **Should ADR-0019 be written first or last?** First gives the procedure a numbered home in the ADR index; last lets the ADR cite finalized doc paths. Recommend last; it's a 1-page summary of decisions already documented in the procedure docs.
- **How verbose should "Adopting in your project" sections be?** The user wants generalization but didn't specify how detailed. Recommend: 1 paragraph per Claude-Code-specific dependency (hooks, AskUserQuestion, Skill tool, subagents, slash commands), noting what an equivalent would look like in OpenAI Assistants / LangGraph / Aider, but NOT writing the equivalent. The cross-platform port is itself a future work-item, not this session's scope.
- **Worked examples — fresh from this session, or capture from older sessions too?** Recommend mostly this session (v3 hardening produced rich, recent, well-documented examples). One older example (the criteria-self-bias fixture-04 recovery from v1) is worth including in `03-surface-issues.md`.
- **Should the docs include explicit "what 20-year dev quality means" criteria?** Yes — short section in `README.md`. Suggested anchors: doesn't rush; measures twice; has explicit rollback; treats independent review as load-bearing; uses statistics not vibes; captures failures as tests; pushes back on scope when evidence is thin.

## Verification recipe (run after all 8 docs land)

```bash
# Architectural invariants — must remain green (docs-only work).
bash plugins/autopilot-v2/test/triggers-roundtrip.sh
bash evals-v2/test/scorer-sync.sh
bash plugins/autopilot-v2/test/run-hook-tests.sh

# Independent audit on the full procedure-docs diff.
python3 evals-v2/auditor.py
# Must return VERDICT PASS. The auditor is an embodiment of the audit
# phase; if it can't pass on these docs, the docs are wrong.

# Cross-reference check — every referenced file should exist.
grep -rEo '(plugins|evals|evals-v3|docs|standards)/[A-Za-z0-9_./-]+' docs/procedures/ \
  | sort -u \
  | while read p; do [ -e "$p" ] || echo "STALE: $p"; done

# Mechanism-track replay — ensures shared scorer/loader behavior unchanged.
python3 evals-v3/mechanism/replay.py
```

## Cost framing

| Item | Estimated cost |
|---|---|
| Coordinator tokens for sequential authoring (8 docs × ~1500 LoC total) | $3-6 |
| Auditor invocations (3-4 rounds expected per session pattern) | $1-2 |
| Architectural invariants + replay (no `claude` calls) | $0 |
| **Total estimated session-add** | **$4-8** |

No re-baseline needed — pure documentation. The procedure being written CODIFIES the behavior validated by today's $5.52 canonical re-baseline.

## What this work explicitly does NOT do

- Build new tooling or scripts. Procedure docs reference existing artifacts; if a gap requires new tooling, it gets a v4 work-item, not a procedure addition.
- Generalize the procedure to non-Claude-Code platforms in detail. "Adopting in your project" sections note dependencies but don't write the LangGraph/OpenAI equivalents.
- Re-derive principles from first principles. Cites this codebase's evidence as authoritative.
- Spawn worker agents (Option A in the plan was rejected for cohesion).

## Session context at handoff

- Branch: `main`
- Last commit: `e407bcb` v3 unit 2: JSONSchema validation for triggers registry (#5)
- All 5 v3 hardening PRs merged
- v3 post-hardening canonical baseline run: `evals-v2/results/v2-canonical-post-v3-hardening-1779299739.json` (gitignored — don't commit; reference its NUMBERS not the file)
- This handoff is the only file uncommitted in `docs/procedures/`
- Existing worktrees `.claude/worktrees/agent-*` from today's parallel batch are still on disk; safe to delete since their PRs all merged (or keep for forensics)

## Picking up later

Start a new Claude Code session, `cd` here, and prompt:

> Continue the procedural workflow buildout. The handoff doc is at `docs/procedures/HANDOFF.md`. Read it and the linked plan, then begin with the first step from the handoff (update evals-v2/README.md, then write docs/procedures/00-principles.md per the plan's order). Run the auditor after each commit.

That prompt is enough; the handoff + plan have everything else needed.
