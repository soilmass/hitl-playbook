---
name: decision-log
description: Append a markdown entry to the autopilot session decision log every time you make a silent yellow-tier-adjacent decision (a choice you considered escalating but didn't). The log complements the handback by capturing decisions as they happen, not just at task end.
---

# Decision log

In autopilot mode, the `posttool-log` hook captures every tool call automatically. The *decision log* is the intent layer the hook can't capture: when you made a silent choice that could have been a checkpoint, write it down so the human can audit later.

## When to append

Append an entry every time you do any of these without invoking AskUserQuestion:

- Picked between two non-trivial approaches without surfacing both.
- Touched a file slightly outside the briefed scope because the brief seemed to imply it.
- Interpreted an ambiguous brief one way over another.
- Decided NOT to ask the human because the answer felt obvious.
- Deferred a tangential issue to the handback (note it here too).

If you would have asked the human in pair mode, log it here in supervised/autonomous mode.

## Where

Append to `$CLAUDE_PROJECT_DIR/.claude/autopilot-logs/$CLAUDE_SESSION_ID.md`. Create the file if it doesn't exist with a header:

```markdown
# Autopilot session <session-id>

Brief: <one-line restatement>
Started: <ISO timestamp>
```

Then add one entry per decision:

```markdown
## <ISO timestamp> — <one-line decision summary>

- **Considered:** <option A>, <option B>, ...
- **Chose:** <option>
- **Why:** <one-line reason — load-bearing for audit>
```

Keep entries terse — three to five lines. The reviewer scans this file top-to-bottom to reconstruct the run's reasoning.

## Rules

- **Prose only.** Never quote file contents, never paste tool output. Those go in the JSONL hook log and risk dragging secrets in.
- **One entry per decision.** Don't batch unrelated decisions into a single entry.
- **No retroactive editing.** Each entry is timestamped at the moment of decision; if you change your mind later, append a new entry referencing the old one.
- **Reference in handback.** The final handback's `Verify before merging:` section should point at this log: *"See `.claude/autopilot-logs/<id>.md` for silent-decision rationale."*

## What NOT to log

- Green-tier work (reads, in-scope edits, tests, lints, subagent spawns) — the JSONL hook log has those.
- Yellow-tier asks that you actually surfaced via AskUserQuestion — the human's selection is the record.
- Routine intermediate steps with no decision content ("ran the tests, they passed").

## Why this exists

Component 4 of the HITL framework ([`../../docs/hitl-framework.md`](../../../docs/hitl-framework.md)) requires the **Assumed** handback field as the audit trail for silent decisions. The decision log is its companion: assumptions captured *as they form*, not reconstructed at task end. End-of-task reconstruction loses context.
