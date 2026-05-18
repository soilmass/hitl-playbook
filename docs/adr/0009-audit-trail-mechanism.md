# 0009. Audit trail mechanism for autopilot sessions

Date: 2026-05-18

## Status

Accepted

## Context

In autopilot mode, the agent makes silent decisions between human checkpoints. The end-of-task handback ([`../../plugins/autopilot/skills/handback/SKILL.md`](../../plugins/autopilot/skills/handback/SKILL.md)) captures `Assumed` entries — but only at task end, by reconstruction. Reconstruction loses context: the agent doesn't remember every silent choice it made an hour ago.

For long autonomous runs, we need a richer audit trail than handback-time recall. Options considered:

- **Transcript scraping** — full reasoning text, but post-hoc only and the transcript format is unstable.
- **PostToolUse hook → JSONL log** — captures the *what* deterministically, doesn't capture *why*.
- **Agent-written decision log** — captures *intent*, but relies on agent discipline.
- **MCP observability server** — structured, queryable, but heavy operational complexity for a solo developer.

No single option covers both *what ran* and *why it ran*. They cover each other's blind spots.

## Decision

We will use a **hybrid: hook for ground truth + skill-enforced decision log for intent.**

Two mechanisms, two log files per session, both under `$CLAUDE_PROJECT_DIR/.claude/autopilot-logs/`:

1. **`<session-id>.jsonl`** — written by the new `posttool-log` mode in [`../../plugins/autopilot/hooks/guard.mjs`](../../plugins/autopilot/hooks/guard.mjs). One JSONL line per tool call, with redacted input summary (capped at 200 chars, regex-redacted secrets), tool name, timestamp, error status. Captures *everything* the agent did. Hook-triggered, no agent cooperation needed.

2. **`<session-id>.md`** — written by the agent per the new [`decision-log`](../../plugins/autopilot/skills/decision-log/SKILL.md) skill. Markdown entries appended every time the agent makes a yellow-tier-adjacent silent choice. Captures *why* the agent decided what it decided. Skill-enforced; the agent must remember to append.

Review surface: the new `/autopilot-review` command reads the decision log first (chronological narrative), then displays a compact summary of the JSONL trace. No web UI; no daemon.

Privacy: the hook log captures input *summaries only* (truncated, redacted), never tool *output* (where secrets actually live). Log dir is in `.gitignore`.

## Consequences

Easier:
- After a 30-minute autonomous run, the human has two complementary views: what happened (JSONL) and why (markdown).
- Failed runs become reviewable — the decision log shows where the agent chose a path that led to the failure.
- Postmortems (see future ADR) have concrete artifacts to reference.

Harder:
- Every PostToolUse adds I/O. For solo dev usage, negligible. For high-frequency tool loops, measurable.
- The decision log relies on agent discipline — if the agent forgets to append, the silent decision is invisible until handback. Mitigated by listing the discipline as a top-tier operating principle in `autopilot/SKILL.md`.
- Redaction is heuristic regex; novel secret formats slip through. The mitigation is "don't log tool output, only input"; if a secret is in an input command (`curl https://api.example.com/?token=...`), it's at risk.

Constrains:
- Log paths are hard-coded under `.claude/autopilot-logs/`. If Claude Code changes its project-dir convention, paths need updating.
- The handback skill now points at the audit-trail location — handback and decision-log are coupled.
