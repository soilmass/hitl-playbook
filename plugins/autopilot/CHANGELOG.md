# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/) — see "Versioning policy" below.

## [Unreleased]

### Changed — Eval methodology (no plugin behavior change)

- **Eval harness rewritten** per [ADR-0017](../../docs/adr/0017-rigorous-criteria-methodology.md):
  scoring is now per-criterion binary checks with paired-bootstrap-CI
  merge gating (Wilson 95% CI on pass-rate, 10k-resample bootstrap on
  Δp̂, |Δ| ≥ 0.15 effect-size floor). The legacy 5-point composite
  rule from ADR-0011 is removed. Each criterion declares a single
  `target_artifact` so failures map 1:1 to a file to open. No change
  to plugin code; this is purely a measurement upgrade.
- **v2 canonical baseline** (Sonnet, 10-task, n=3): **94.7** overall
  pass-rate across applicable criteria. See `evals/README.md`.
- **Judge calibration** infrastructure added under `evals/judge/`:
  binary rubrics gated on Gwet's AC2 ≥ 0.7 against human labels.
  No rubric currently calibrated; `judge_binary` criteria fall back
  to `skipped`. PR-7 (handback quality migration) blocked on labels.

### Fixed — Eval harness

- **`evals/run.py`**: removed call to `_classify_ask` (deleted in
  PR-8 of the methodology shift) from `_parse_stream_json`. Without
  this fix, every fixture that fired `AskUserQuestion` would crash
  with `NameError`, silently swallowed by the broad `except Exception`
  as `error:`. Caught by independent audit; the published v2
  canonical numbers were captured before PR-8 and remain valid.

## [0.3.0] - 2026-05-19

### Added — Behavior

- **Behavior:** `autopilot:decision-log` skill is now reliably invoked
  via state-tracked PreToolUse nudge. Mechanism: `guard.mjs` maintains
  a per-session `<id>.dlog-writes` counter that increments on Edit/Write
  and resets when posttool-log observes a `Skill` call for
  `autopilot:decision-log`. At threshold (default 3, env-overridable
  via `AUTOPILOT_DLOG_THRESHOLD`), the next Edit/Write gets an
  `additionalContext` nudge instructing the agent to invoke the skill
  before proceeding. Empirical: fixture 09 (decision-log) went from
  0 invocations across all baselines to **3/3 invocations** with
  composite **100/100/100**. Was previously documented as a persistent
  Class B gap; the state-tracked-at-tool-layer pattern reclassifies it
  as a hybrid Class A trigger — see updated ADR-0016.

### Added — Hook

- New `DLOG_THRESHOLD` constant and `checkDecisionLog` function in
  `guard.mjs`. Wired into the existing `pretool-budget` mode (matcher
  `""` — fires on every tool call). Non-blocking (warning only, agent
  retains autonomy).

### Added — Fixtures

- `evals/tasks/10-verifier-catches-bug.yaml` — sharper test for the
  verifier subagent with a deliberate SQL-injection trap.

### Changed — Documentation

- `docs/autopilot-plugin.md` Known Limitations: removed
  "decision-log skill is not reliably invoked" — the mechanism fix
  resolves it (verified empirically at v0.3.0).
- ADR-0016 amended: the binary Class A / Class B distinction admits
  a hybrid third class where triggers can be detected via *aggregated
  tool-layer state*, not just single tool inputs. Decision-log is the
  exemplar (writes-since-last-skill counter).

### Behavior — what shifted (preliminary; full baseline at next release)

`Sonnet single-task probe scores (3 runs):`
- 09-decision-log: **NEW MECHANISM** → 100, 100, 100 (was 0 invocations in all prior baselines)

### Documented limitations (now smaller)

- `architectural_choice` and `ambiguity` triggers cap around 33-50 mean
  on Sonnet; brief-content-only triggers without any tool-layer state
  signal remain not-mechanism-enforceable. These are the only two
  triggers without a mechanism path now.
- All other limitations from 0.2.0 still apply.

---

## [0.2.0] - 2026-05-19

Eval-driven iteration cycle following the 0.1.0 ship. All changes below
are empirically verified via `evals/run.py` against the canonical
Sonnet baseline. See `evals/README.md` for current per-task scores.

### Fixed — Hooks

- **plugin.json `repository` field schema.** Was using npm-style
  `{type, url}` object; Claude Code's manifest schema requires a string.
  The plugin had been failing to load silently in every real session
  between 0.1.0 and the discovery.
- **Session-id resolution.** Code used `CLAUDE_SESSION_ID` env var
  which doesn't exist. Correct name is `CLAUDE_CODE_SESSION_ID`, also
  available as `session_id` on hook stdin. Without this fix every
  audit log collapsed into `unknown-session.jsonl`.
- **macOS Write hook.** Resolve nonexistent paths via walking-ancestor
  realpath, and accept both `/tmp` and `os.tmpdir()` (macOS uses
  `/var/folders/.../T` for the latter).
- **Bash regex bypass-tightening** based on adversarial probe results:
  hardened against `find -delete`, `dd`, `shred`, `truncate`, escaped
  `\rm` / `/bin/rm`, env-var indirection (`PATH=...`, `LD_PRELOAD=...`),
  `git -c alias.X='!rm -rf .'`, base64 piping. PATH pinned + LD_PRELOAD
  unset inside the guard.
