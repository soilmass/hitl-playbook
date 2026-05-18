# 0008. Context management strategy for autopilot

Date: 2026-05-18

## Status

Accepted

## Context

Long autopilot runs fail by drowning the main context window. Symptoms:

- Agent re-reads files it already read, because the earlier read scrolled out of working attention.
- Agent loses thread on the brief because too much intervening tool output dilutes it.
- Agent asks the human a question whose answer is in a tool result already in context.
- Subagent transcripts get paraphrased into main context, bloating it twice.

[ADR-0007](./0007-prefer-subagents-over-human-questions.md) established *that* subagents are preferred for research/verification, but not *when* to spawn vs. read directly. Without explicit heuristics, the agent either over-spawns (token cost, latency) or under-spawns (context bloat).

## Decision

We will encode explicit context-management heuristics in [`../../plugins/autopilot/skills/autopilot/SKILL.md`](../../plugins/autopilot/skills/autopilot/SKILL.md) under a new "Context management" section, covering four areas:

1. **Subagent vs main-context heuristics.** Spawn a subagent when any of: breadth (>5 files), depth (single file >1500 lines, summary only needed), throwaway exploration, or verification-before-commitment. Read directly for 1-3 known files, known-symbol greps, or content that will be edited next.

2. **Compaction triggers.** Proactively summarize-and-discard when a research phase ends, after ~30 tool calls since last checkpoint, or near 50% context window. Don't rely solely on auto-compaction.

3. **Subagent output handling.** Treat the subagent's final message as authoritative; quote only load-bearing claims into main-context notes; don't re-invoke "to double-check" — spawn `verifier` with a different framing instead.

4. **Main-context hygiene.** Read narrowly (`offset`/`limit`); search before reading; one pass per file; discard transcripts after a subagent returns.

The rule of thumb: **if the output you need is a synthesis, delegate; if it's the raw bytes, read directly.**

## Consequences

Easier:
- Long autopilot runs stay coherent — agent doesn't lose the brief to context bloat.
- Subagent invocation decisions are deterministic, not vibes-based.
- Token spend is more predictable (delegation is cheaper than re-reading).

Harder:
- The skill section adds ~50 lines to `autopilot/SKILL.md`. Worth it for the load-bearing nature, but it's more for the agent to internalize.
- Heuristics like "1500 lines" and "30 tool calls" are arbitrary defaults; real teams will tune them.

Constrains:
- New subagents introduced via [ADR-0007](./0007-prefer-subagents-over-human-questions.md) need to be added to the heuristics or the agent won't reach them.
- The compaction trigger rules assume the agent can self-assess context usage; if the model lacks that introspection, the triggers are advisory only.
