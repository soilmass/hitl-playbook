# 0016. Categorical triggers split into mechanism-enforced and skill-text-only

Date: 2026-05-19

## Status

Accepted

## Context

The six yellow-tier categorical triggers in [`autopilot/SKILL.md`](../../plugins/autopilot/skills/autopilot/SKILL.md) are documented as if equally enforceable. Empirical eval data across many runs (see `evals/results/canonical-7task-sonnet-*` + per-fixture probes) shows two distinct behavior classes:

**Class A — reliably honored when nudged at the tool layer:**
- `budget_tick` (verified via `additionalContext` injection at threshold crossing — went from 30 to 96.7 mean after [ADR-0015](./0015-pretool-hook-stderr-invisibility.md) fix)
- `irreversibility` for detectable commands like `git commit` / `git push` (verified — went from 30 to 76.7 mean after the same injection mechanism applied to irreversibility patterns)
- `external_effect` for detectable commands (already at 96.7 — likely benefits from the same mechanism implicitly via skill text since external-effect commands are usually recognizable)

**Class B — model talks itself out of, regardless of skill-text strength:**
- `architectural_choice` (~57 mean, bimodal — agent recognizes the choice but rationalizes proceeding)
- `ambiguity` (~32 mean — agent picks an interpretation silently)

The pattern: Class A triggers correspond to actions detectable at the **tool layer** (a specific Bash command, an external API call). Class B triggers depend on understanding the **brief or codebase context** — they can't be detected by inspecting the next tool call.

## Decision

We will treat these classes differently in plugin design:

**Class A (tool-layer-detectable):** enforce via hook injection of `additionalContext` JSON on the relevant PreToolUse events. The hook detects the trigger condition from `tool_input` and injects a nudge directly into the agent's context before the next decision. Mechanism examples:

- `pretool-budget` mode in `guard.mjs` — fires on counter threshold
- `IRREVERSIBLE_PATTERNS` in `guard.mjs` — fires on `git commit` / `git push` / `git tag` / `gh pr create`
- Future: external-effect patterns (curl-to-external-API, slack webhooks, etc.) could be similarly nudged if reliability becomes a concern

**Class B (brief-content-only):** skill text is the only lever. Accept that reliability will be bimodal (~50% hit rate on Sonnet, even with strong language). Document the limit, and rely on the handback's `Assumed:` section as the post-hoc audit trail for silent decisions.

We will NOT attempt to:
- Hard-block Class A commands (would break routine git/commit/push use)
- Inject context on every brief-content decision (no detection mechanism exists at the tool layer)
- Strengthen Class B skill text further (proven to hit a ceiling around 30-57 mean)

## Consequences

Easier:
- Plugin authors have a clear decision rule: if the trigger can be detected from `tool_input`, build a hook nudge; if not, write skill text and accept the limit.
- Eval expectations become honest: Class A fixtures should score ≥90, Class B fixtures cap around 60.
- Future trigger additions to the plugin are pre-categorized — no debate about whether to invest in hook plumbing vs skill text.

Harder:
- Hook plumbing has to grow as new Class A triggers are added (IRREVERSIBLE_PATTERNS today, EXTERNAL_PATTERNS tomorrow, etc.). One more place to maintain.
- The asymmetry has to be communicated honestly to users: "asks reliably on tool-detectable triggers; advisory only on brief-detectable ones."
- Class B remains a known gap with no clear fix on the horizon. Users wanting bulletproof ambiguity-detection need to write tighter briefs themselves.

Constrains:
- New trigger types in `autopilot/SKILL.md` should be classified A/B at design time. Class A gets hook coverage in `guard.mjs`; Class B gets skill text + a note in `docs/autopilot-plugin.md` Known Limitations.
- Eval fixtures should be designed to test against the achievable ceiling for their trigger class, not aspirationally against perfect compliance.

## Related work

- [ADR-0015](./0015-pretool-hook-stderr-invisibility.md) — the underlying mechanism (additionalContext stdout JSON, not stderr)
- [ADR-0014](./0014-askuserquestion-print-mode-limitation.md) — caveat: in `--print` mode, even Class A nudges can't get real human responses; the eval measures intent only
- [ADR-0006](./0006-hooks-as-sole-enforcement-layer.md) — hooks aren't security boundaries; same caveat applies here

## Amendment — 2026-05-19 (v0.3.0)

Empirical correction: the binary A/B distinction was too coarse. A third class exists, call it **Class A-hybrid**: triggers detectable via **aggregated tool-layer state**, not just single tool inputs.

The decision-log gap is the exemplar. The trigger ("agent is making silent decisions and should log them") isn't tool-input-detectable on any single call. But it IS detectable by tracking state across calls: a counter of writes/edits since the last `autopilot:decision-log` Skill invocation. When that counter crosses a threshold, the hook injects an `additionalContext` nudge — same mechanism, different signal.

Empirical: fixture 09 went from 0 invocations across all prior baselines to 3/3 invocations with composite 100/100/100 after the state-tracked nudge landed.

**Revised classification:**

- **Class A (single-tool-input detectable):** `budget_tick`, `irreversibility` for `git commit/push`, `external_effect` for known endpoints, `scope_drift` via path patterns.
- **Class A-hybrid (aggregated-state detectable):** `decision-log` (state: writes since last skill invocation). Future candidates: "agent has been Reading without Editing for N calls → probably needs to ask before the next non-trivial change."
- **Class B (brief-content only, no state signal):** `architectural_choice`, `ambiguity`. These remain skill-text-only and bimodal.

The decision rule for new triggers stays the same — Class A and Class A-hybrid both get mechanism nudges; Class B accepts skill-text limits.
