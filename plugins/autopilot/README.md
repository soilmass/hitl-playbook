# autopilot

A Claude Code plugin for high-autonomy work with surgical human-in-the-loop gates. The agent proceeds by default, pauses via `AskUserQuestion` at categorical branch points, and is hard-stopped from destructive operations by hooks.

## Install

```bash
/plugin install /path/to/hitl-playbook/plugins/autopilot
```

Verify the install:

```
/help    # /autopilot and /checkpoint should appear
```

## Try it

```
/autopilot add a CHANGELOG entry for the most recent commit
```

This is a safe first task — read-only discovery, one small write, and a handback report. It exercises every plugin surface (skill, checkpoint format, handback) with no risk.

## What to expect

- The agent restates the brief, then proceeds.
- It will pause via a structured `AskUserQuestion` at decision points (scope drift, architectural choice, ambiguity, irreversibility, every ~10 tool calls).
- Destructive commands (`rm -rf`, force-push, `npm publish`, etc.) are hard-blocked by the guard — the agent surfaces to you instead of running them.
- When done, you get a **handback** report. **Read `Assumed:` first** — that's where silent decisions are listed and the most likely place to find a problem.

## Always-on mode (optional)

```bash
export CLAUDE_AUTOPILOT=1
```

A SessionStart hook then loads autopilot for every session in that environment. Recommended only after you've done a few `/autopilot` runs and trust the behavior.

## Recommended model

**Sonnet or stronger.** Verified via the eval harness: Haiku consistently ignores categorical yellow-tier triggers (0 asks across 6 runs on the scope-drift fixture); Sonnet honors them (2/2). The plugin's HITL guarantees are model-dependent. Haiku is acceptable for trivial green-tier work but isn't reliable enough for the supervised mode the plugin is designed around.

```bash
# In your Claude Code config or session: prefer Sonnet
claude --model sonnet ...
```

## Defense in depth (optional)

The plugin's hook is the only enforcement layer. For belt-and-suspenders, mirror the destructive-command patterns into your own `~/.claude/settings.json` `permissions.deny` list. The hook is not a real security boundary — it stops accidents and well-behaved agents, not a compromised model.

## Reference

Canonical reference lives at [`../../docs/autopilot-plugin.md`](../../docs/autopilot-plugin.md). Methodology is at [`../../docs/hitl-framework.md`](../../docs/hitl-framework.md). Decisions are recorded in [`../../docs/adr/`](../../docs/adr/).

## Tests

```bash
bash plugins/autopilot/test/run-hook-tests.sh
```

85 cases covering destructive patterns, bypass attempts, edge-case safe commands, and Write-path traversal.
