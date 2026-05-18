---
name: handback
description: End-of-task report format for autopilot mode. Invoke when the briefed task is complete or you are truly blocked.
---

# Handback report

When autopilot mode completes a task (or is fully blocked), produce a handback in this shape. The human is reading this to decide whether to merge, retry, or redirect — make that decision fast.

## Format (when done)

```
**Done:** <one-line summary of what shipped>

**Changed:**
- path/to/file.ts:42 — what changed and why
- path/to/other.ts — created; contains X

**Skipped:**
- <thing you noticed but didn't fix, with reason>

**Assumed:**
- <load-bearing assumption you made without asking — flag for review>

**Verify before merging:**
- <concrete spot to re-check; not "review the diff">

**Open questions:**
- <anything you'd ask if the loop continued>
```

## Format (when blocked)

```
**Blocked:** <one-line description of what's stuck>

**Did:**
- <what you completed before hitting the block>

**Tried:**
- <approaches you attempted; why each didn't work>

**Need from you:**
- <specific input that would unblock — credential, decision, missing context>
```

## Rules

- Lead with **Done** or **Blocked**. Headline first.
- **Changed** lists *behavior changes*, not every touched file. Formatting-only edits don't belong here.
- **Assumed** is the most important section. Any decision made without asking should appear here — that's the audit trail for autopilot mode.
- **Verify before merging** is concrete: *"Check that the new error path returns 401, not 500"* — not "review the auth changes."
- Don't restate the brief. The human knows what they asked for.
- Don't apologize, don't editorialize, don't pad. Terse is respectful.

## Why this matters for autopilot

In autopilot mode the human did not watch every step. The handback is their only window into what happened. A bad handback turns "high autonomy" into "high blast radius" — the human can't tell what was decided silently. Make the **Assumed** section ruthlessly complete.
