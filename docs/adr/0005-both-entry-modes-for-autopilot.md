# 0005. Both entry modes for autopilot (slash command + env var)

Date: 2026-05-18

## Status

Accepted

## Context

The autopilot plugin can be entered in two ways:

1. **Per-task slash command** — `/autopilot <task>` enters the mode for one task; the next session is back to default.
2. **Always-on environment variable** — `CLAUDE_AUTOPILOT=1` triggers a SessionStart hook that injects autopilot instructions for every session.

Per-task is safer: the human explicitly opts in each time. Always-on is more ergonomic for users who *always* want autopilot (e.g., solo developers in dedicated agent environments) but easier to forget you're in.

The trade-off isn't "which is better" — different users want different things.

## Decision

We will support **both** modes:

- **Slash command** as the default, per-task entry. Defined in [`../../plugins/autopilot/commands/autopilot.md`](../../plugins/autopilot/commands/autopilot.md).
- **Environment variable + SessionStart hook** as the opt-in always-on mode. Defined in [`../../plugins/autopilot/hooks/hooks.json`](../../plugins/autopilot/hooks/hooks.json). Disabled unless `CLAUDE_AUTOPILOT=1` is set in the environment.

The hook is *opt-in by env var* rather than always-active to prevent surprising users who installed the plugin only for the slash command.

## Consequences

Easier:
- Casual users get safe per-task autonomy without configuration.
- Power users get always-on autonomy with a single environment variable.
- The two modes share the same skill, format, and enforcement — no behavioral divergence between them.

Harder:
- Two entry surfaces to document and test.
- The SessionStart hook fires on every session even when the env var isn't set (it just no-ops). Minor overhead but not zero.

Constrains:
- Changes to the autopilot skill must work for both entry modes.
- The hook's env-var check is the only thing keeping always-on from becoming default; future maintainers must understand this gating.
