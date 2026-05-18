---
description: Display the autopilot decision log and tool-call trace for the current (or specified) session. Read this after an autonomous run to audit what happened.
argument-hint: [session-id]
---

You are reviewing an autopilot session. The user wants to see what the agent did.

1. Determine the session to review:
   - If `$ARGUMENTS` is provided, use it as the session ID.
   - Otherwise, find the most recent file under `$CLAUDE_PROJECT_DIR/.claude/autopilot-logs/` (sort by mtime, take newest).

2. Read and display, in order:

   a. **Decision log** (`<session-id>.md`) — read the full file and display verbatim. This is the narrative of silent decisions in chronological order.

   b. **Tool-call summary** (`<session-id>.jsonl`) — parse the JSONL and produce a compact table:
      ```
      timestamp  tool       input (redacted)
      ```
      Group consecutive same-tool calls if there are >5 in a row ("Read x12 files in src/").

   c. **Statistics** — at the bottom:
      - Total tool calls
      - Breakdown by tool (Read: N, Edit: M, Bash: K, ...)
      - First and last timestamps
      - Any tool calls that returned errors

3. Do NOT modify the logs. Read-only review.

4. After displaying, ask the user (via AskUserQuestion):
   - "Continue investigating" — open a specific entry or run a follow-up grep.
   - "Mark reviewed — looks good"
   - "Found a problem — start a postmortem" (if `docs/postmortems/TEMPLATE.md` exists, point at it).

If neither file exists for the session, report that and list available session IDs found in the log directory.
