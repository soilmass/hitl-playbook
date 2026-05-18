# 0006. Hooks as the sole enforcement layer for destructive ops

Date: 2026-05-18

## Status

Accepted

## Context

We initially designed the autopilot plugin with two enforcement layers for red-tier (destructive) operations:

1. A `permissions.deny` list in the plugin's `settings.json`, denying common destructive bash patterns.
2. PreToolUse hooks in `hooks/hooks.json` running regex checks and exiting non-zero on match.

Defense in depth was the intent: even if a hook regex missed a pattern, the permission denylist would catch it (and vice versa).

Verification against current Claude Code documentation revealed that **`settings.json` at the plugin root only honors `agent` and `subagentStatusLine` keys.** The `permissions` field there is silently ignored — Claude Code reads plugin-shipped `settings.json` for a narrow set of keys and discards the rest.

The denylist was dead config. We had one enforcement layer, not two — we just didn't know it.

## Decision

We will use **PreToolUse hooks as the sole enforcement layer** for destructive ops within the plugin. The plugin ships:

- [`../../plugins/autopilot/hooks/hooks.json`](../../plugins/autopilot/hooks/hooks.json) with PreToolUse matchers on `Bash` (regex blocking destructive patterns) and `Write` (blocking paths outside `cwd`).
- No `settings.json` (deleted).

For a second defense layer, the plugin's install instructions recommend that users add the same denylist to their *own* `~/.claude/settings.json` or project `.claude/settings.json`. This is a per-installation step, not something the plugin can ship.

## Consequences

Easier:
- One enforcement layer means one place to update when new destructive patterns are discovered.
- The hook regex is testable in isolation (and is — the plugin's verification suite covers 23 cases, 15 destructive and 8 safe-but-tricky like `feature-fix`).

Harder:
- No defense in depth from the plugin alone. A bug in the hook regex is a complete bypass.
- Users who don't add the recommended denylist to their own settings have only one enforcement layer.

Constrains:
- Changes to the destructive-pattern list happen in exactly one place: `hooks/hooks.json`.
- If Claude Code adds plugin-level permission support in the future, this ADR should be revisited and likely superseded by one that re-introduces defense in depth.
- Any new destructive operation type (e.g., a new cloud CLI with a destructive subcommand) requires updating the hook regex; there is no fallback.
