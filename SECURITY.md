# Security policy

## Reporting

Please report security issues privately via GitHub Security Advisories on this repo (`Security` tab → `Report a vulnerability`), not via public issues.

For non-security bugs, use the regular issue tracker.

## What this project IS

A defensive HITL framework for Claude Code that:

- **Hard-blocks destructive bash patterns** at the PreToolUse hook layer: `rm -rf`, force-push, `git reset --hard`, `gh pr merge`, `npm publish`, SQL `DROP/TRUNCATE`, base64-piped eval, env-var hijack (`PATH=`, `LD_PRELOAD=`), and 80+ other patterns. See `plugins/autopilot/hooks/guard.mjs` and the 88-case regression suite in `plugins/autopilot/test/run-hook-tests.sh`.
- **Blocks Write operations to paths outside the project's `cwd` and `/tmp`** via PreToolUse on the `Write` tool, with symlink canonicalization to defeat `..` traversal.
- **Redacts common secret patterns** in the audit JSONL log: anything matching `api_key=`, `token=`, `bearer=`, `password=`, `authorization=`, plus opaque 32+ char tokens not embedded in paths. The redaction logic is in `SECRET_PATTERNS` in `guard.mjs`.
- **Logs every tool invocation** to a per-session JSONL audit trail so suspicious behavior is reviewable post-hoc.

## What this project IS NOT

**The autopilot plugin is NOT a security boundary against an adversarial or compromised model.** This is stated explicitly in [`docs/adr/0006-hooks-as-sole-enforcement-layer.md`](./docs/adr/0006-hooks-as-sole-enforcement-layer.md). Specifically:

- A determined / compromised agent can defeat the hook regex via novel indirection (custom CLIs the regex doesn't know about, calling arbitrary scripts via `xargs`, embedding shell commands in higher-level tools like `python -c` *combinations* the regex hasn't been tightened against).
- Hook stderr at exit 0 is invisible to the agent ([ADR-0015](./docs/adr/0015-pretool-hook-stderr-invisibility.md)) — yellow warnings are best-effort, not enforced.
- `AskUserQuestion` does not function in `claude --print` mode ([ADR-0014](./docs/adr/0014-askuserquestion-print-mode-limitation.md)) — the HITL surface is interactive-mode only; batch use degrades to advisory.
- The audit log's secret-redaction is regex-based and pattern-incomplete: novel secret formats may not be matched. Tool *output* is never logged (only input summaries) precisely because the redaction can't be exhaustive.
- Path-canonicalization in the Write hook handles `..` traversal and symlinks at the standard POSIX level, but is not hardened against TOCTOU races between hook execution and tool execution.

**Real security against adversarial agents requires OS-level sandboxing** (containers, bubblewrap, firejail, gVisor, etc.) — out of scope for a plugin.

## Threat model the plugin DOES address

| Threat | How it's addressed |
|---|---|
| Well-behaved agent fat-fingers `rm -rf` | Hardened destructive-bash regex blocks it |
| Agent silently force-pushes (overwriting upstream) | Force-push patterns covered by hook regex |
| Agent publishes a half-finished package to npm | `npm/pnpm/yarn publish` blocked |
| Agent writes files outside the project (e.g. modifying `/etc`) | Write hook blocks; path canonicalized via `realpath` |
| Agent silently exceeds compute budget | Tool-call counter with hard red threshold at 150 calls (configurable) |
| Agent leaks logged secrets via inputs to common tools | Input summaries redacted on the way to JSONL log |

## Threat model the plugin does NOT address

| Threat | Why not |
|---|---|
| Compromised agent runs `python -c 'import os; os.system(...)'` with novel indirection | Hook regex is heuristic; finite pattern coverage |
| Agent reads secrets from a file and uses them in a tool call where redaction misses | Tool *input* summarization can't be exhaustive |
| Agent exfiltrates data via legitimate-looking outbound HTTP | No network sandboxing |
| Race between hook fire and tool execution | No POSIX-level locking |
| Privileged file access via subprocess that bypasses Claude Code's tool layer | OS-level concern |

If your threat model includes any of these, you need OS-level sandboxing **in addition to** this plugin.

## Defense-in-depth recommendation for production use

1. Run Claude Code inside a container or bubblewrap'd shell with limited network and filesystem access.
2. Mirror the destructive-bash denylist from `plugins/autopilot/hooks/guard.mjs` into your own `~/.claude/settings.json` `permissions.deny` for a second-layer block.
3. Audit `.claude/autopilot-logs/<session>.jsonl` after long autonomous runs (`/autopilot-review` displays them).
4. Use Sonnet, not Haiku (Haiku's reduced trigger compliance increases the chance the agent acts without an HITL pause; see [ADR-0014](./docs/adr/0014-askuserquestion-print-mode-limitation.md) and the model-strength notes in `docs/autopilot-plugin.md`).
5. Treat the audit log as suspect if the agent has *write access* to it — a fully-compromised agent could rewrite history. Ship it to a read-only sink for high-stakes use.

## Disclosure timeline

I'll triage reports within 7 days. Fixes for the plugin's hook regex (e.g. a new bypass class) typically ship within 48 hours of triage. Coordinated disclosure window: 30 days standard; longer if the fix requires architectural changes.

## Past advisories

None.
