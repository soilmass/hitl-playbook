# Autopilot Plugin

**Source:** [`../plugins/autopilot/`](../plugins/autopilot/)
**Implements:** [`hitl-framework.md`](./hitl-framework.md)
**Status:** v0.1 (2026-05-18)
**Changelog:** [`../plugins/autopilot/CHANGELOG.md`](../plugins/autopilot/CHANGELOG.md)

Canonical reference for what the autopilot plugin contains, how each piece works, and why.

---

## Purpose

A Claude Code plugin for high-autonomy work with surgical human-in-the-loop gates. Default behavior is to proceed; asking is the exception. Destructive operations are hard-stopped by hooks, not by skill instructions the model could ignore.

---

## File-by-file

### Plugin metadata

**`.claude-plugin/plugin.json`** — name, version, description, author, license (MIT), keywords, `engines.claude-code` compatibility range.

### Skills

**`skills/autopilot/SKILL.md`** — operating philosophy: three tiers (green / yellow / red), six categorical yellow-tier triggers, context-management heuristics, operating principles, common failure modes. Loaded by `/autopilot` command and the `CLAUDE_AUTOPILOT=1` SessionStart hook. See [ADR-0002](./adr/0002-three-tier-action-classification.md), [ADR-0004](./adr/0004-categorical-ask-triggers.md), [ADR-0007](./adr/0007-prefer-subagents-over-human-questions.md), [ADR-0008](./adr/0008-context-management-strategy.md).

**`skills/checkpoint-format/SKILL.md`** — required shape for every yellow-tier `AskUserQuestion` call: status preamble, concrete question, 2–4 options with consequence descriptions, recommended first. Templates for architectural choice, scope confirmation, budget tick, ambiguity resolution, pre-irreversible action. See [ADR-0003](./adr/0003-askuserquestion-as-exclusive-hitl-surface.md).

**`skills/handback/SKILL.md`** — end-of-task report format. `Done`/`Blocked` headline + Changed / Skipped / Assumed / Verify-before-merging / Open-questions / Audit-trail / Budget. The **Assumed** section is the load-bearing audit trail for silent decisions.

**`skills/decision-log/SKILL.md`** — append a markdown entry per silent yellow-tier-adjacent decision in real time. Complements handback: handback is end-of-task reconstruction; decision log is contemporaneous. See [ADR-0009](./adr/0009-audit-trail-mechanism.md).

### Commands

**`commands/autopilot.md`** — generic per-task entry: `/autopilot <task description>`. See [ADR-0005](./adr/0005-both-entry-modes-for-autopilot.md).

**`commands/autopilot-bugfix.md`** — bugfix-specific: pause before non-test edit if bug not reproduced; block test edits in same diff as production fix. See [ADR-0010](./adr/0010-task-type-specific-commands.md).

**`commands/autopilot-refactor.md`** — refactor-specific: pause on public API changes; block test edits alongside refactor.

**`commands/autopilot-feature.md`** — feature-specific: pause after plan, on architectural forks, before new top-level deps / routes / env vars / schema.

**`commands/autopilot-deps.md`** — dependency-specific: pause on major bumps, large lockfile churn, new top-level deps.

**`commands/autopilot-tests.md`** — test-specific: block edits outside test directories; surface latent bugs without silently fixing.

**`commands/autopilot-chore.md`** — chore-specific: block semantic edits when brief is format-only; more aggressive budget ticks.

**`commands/checkpoint.md`** — force an immediate checkpoint mid-task: `/checkpoint`.

**`commands/autopilot-review.md`** — `/autopilot-review [session-id]` — displays the decision log + tool-call summary for the latest (or specified) session.

**`commands/budget.md`** — `/budget` — prints current session's tool-call count vs. yellow/red thresholds, breakdown by tool, elapsed time, status. See [ADR-0012](./adr/0012-cost-budget-via-tool-call-counter.md).

### Subagents

**`agents/verifier.md`** — read-only second opinion. Tools: Read, Grep, Glob, Bash. 10-point check covering hallucinated APIs, framework drift, fabricated comments, claimed-but-unrun verification, scope creep, security anti-patterns, race conditions, ADR-aware drift. Used instead of asking the human "is this correct?".

**`agents/scout.md`** — research agent. Tools: Read, Grep, Glob, WebFetch, WebSearch, Bash. Used instead of asking the human "where is X?" / "what does Y do?". Returns synthesis (~300 word cap), not raw search results.

### Hooks

**`hooks/hooks.json`** — registers all hooks. Invokes the Node guard for each mode. See [ADR-0013](./adr/0013-cross-platform-node-helper.md).

**`hooks/guard.mjs`** — single Node helper, five modes:

1. **`pretool-bash`** — regex blocks destructive bash patterns. 13 hardened pattern categories covering alt-deletion tools (`find -delete`, `dd`, `shred`, `truncate`), quoted/path-prefixed `rm`, git alias indirection, force-push short flags, publish commands, SQL via client tools only, eval/source at command position, env hijack. PATH pinned, `LD_PRELOAD`/`BASH_ENV` unset inside guard.
2. **`pretool-write`** — blocks Writes outside `cwd` and `/tmp`. Paths canonicalized via `realpath` to defeat `..` traversal.
3. **`pretool-budget`** — reads tool-call counter, warns to stderr at yellow threshold (50) and exits 2 at red (150). Thresholds via `AUTOPILOT_BUDGET_YELLOW` / `AUTOPILOT_BUDGET_RED` env vars.
4. **`posttool-log`** — appends redacted JSONL entry per tool call to `.claude/autopilot-logs/<session-id>.jsonl`; increments budget counter at `.budget`.
5. **`session-start`** — env-var-gated (`CLAUDE_AUTOPILOT=1`); injects autopilot mode instruction.

