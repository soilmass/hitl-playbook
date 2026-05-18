# 0013. Cross-platform Node helper for hooks

Date: 2026-05-18

## Status

Accepted

## Context

The original hook implementation ([ADR-0006](./0006-hooks-as-sole-enforcement-layer.md) era) used inline bash with `jq` and GNU `grep -E` in `hooks/hooks.json`. Cross-platform investigation revealed:

- **Linux:** works (GNU grep, jq packaged).
- **macOS:** works for grep (BSD grep supports `[[:space:]]` POSIX classes — a common misconception), but `jq` is not preinstalled. Users without Homebrew `jq` see hooks silently no-op — the `cmd=$(jq -r ...)` assignment becomes empty, grep matches nothing, destructive commands pass through. Same-class security failure as the hook being disabled.
- **Windows:** broken. Claude Code on Windows runs hooks via Git Bash (MSYS2), which doesn't bundle `jq`. Path handling also breaks — `pwd` returns `/c/Users/...` while `tool_input.file_path` may be `C:\Users\...` — the cwd-containment check fails for legitimate writes, blocking everything.

Inline bash with `jq` has two compounding fragility points: tool availability and path normalization. Neither is fixable in pure bash without shipping a vendored toolchain.

## Decision

We will replace inline bash hooks with a **Node helper** at [`../../plugins/autopilot/hooks/guard.mjs`](../../plugins/autopilot/hooks/guard.mjs), invoked via `node "${CLAUDE_PLUGIN_ROOT}/hooks/guard.mjs" <mode>` from `hooks.json`.

Rationale:
- **Node is already required.** Claude Code itself runs on Node — if Claude Code is installed, `node` is available. No new dependency.
- **No `jq` needed.** `JSON.parse(readFileSync(0, 'utf8'))` reads stdin natively.
- **No path normalization issues.** `path.resolve()` produces canonical absolute paths on all platforms; `realpathSync` resolves symlinks; `path.sep` handles Windows backslashes.
- **Regex is identical across OSes.** JS regex engine doesn't vary by platform like grep does.
- **Exit codes honored uniformly.** `process.exit(0)` / `process.exit(2)` work identically on Linux/macOS/Windows.

The guard is a single ~210-line file with four modes selected by `argv[2]`:
- `pretool-bash` — destructive-pattern regex check
- `pretool-write` — path canonicalization + cwd-containment check
- `pretool-budget` — tool-call counter threshold check ([ADR-0012](./0012-cost-budget-via-tool-call-counter.md))
- `posttool-log` — redacted JSONL append + budget counter increment ([ADR-0009](./0009-audit-trail-mechanism.md))
- `session-start` — env-var-gated mode injection ([ADR-0005](./0005-both-entry-modes-for-autopilot.md))

This does not supersede [ADR-0006](./0006-hooks-as-sole-enforcement-layer.md) — hooks remain the sole enforcement layer. It changes the *implementation language*, not the architectural decision.

## Consequences

Easier:
- Plugin works on Windows / macOS / Linux without per-platform branching.
- One language, one regex engine, one test suite (`test/run-hook-tests.sh` runs the Node guard on all three OSes — CI matrix Linux + macOS proves it).
- Future hook logic (smarter checks, structured outputs) is easier to write in JS than dense bash.

Harder:
- Node startup cost per hook fire (~50ms cold; faster after Node module caching). Negligible at solo-dev scale; possibly visible in high-frequency tool-call loops.
- Requires `node` in `PATH` at hook invocation. If Claude Code's host environment lacks it (unlikely), hooks fail open. Mitigation: the failure produces a visible error in Claude Code's hook output.
- Marginally more code than a one-line bash regex. Worth it for the portability + readability + testability.

Constrains:
- All hook logic now lives in one file. Splitting modes into separate files is possible but unnecessary at this size.
- Future destructive-pattern additions edit a JS regex array — easier to maintain than the previous bash regex but still a single point of failure.
- Cross-platform behavior must be tested on macOS (the CI matrix covers this) and ideally Windows (manual until a Windows runner is added).
