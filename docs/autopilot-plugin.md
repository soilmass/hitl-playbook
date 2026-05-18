# Autopilot Plugin

**Source:** [`../plugins/autopilot/`](../plugins/autopilot/)
**Implements:** [`hitl-framework.md`](./hitl-framework.md)
**Status:** v0.1 (2026-05-18)

Canonical reference for what the autopilot plugin contains, how each piece works, and why.

---

## Purpose

A Claude Code plugin for high-autonomy work with surgical human-in-the-loop gates. Default behavior is to proceed; asking is the exception. Destructive operations are hard-stopped by hooks, not by skill instructions the model could ignore.

---

## File-by-file

### `.claude-plugin/plugin.json`

Plugin metadata. Required fields: `name`, `version`, `description`. Optional but recommended: `author`. See [Claude Code plugins reference](https://code.claude.com/docs/en/plugins-reference) for the full schema.

### `skills/autopilot/SKILL.md`

The operating philosophy. Defines:

- The three tiers (green / yellow / red) and what falls in each.
- The categorical yellow-tier triggers (scope drift, architectural choice, ambiguity, external effect, irreversibility, budget tick).
- Operating principles: status not narration, ask once well, prefer subagents over questions, don't gold-plate, don't work around hooks.
- Common failure modes to avoid: over-asking, under-asking, sycophantic acceptance, hook circumvention.

Loaded by either entry mode:
- The `/autopilot <task>` command (per-task).
- The SessionStart hook when `CLAUDE_AUTOPILOT=1` (always-on).

See [ADR-0002](./adr/0002-three-tier-action-classification.md), [ADR-0004](./adr/0004-categorical-ask-triggers.md), [ADR-0007](./adr/0007-prefer-subagents-over-human-questions.md).

### `skills/checkpoint-format/SKILL.md`

The required format for every yellow-tier `AskUserQuestion` call. Contains:

- The required shape (status preamble, concrete question, 2–4 options, recommended first).
- Templates for question types: architectural choice, scope confirmation, budget tick, ambiguity resolution, pre-irreversible action.
- Anti-patterns: vague "should I proceed?", asking after acting, more than 4 options, prose questions.

See [ADR-0003](./adr/0003-askuserquestion-as-exclusive-hitl-surface.md).

### `skills/handback/SKILL.md`

End-of-task report format. Two variants:

- **Done:** headline + Changed / Skipped / Assumed / Verify before merging / Open questions.
- **Blocked:** Blocked headline + Did / Tried / Need from you.

The **Assumed** section is the load-bearing audit trail for silent decisions made in autopilot mode.

### `commands/autopilot.md`

Slash command for per-task entry: `/autopilot <task description>`. Loads the autopilot skill, restates the task, surfaces foreseeable yellow-tier decisions up front, then proceeds.

See [ADR-0005](./adr/0005-both-entry-modes-for-autopilot.md).

### `commands/checkpoint.md`

Slash command to force an immediate checkpoint mid-task: `/checkpoint`. Produces a status + plan + `AskUserQuestion` with a continue option and 1-2 redirect options.

### `agents/verifier.md`

Read-only subagent for independent verification. Tools: Read, Grep, Glob, Bash. Used instead of asking the human "is this correct?".

Output format: Verdict (Pass / Pass with notes / Fail) + concrete issues + non-blocking notes + an explicit "did not verify" list so the main agent doesn't assume false coverage.

### `agents/scout.md`

Research subagent. Tools: Read, Grep, Glob, WebFetch, WebSearch, Bash. Used instead of asking the human "where is X?" or "what does Y do?". Returns synthesis, not raw search results, capped at ~300 words.

See [ADR-0007](./adr/0007-prefer-subagents-over-human-questions.md).

### `hooks/hooks.json`

The enforcement layer for red-tier operations. Three hooks:

1. **PreToolUse on `Bash`** — regex blocks destructive patterns: `rm -rf`, force-push (including `-f`, `-fu`, `-uf` short forms), `git reset --hard`, `git clean -fd`, publish commands (`npm`, `pnpm`, `yarn`), `gh pr merge`, `gh release create`, `--no-verify`, `DROP TABLE`, `TRUNCATE TABLE`.
2. **PreToolUse on `Write`** — blocks writes outside the project's `cwd` and `/tmp`.
3. **SessionStart** — if `CLAUDE_AUTOPILOT=1` is set in the environment, injects the autopilot mode instruction into the session via `additionalContext`. No-op otherwise.

The Bash regex is non-trivial due to short-flag combination handling (`-fu` and `-uf` must block but `feature-fix` must not). See [ADR-0006](./adr/0006-hooks-as-sole-enforcement-layer.md) for why this is the *sole* enforcement layer.

---

## What's intentionally NOT in the plugin

- **`settings.json` at plugin root.** Claude Code only honors `agent` and `subagentStatusLine` keys there; `permissions.allow` / `permissions.deny` are silently ignored. The plugin cannot ship permissions. See [ADR-0006](./adr/0006-hooks-as-sole-enforcement-layer.md).
- **A second enforcement layer.** The hook regex is the only guard. For defense in depth, install instructions recommend mirroring the denylist into the user's own `~/.claude/settings.json`.
- **Eval harness, cost governance, automated postmortem.** Deferred per [`hitl-framework.md`](./hitl-framework.md).
- **A README.md.** The plugin's behavior is documented here, not duplicated in the plugin directory.

---

## Installation

```bash
# From any project that wants autopilot:
/plugin install /path/to/web-engineering-playbook/plugins/autopilot

# Verify
/help    # /autopilot and /checkpoint should appear

# Optional: enable always-on mode
export CLAUDE_AUTOPILOT=1

# Optional: add a defense-in-depth denylist to your own settings.json
# Mirror the patterns in plugins/autopilot/hooks/hooks.json
```

---

## Verification

The Bash hook regex is tested against 23 cases — 15 destructive that must block, 8 safe that must allow (including tricky branch names like `feature-fix` and `my-foo-branch`). All pass.

Re-running the verification suite is currently a manual exercise — extract the hook command from `hooks/hooks.json` and feed test inputs via `jq`. A packaged script is a known TODO; see [`hitl-framework.md`](./hitl-framework.md) component 5.

---

## Version history

- **v0.1 (2026-05-18)** — initial cut. Implements framework components 1, 2, 4, 6, and partial 5/7. Components deferred: eval (5 programmatic), automated postmortem (7 automated), audit trail.