### Tests

**`test/run-hook-tests.sh`** — 85-case regression suite. Sources the live guard so the suite can't drift from the implementation. Runs on Linux + macOS in CI via [`../.github/workflows/autopilot-ci.yml`](../.github/workflows/autopilot-ci.yml).

### Top-level

**`README.md`** — install + verify + first task FTUX entry. Points here for the full reference.

**`CHANGELOG.md`** — Keep a Changelog format. Includes the versioning policy: MAJOR = removes a pause; MINOR = adds a pause; PATCH = bug fix. Behavior callouts on every entry that shifts pause behavior.

---

## Known limitations

- **`AskUserQuestion` is non-functional in `claude --print` (non-interactive) mode.** The tool fires but Claude Code returns an immediate `is_error: true` response (no human to answer). The agent then reverts to prose questions, violating the autopilot skill's "no prose questions" rule. Autopilot is fundamentally an **interactive-mode** plugin; CI/batch/eval contexts get degraded behavior. See [ADR-0014](./adr/0014-askuserquestion-print-mode-limitation.md).
- **Haiku ignores categorical yellow-tier triggers.** Verified via the eval harness (`evals/run.py`): on the scope-drift fixture, Haiku scored 15–30 over 6 runs and **never** invoked AskUserQuestion. Sonnet scored 90 on both runs and **always** invoked it. The plugin's design assumes the agent will follow explicit skill instructions; Haiku does not bind tightly enough to those instructions. **Recommended model: Sonnet or stronger.** Haiku is fine for trivial tasks but the HITL guarantees degrade.
- **Hook cannot be a security boundary against an adversarial or compromised model.** Hardened regex + Node guard stop accidents and well-behaved agents; novel indirection paths (shell-via-Python, custom CLIs) require OS-level sandboxing. See [ADR-0006](./adr/0006-hooks-as-sole-enforcement-layer.md).
- **The `decision-log` skill is not reliably invoked.** Even with explicit "invoke the Skill tool with `skill: 'autopilot:decision-log'`" instructions in `autopilot/SKILL.md`, the model frequently doesn't recognize it's making a silent decision and so doesn't reach for the skill. The end-of-task handback's `Assumed:` field remains the load-bearing audit surface.
- **Architectural-fork yellow trigger is rationalizable.** Sonnet can talk itself out of asking by reading the brief as "a clear directive" or claiming the choice is "obvious." Stronger language in the skill helps but doesn't fully prevent. Users wanting bulletproof always-ask behavior should write briefs that leave the choice explicitly open.

---

## What's intentionally NOT in the plugin

- **`settings.json` at plugin root.** Claude Code only honors `agent` and `subagentStatusLine` keys there; permissions are silently ignored. The plugin cannot ship permissions. See [ADR-0006](./adr/0006-hooks-as-sole-enforcement-layer.md).
- **A second enforcement layer.** The hook is the only guard. For defense in depth, install instructions recommend mirroring the destructive-command patterns into the user's own `~/.claude/settings.json`. The hook is NOT a security boundary against adversarial/compromised models.
- **Wall-clock time and token budgeting.** Only tool-call count is tracked in v0.1. See [ADR-0012](./adr/0012-cost-budget-via-tool-call-counter.md).
- **Automated postmortem capture.** Template ships at [`./postmortems/TEMPLATE.md`](./postmortems/TEMPLATE.md); filling it remains a human step.

---

## Installation

```bash
# From any project that wants autopilot:
/plugin install /path/to/hitl-playbook/plugins/autopilot

# Verify
/help    # /autopilot, /checkpoint, /budget, /autopilot-review,
         # and 6 /autopilot-<type> commands should appear

# Optional: enable always-on mode
export CLAUDE_AUTOPILOT=1

# Optional: tune budget thresholds
export AUTOPILOT_BUDGET_YELLOW=80
export AUTOPILOT_BUDGET_RED=200

# Optional: add a defense-in-depth denylist to your own settings.json
# Mirror the destructive patterns from plugins/autopilot/hooks/guard.mjs
```

---

## Verification

```bash
bash plugins/autopilot/test/run-hook-tests.sh
```

85 cases covering destructive patterns, bypass attempts from a focused security review (alternate deletion tools, quoted/path-prefixed `rm`, eval/source/bash-c/python-c indirection, env hijack, SQL via client tools), edge-case safe commands that must not false-block (branch names containing `force`/`fix`/`foo`, prose like `echo 'drop table is bad'`), and Write-path traversal.

Currently 85/85 pass. CI runs the same suite on Linux + macOS matrix.

---

## Version history

- **v0.1.0 (2026-05-18)** — initial cut. See [`CHANGELOG.md`](../plugins/autopilot/CHANGELOG.md) for the full inventory.