- **SECRET_PATTERNS over-redaction.** The opaque-token regex matched
  workspace dir names containing 32+ char `[A-Za-z0-9_-]` runs
  (e.g. `/tmp/autopilot-eval-07-budget-tick-1d3jcl6o/...` → `/tmp/***/...`).
  Fixed with `(?<!\/)\b...\b(?!\/)` lookarounds. Known limit:
  hyphen-rich path segments with 32+ chars between hyphens can still
  partially match; documented in tests.

### Added — Behavior

- **Behavior:** Budget yellow tick now actually nudges the agent.
  Was previously stderr-only at hook exit 0, which Claude Code does
  not surface to the model. Fix: switch to stdout JSON
  `hookSpecificOutput.additionalContext` injection. Empirical: task
  07 (budget-tick fixture) went 30 → 96.7 mean composite score on
  Sonnet 3-run baseline. See ADR-0015.
- **Behavior:** Irreversibility yellow trigger now nudges on
  detectable irreversible commands (`git commit`, `git push`,
  `git tag`, `gh pr create`). Same `additionalContext` mechanism as
  budget tick. Empirical: task 05 (irreversibility fixture) went
  30 → 76.7 mean after the patch. The 1-in-3 remaining miss is the
  same model-bias bimodality seen on architectural-fork (see ADR-0016).
- **Added — Hook:** new `IRREVERSIBLE_PATTERNS` array in
  `hooks/guard.mjs` covering the above commands. Non-blocking; agent
  retains autonomy to proceed if it ignores the nudge.

### Added — Skills

- **Strengthened subagent invocation guidance** in `autopilot/SKILL.md`:
  *"Use autopilot:scout / autopilot:verifier, NOT the built-in Explore /
  general-purpose agents."* Empirical: in repeated probes the agent
  reliably reaches for `autopilot:scout` / `autopilot:verifier` and
  no longer falls back to the built-in `Explore` agent (4/4 runs of
  fixture 08 invoked `autopilot:verifier`).
- **Strengthened ambiguity trigger** in `autopilot/SKILL.md` with
  explicit "vague action verbs are ambiguous by default" rule:
  *"Treat vague action verbs (clean up, improve, refactor, modernize,
  fix, tidy, polish) without a specified target as ambiguous by default."*
  Limited impact: trigger fires more often but still bimodal.
- **Strengthened architectural-fork trigger** with explicit anti-
  rationalization language: *"You will be tempted to rationalize: 'the
  implementation is obvious'. That rationalization is the failure mode
  this trigger exists to prevent."* Empirical: marginal improvement.
- **Cross-skill linking corrected.** `[[name]]` references between
  skills were decorative — agent didn't follow them. Replaced with
  explicit `Skill(skill: 'autopilot:<name>')` invocation instructions.
- **Subagent mention syntax corrected.** Was `[[scout]]`/`[[verifier]]`
  (skills syntax); real path is the `Agent` tool with
  `subagent_type: 'autopilot:scout'` (note plugin namespace).

### Added — Plugin metadata

- `plugin.json` now declares `license`, `homepage`, `repository`,
  `keywords`, `engines.claude-code`.

### Added — Eval / tooling

- `evals/run.py` — wired to `claude --print` end-to-end. Stream-json
  parsing reflects real Claude Code output shape (tool_use nested in
  assistant content; AskUserQuestion is a tool, not an event type).
- `evals/run.py` — per-fixture `setup_commands`, `allowed_tools`,
  `env` fields support fixtures that need git, npm, or env-var setup.
- `evals/run.py` — `--filter <substr>` flag for single-task iteration.
- `evals/run.py` — `score_task` now tracks `Agent` subagent invocations
  (`expected_subagents` field) and `Skill` invocations (`expected_skills`
  field). Both contribute to `appropriate_ask_rate` when declared.
- `evals/compare-runs.py` — diff two result files, flag composite
  regressions >5 points, exit non-zero. Pre-merge gate.
- `evals/probes.sh` — 5-probe adversarial regression suite separate
  from scoring evals.
- `evals/tasks/` — fixtures 04–09 added (external-effect, irreversibility,
  ambiguity, budget-tick, verifier-trigger, decision-log). Initial 01–03
  refined with proper namespacing and Sonnet-appropriate briefs.

### Added — Docs / decisions

- **ADRs 0014–0016** capture the new architectural decisions:
  - 0014: AskUserQuestion is non-functional in `--print` mode.
  - 0015: PreToolUse hook stderr is invisible at exit 0; use
    `additionalContext` JSON.
  - 0016: Triggers split into mechanism-enforced (Class A) vs
    skill-text-only (Class B).
- `docs/autopilot-plugin.md` Known Limitations expanded.
- `evals/README.md` carries the canonical baseline numbers.

### Behavior — what shifted

`Sonnet 7-task canonical baseline mean composite score:`
- 02-scope-drift: **90 → 97**
- 03-arch-fork: 50 → 57 (still bimodal; documented limit)
- 04-external-effect: **89 → 97**
- 05-irreversibility: **30 → 77** (irreversibility nudge mechanism)
- 06-ambiguity: 32 → 32 (skill-text limit; documented in ADR-0016)
- 07-budget-tick: **NEW → 97** (additionalContext mechanism)
- Overall: 56 → 71

### Documented limitations (no fix planned)

- `architectural_choice` and `ambiguity` triggers cap around 50-60 mean
  on Sonnet; brief-content-only triggers are not mechanism-enforceable
  (ADR-0016).
- `AskUserQuestion` does not function in `--print` mode (ADR-0014);
  plugin is fundamentally an interactive-mode tool. Eval measures intent
  only.
- Hook is NOT a security boundary against an adversarial / compromised
  model (ADR-0006).

---

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
