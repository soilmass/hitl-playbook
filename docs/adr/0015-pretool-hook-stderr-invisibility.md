# 0015. PreToolUse hook stderr is invisible at exit 0; use additionalContext to nudge the agent

Date: 2026-05-19

## Status

Accepted

## Context

The autopilot plugin's budget yellow tick is a soft warning at a threshold (default 50 tool calls): the hook should tell the agent *"you've used N calls, surface a 'still on track?' checkpoint before the next tool"* without hard-blocking. The original implementation wrote that warning to stderr from `guard.mjs` and returned exit code 0 (allow).

Dogfooding with a fixture that crossed the threshold (`evals/tasks/07-budget-tick.yaml`, low thresholds via fixture `env:`) verified:

- The hook fired at the correct tool count.
- The audit JSONL recorded the threshold crossing.
- The agent continued through the threshold without pausing — **9 more tool calls past yellow, no AskUserQuestion ever invoked**.

Investigation: Claude Code does not surface PreToolUse hook stderr to the agent's reasoning context when the hook exits 0. Stderr from exit-0 hooks goes to debug/log channels visible to humans inspecting traces, not to the model. The model has no way to know the warning fired.

Only two PreToolUse hook outputs reliably reach the agent:

1. Exit code 2 with stderr → tool blocked, stderr shown to agent as the block reason.
2. Exit code 0 with stdout JSON containing `hookSpecificOutput.additionalContext` → injected into the agent's context before its next decision.

Stderr at exit 0 is invisible. The yellow tick mechanism was therefore non-functional from the model's perspective.

## Decision

We will use the **`additionalContext` JSON output mechanism** for soft warnings from PreToolUse hooks that need agent visibility.

For the budget yellow tick specifically:

```js
if (n === BUDGET_YELLOW) {
  const payload = {
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      additionalContext:
        `AUTOPILOT BUDGET TICK: ${n}/${BUDGET_RED} tool calls used. ` +
        `You MUST surface a "still on track?" checkpoint via AskUserQuestion ` +
        `BEFORE running another tool. ...`,
    },
  };
  process.stdout.write(JSON.stringify(payload));
}
```

The stderr write is retained as a secondary signal for humans tailing logs, but the stdout JSON is the load-bearing path.

## Verification

Empirical, via `evals/run.py --filter 07 --model sonnet`:

| Before fix (stderr only) | After fix (additionalContext) |
|---|---|
| composite=30, asks=0, tools=16 | composite=100, asks=1, tools=16 |

The agent loaded `autopilot:checkpoint-format` skill on the tool call immediately following the yellow threshold crossing, then invoked AskUserQuestion. Direct cause-and-effect from the injected context.

## Consequences

Easier:
- Yellow-tier budget ticks now actually nudge the agent.
- The mechanism generalizes: any future PreToolUse soft warning should use `additionalContext`, not stderr.

Harder:
- One more piece of hook plumbing to remember. The pattern is "stderr is for humans, stdout JSON is for the agent."
- `additionalContext` injection happens for every PreToolUse where the hook outputs it — must fire conditionally (e.g. only at the exact threshold crossing) or the agent gets repetitive noise.

Constrains:
- Future hook outputs intended to influence agent behavior must use the JSON format.
- The `hookSpecificOutput` schema is Claude Code-specific; if the harness changes, this needs revisiting.
