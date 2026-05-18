# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/) — see "Versioning policy" below.

## [0.1.0] - 2026-05-18

Initial cut. Implements components 1–4, 6, partial 5/7 of the HITL framework (`../../docs/hitl-framework.md`).

### Added — Skills

- `autopilot` — three-tier action classification (green/yellow/red), six categorical yellow-tier triggers, context-management heuristics, common failure modes.
- `checkpoint-format` — required shape for every `AskUserQuestion` call: status preamble, concrete question, 2–4 options with consequences, recommended first.
- `handback` — end-of-task report format. `Done`/`Blocked` headline + Changed / Skipped / Assumed / Verify-before-merging / Open-questions / Audit-trail / Budget.
- `decision-log` — append a markdown entry per silent yellow-tier-adjacent decision in real time. Complements handback (handback is reconstruction; decision log is contemporaneous).

### Added — Commands

- `/autopilot <task>` — generic per-task entry.
- `/autopilot-bugfix` — reproduce-first discipline; blocks test changes alongside production fixes.
- `/autopilot-refactor` — blocks behavior-change-shaped diffs; no test edits alongside refactor.
- `/autopilot-feature` — pauses on architectural forks, new deps, new routes, new schema.
- `/autopilot-deps` — pauses on major bumps, large lockfile churn, new top-level deps.
- `/autopilot-tests` — blocks edits outside test directories.
- `/autopilot-chore` — blocks semantic edits when brief is format-only.
- `/checkpoint` — force an immediate status + structured question mid-task.
- `/autopilot-review [session-id]` — display the decision log + tool-call summary for a session.
- `/budget` — show current session's tool-call count vs. yellow/red thresholds.

### Added — Subagents

- `verifier` — read-only second opinion with a 10-point check (hallucinated APIs, framework drift, fabricated comments, claimed-but-unrun verification, scope creep, security anti-patterns, race conditions, ADR-aware drift).
- `scout` — research with focused synthesis output, capped at ~300 words.

### Added — Hooks

- `pretool-bash` — Node-based regex guard against destructive bash patterns. 85-case regression suite. PATH pinned, `LD_PRELOAD`/`BASH_ENV` unset.
- `pretool-write` — blocks Writes outside cwd and `/tmp`. Paths canonicalized via `realpath` to defeat `..` traversal.
- `pretool-budget` — checks running tool-call count, warns at yellow threshold (50) and blocks at red (150). Both overridable via `AUTOPILOT_BUDGET_YELLOW` / `AUTOPILOT_BUDGET_RED`.
- `posttool-log` — appends redacted JSONL entry per tool call to `.claude/autopilot-logs/<session>.jsonl`. Increments budget counter.
- `session-start` — env-var-gated (`CLAUDE_AUTOPILOT=1`) — injects autopilot mode for the whole session.

### Added — Entry modes

- Per-task slash command (default; safer).
- Always-on via `CLAUDE_AUTOPILOT=1` environment variable.

### Behavior — what shipped

- **Status, not narration.** Default to proceeding; surface only at categorical triggers.
- **Ask once, well.** Structured `AskUserQuestion` exclusively; no prose questions.
- **Prefer subagents over questions.** `@agent-scout` / `@agent-verifier` answer factual/correctness questions without asking the human.
- **Audit trail by default.** Every tool call logged with secret redaction; agent appends prose entries at silent decisions.
- **Budget governance.** Soft yellow at 50 tool calls, hard red at 150; overridable.

### Security note

Hooks are NOT a security boundary against an adversarial or compromised model — they stop accidents and well-behaved agents. Real enforcement requires OS-level sandboxing. See [ADR-0006](../../docs/adr/0006-hooks-as-sole-enforcement-layer.md).

---

## Versioning policy

The plugin's "API" is the user's expectation contract: what the agent does autonomously, what it pauses on, what it blocks.

- **MAJOR (x.0.0)** — changes that can surprise an existing user mid-session: removing a pause point (agent now proceeds where it used to ask), removing/renaming a command or skill, changing a hook from advisory to blocking, restructuring `AskUserQuestion` checkpoint shape consumers may script against.
- **MINOR (0.x.0)** — *adds* a pause/checkpoint where there wasn't one (new yellow-tier trigger), new agent, new command, new skill, new optional hook. Safe-by-default — erring toward "ask more" is additive caution.
- **PATCH (0.0.x)** — tightening a destructive-op regex so `git push -f` is now caught: this is a **fix** (the rule's stated intent was always to catch force-push; the regex was buggy). Doc fixes, prompt wording, perf.

Edge case: a "fix" that meaningfully expands what gets blocked (e.g., regex now catches `rm -rf $VAR`) is treated as **MINOR** — same intent, materially broader surface.

### Behavior entries

Every entry that shifts when the agent pauses/proceeds gets a `**Behavior:**` prefix in the changelog and a one-line *before → after* diff. Pre-release tags (`-beta.N`, `-rc.N`) for any MINOR/MAJOR changing pause behavior, shipped to opt-in users first.

### Cadence

Manual, tag-driven (`autopilot-vX.Y.Z`). Not continuous-on-merge — autonomy guardrails are too consequential for accidental ships.

### Compatibility

`plugin.json` declares an `engines.claude-code` range. The plugin loader does not enforce this today; the README notes the minimum tested version. Re-test against the latest Claude Code on every MINOR.
