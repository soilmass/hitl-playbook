# 0003. AskUserQuestion as the exclusive HITL surface

Date: 2026-05-18

## Status

Accepted

## Context

When the agent pauses for human input mid-task, it can either:

(a) Print a prose question in the chat and wait for a free-text reply, or
(b) Invoke the harness's structured-question tool (`AskUserQuestion` in Claude Code) which renders a labeled question with discrete options.

Prose questions degrade the HITL surface in several ways:

- Free-text replies have to be re-parsed; the agent often misreads them.
- Options are implicit; the human invents a third path the agent didn't consider.
- No visual distinction from regular agent narration — easy to miss.
- Inconsistent format across asks makes the user habituate to skimming.

Structured questions fix all four problems but require the harness to support them and require the agent to discipline itself into always using them.

## Decision

In autopilot mode, the agent uses **`AskUserQuestion` exclusively** for every yellow-tier pause. Prose questions are prohibited.

Every `AskUserQuestion` call must follow the format in [`../../plugins/autopilot/skills/checkpoint-format/SKILL.md`](../../plugins/autopilot/skills/checkpoint-format/SKILL.md):

1. One-line status preamble (past tense) in the surrounding message.
2. A concrete, specific question — never "should I proceed?".
3. 2–4 options, each with a label (≤5 words) and a one-line consequence description.
4. Recommended option first, marked "(Recommended)".

## Consequences

Easier:
- Every HITL gate looks the same — the human develops fast pattern recognition.
- Options are explicit; the human sees the trade-offs without reading the agent's mind.
- The agent cannot accidentally turn a checkpoint into an open-ended conversation.

Harder:
- Some questions genuinely don't fit 2–4 options. The agent must collapse, split, or pick a default + offer "Other".
- Requires the harness to support a structured-question tool. Claude Code does; other harnesses may not.

Constrains:
- The autopilot plugin is currently Claude Code-specific. Porting to another harness requires an equivalent structured-question mechanism, or a fallback to disciplined prose with a documented degradation.
- The format spec in `checkpoint-format/SKILL.md` is load-bearing; changes to it propagate to every checkpoint.
