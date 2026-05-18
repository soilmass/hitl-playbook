---
description: Show current autopilot session budget status (tool calls used, thresholds, breakdown).
---

Display the current autopilot budget for this session.

1. Read `$CLAUDE_PROJECT_DIR/.claude/autopilot-logs/$CLAUDE_SESSION_ID.budget` for the running tool-call count. If missing, count is 0.
2. Read `$CLAUDE_PROJECT_DIR/.claude/autopilot-logs/$CLAUDE_SESSION_ID.jsonl` and produce:
   - Total tool calls (should match the budget file)
   - Breakdown by tool name
   - First and last timestamp; elapsed time
   - Count of errored tool calls
3. Compare against thresholds:
   - Yellow: `AUTOPILOT_BUDGET_YELLOW` env var or default 50
   - Red: `AUTOPILOT_BUDGET_RED` env var or default 150
4. Render as:

   ```
   Budget: N / RED tool calls (YELLOW yellow)
   Breakdown: Read=12, Edit=4, Bash=3, ...
   Elapsed: 18m  (started 2026-05-18T14:02:11Z)
   Errors:  0
   Status:  green | YELLOW (next checkpoint due) | RED (hand back now)
   ```

Read-only. Do not modify the budget file.
