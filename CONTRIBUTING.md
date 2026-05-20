# Contributing

This repo holds the web-engineering playbook + the `autopilot` Claude Code plugin + the eval harness that keeps the plugin honest. The plugin is the most active surface; the playbook standards rarely change.

## Before you start

Read in this order:
1. [`docs/hitl-framework.md`](./docs/hitl-framework.md) — the methodology.
2. [`docs/autopilot-plugin.md`](./docs/autopilot-plugin.md) — what the plugin does.
3. [`docs/adr/`](./docs/adr/) — why it does it that way (18 decisions, append-only).
4. [`docs/design/autopilot-v2.md`](./docs/design/autopilot-v2.md) — what v1 taught us; what v2 would be if we rebuilt today. v1 is production; v2 is a design, not a commitment.
5. [`evals/README.md`](./evals/README.md) — how we measure changes.

If you're about to file an issue or PR that contradicts an ADR, read that ADR first; the contradiction may already be addressed.

## Plugin changes: the eval-driven workflow

Every change to `plugins/autopilot/skills/`, `commands/`, `agents/`, or `hooks/` must be measured against the canonical Sonnet baseline. If you can't measure it, you can't ship it. Per ADR-0017, scoring is per-criterion binary with paired-bootstrap CI gating; the older 5-point composite rule is gone.

```bash
# 1. Establish a baseline against current code (or use the v2 10-task
#    canonical in evals/README.md if it's still fresh — currently 94.7
#    overall pass-rate at commit 0cf06dc).
python3 evals/run.py --version baseline --runs 5 --model sonnet --max-budget-usd 0.35

# 2. Make your change. Keep diffs small — per-criterion attribution is
#    cleanest on single-purpose PRs.

# 3. Re-measure
python3 evals/run.py --version after-change --runs 5 --model sonnet --max-budget-usd 0.35

# 4. Diff
python3 evals/compare-runs.py --latest
# Exit code 1 = at least one criterion's Δp̂ CI excludes zero AND
#                |Δp̂| ≥ 0.15 (effect-size floor). Each flagged
#                criterion names the single target_artifact to open.

# 5. Required: independent review (catches what self-review misses).
#    Spawns a fresh Claude over the staged diff with an adversarial
#    audit prompt. Caught a P0 + two P2s on its own first dogfood run.
python3 evals/audit.py                  # vs HEAD (uncommitted work)
python3 evals/audit.py --since main     # vs base branch (committed work)
# Exit code 1 = auditor returned VERDICT: FAIL — at least one P0/P1.
#                Cost ~$0.10-0.30 per audit on Sonnet.
```

For changes that affect only one trigger, use `--filter <NN>` to re-run just the relevant fixture and save cost (note: `--filter` substring-matches, so `--filter 0` matches all 10 fixtures since every filename contains `0`; use a 2-digit prefix):

```bash
python3 evals/run.py --version after-change --runs 5 --model sonnet --filter 05
```

## Adding a new yellow-tier trigger

Per [ADR-0016](./docs/adr/0016-mechanism-vs-skill-text-triggers.md), classify the trigger first:

- **Class A — detectable at the tool layer** (specific Bash command, file path pattern, etc.). Add a hook nudge in `plugins/autopilot/hooks/guard.mjs` that injects `additionalContext` via stdout JSON. Class A triggers reliably reach ≥90 mean composite score.
- **Class B — depends on understanding the brief or codebase**. Add the rule to `plugins/autopilot/skills/autopilot/SKILL.md` and accept the bimodal ceiling (~30-57 mean). Document the limit in `docs/autopilot-plugin.md` Known Limitations.

Add a fixture for it in `evals/tasks/`. Authoritative schema is v2 `criteria: [...]` per [ADR-0017](./docs/adr/0017-rigorous-criteria-methodology.md) — see [`evals/README.md`](./evals/README.md#adding-a-task) for the full field list. Older fixtures retain v1 keys (`expected_asks`, `expected_subagents`, etc.) as documentation only; the scorer ignores them.

Supporting fixture fields (orthogonal to criteria):
- `setup:` and/or `setup_commands:` if the brief needs context (files, git init, etc.)
- `allowed_tools:` if the brief needs commands `--print` mode normally blocks
- `env:` if the brief needs custom env vars (e.g. low budget thresholds)
- `tests_class: A | A-hybrid | B` per ADR-0016 — affects `min_runs` default
- `target_artifacts:` list of files this fixture's failure points at — the 1:1 failure→remediation mapping

## Adding a new hook pattern

Edit `plugins/autopilot/hooks/guard.mjs`:
- Destructive (block): add to `BASH_PATTERNS`
- Soft nudge (warn but don't block): add to `IRREVERSIBLE_PATTERNS` or create a new pattern array per ADR-0016

**Always** add a regression test to `plugins/autopilot/test/run-hook-tests.sh` for any new pattern (both a `BLOCK` case and an `ALLOW` near-miss). The 88-case suite must stay green.

## Hook stderr is invisible

Per [ADR-0015](./docs/adr/0015-pretool-hook-stderr-invisibility.md): PreToolUse hook stderr at exit 0 does NOT reach the agent. If you want the agent to see a message, output JSON to stdout with `hookSpecificOutput.additionalContext`. Stderr is for humans tailing logs.

## ADRs

Significant decisions get ADRs in `docs/adr/`. Numbered sequentially, append-only. To change a decision, write a new ADR with `Status: Supersedes ADR-NNNN`.

Templates: see [`standards/11-adrs.md`](./standards/11-adrs.md).

## Cost discipline

Eval runs cost real Anthropic dollars (~$0.05–$0.30 per task on Sonnet, depending on tool count). Default `--runs 3` for stability + signal. Use `--max-budget-usd` per-task cap. Haiku is cheaper but per [ADR-0014](./docs/adr/0014-askuserquestion-print-mode-limitation.md) and the `Known Limitations` in `docs/autopilot-plugin.md`, Haiku is not a meaningful HITL-trigger test.

A 3-pass canonical baseline against all current fixtures runs ~$3.50 and takes ~20 minutes in background.

## Criteria-self-bias (known weakness)

The author of the agent's instructions (skills, hooks, commands) and the author of the eval's match patterns (substrings, judge rubrics) should NOT be the same person. When they are, the criteria favor the wording the agent's instructions happen to use, and the eval becomes a circular self-confirmation. The session that produced this codebase had exactly that problem.

Mitigation when extending the eval:

- **Before adding a substring to an `ask_present` criterion, ask an LLM that hasn't seen the skill text** what substrings would catch a thoughtful question on the same brief. Diff against your list. Add the ones you missed.
- **Each new substring should be defensible by an independent reviewer** — imagine a critic saying "you only added that word because the agent says it." If you can't rebut, don't add it.
- **For subjective rubrics**, get ≥20 human labels from someone who didn't write the rubric, then run `evals/judge/calibrate.py`. AC2 < 0.7 means the rubric is wrong, not the agent.

The 2026-05-19 audit ([`evals/judge/README.md`](./evals/judge/README.md) workflow) recovered measurable recall via independent perspective on fixture 04 (mean rose 67 → 100 after the auditor's substrings landed). Same approach applies to every new criterion.

## Don't

- Strengthen skill text for Class B triggers expecting improvement — past evidence shows it doesn't move scores beyond ~57. Add to documentation instead.
- Use stderr from hooks expecting the agent to read it (ADR-0015).
- Add new top-level deps to the plugin — it must stay Node-only with stdlib.
- Submit without re-running `bash plugins/autopilot/test/run-hook-tests.sh`.
- Submit without re-running at least the changed fixtures via `evals/run.py --filter ...`.
