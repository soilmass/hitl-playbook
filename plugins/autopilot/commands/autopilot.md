---
description: Enter autopilot mode for the given task. Proceed without asking on safe ops, use AskUserQuestion at branch points, hard-stop on destructive ops.
argument-hint: <task description>
---

Enter autopilot mode and execute the following task:

$ARGUMENTS

Load and follow the `autopilot` skill. Use `checkpoint-format` for any pauses. Produce a `handback` report when done or blocked.

Before starting:
1. Restate the task in one line so the human can catch a misread.
2. Identify any obvious tier-2 (yellow) decisions you can foresee, and if there are blocking ambiguities, surface them now via AskUserQuestion *before* doing any work.
3. Otherwise, proceed.
