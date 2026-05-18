# 0014. AskUserQuestion is non-functional in `--print` mode

Date: 2026-05-18

## Status

Accepted

## Context

Yellow-tier checkpoints in autopilot mode use the `AskUserQuestion` tool exclusively ([ADR-0003](./0003-askuserquestion-as-exclusive-hitl-surface.md)). This works in interactive `claude` CLI sessions: the tool renders a structured question, the human selects an option, the agent receives the response and proceeds.

Dogfooding the plugin against `claude --print` (non-interactive mode, used for batch, CI, and the eval harness in `evals/run.py`) surfaced a definitive limitation. With a direct probe — instructing the agent to invoke `AskUserQuestion` with a trivial color-choice question — the trace shows:

1. The agent calls `AskUserQuestion` with valid options. The `tool_use` event appears in the stream.
2. Claude Code returns an immediate tool result: `is_error: true`, content `"Answer questions?"`. There is no interactive user to answer.
3. The agent recovers by writing a prose question in its text response ("Let me know your preference — Blue or Red"), even though the autopilot skill explicitly forbids prose questions.

This is a Claude Code design choice, not a plugin bug. `--print` mode has no interactive surface to render structured questions against.

## Decision

We accept this as a **documented limitation, not a fix target.** Specifically:

- **Interactive sessions** (the intended end-user experience — a human running `/autopilot` in their terminal) retain full yellow-tier functionality.
- **Batch / CI / eval contexts** cannot get a real human response to `AskUserQuestion`. The autopilot plugin in those contexts:
  - Will still *attempt* to invoke `AskUserQuestion` at yellow-tier triggers.
  - Will receive an error response and revert to prose, violating its own "no prose questions" rule.
  - Effectively bypasses the yellow-tier gate.

The eval harness (`evals/run.py`) **measures intent, not response**: it counts `AskUserQuestion` tool-use events regardless of whether they got a real answer. This is the correct semantic for measuring whether the plugin's triggers fire at the right moments.

We do not attempt to:
- Inject auto-responses via `--input-format stream-json` (possible but adds complexity and conflates "agent asked" with "human answered specific thing").
- Add a "no-AskUserQuestion mode" to the plugin (would fragment behavior).
- Reimplement the question surface (out of scope).

## Consequences

Easier:
- Honest framing: autopilot is fundamentally an *interactive-mode* tool. Batch usage is best-effort.
- Eval harness has clear semantics: scores plugin behavior (intent), not human responses.
- No engineering effort spent fighting a Claude Code design choice.

Harder:
- Batch/CI testing cannot verify the full HITL loop end-to-end; only the agent side.
- Users who try to run `/autopilot` non-interactively will see degraded behavior (prose questions) and won't know why without reading this ADR.
- The `--print`-mode prose-question fallback is *also* a violation of the autopilot skill's rules. The skill cannot enforce a rule that depends on a tool that doesn't function in that mode.

Constrains:
- Any future "headless autopilot" use case (e.g., autopilot running in CI to maintain code) needs a different question mechanism — likely treating every yellow-tier trigger as a hard-stop with handback explaining what would have been asked.
- Plugin documentation (README + `autopilot-plugin.md`) must surface this limitation prominently so users know what mode supports what.

## Related findings

Same dogfood pass also surfaced:
- The `Skill` tool returns `is_error: true` when invoked, but the agent's response often appears successful — investigation needed to know whether the skill content actually loaded.
- The agent in `--print` mode can talk itself out of architectural-fork triggers ("the brief is a clear directive") even when the skill text explicitly warns against this rationalization. Likely related to the lack of a real ask-and-wait surface — there's no cost to skipping the ask.
