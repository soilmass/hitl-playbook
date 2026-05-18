# Postmortems

Append-only record of autopilot runs that shipped a bad change or were rolled back.

## Why this exists

[Component 7](../hitl-framework.md#7-failure-recovery-and-postmortem) of the HITL framework: every failure that survives the guardrails should produce a concrete follow-up — a new categorical trigger, a new red-tier pattern, a new subagent check, or an ADR superseding an existing decision. Without postmortems, the same failure ships twice.

## Index

| Date | Slug | Category | Follow-up |
|---|---|---|---|

*(Newest on top. Add an entry per postmortem. Categories: A=plugin under-gated, B=plugin over-gated, C=user judgment, D=model failure.)*

## How to write one

1. Copy [`TEMPLATE.md`](./TEMPLATE.md) to `YYYY-MM-DD-<slug>.md` (slug = 2–4 hyphenated words).
2. Fill it out in ≤15 minutes. Terse is fine.
3. Update the index above with the new entry.
4. If the follow-up requires plugin changes (new trigger, new regex, new subagent), implement them — the postmortem is incomplete until the follow-up ships.
5. If the follow-up is a new ADR, write it under `../adr/` and reference it in the postmortem.

## When to write one

Trigger: any autopilot run whose change was reverted, hot-patched, or caused user-visible breakage. Or a near-miss the user caught at review time that would have shipped otherwise.

Skip: normal yellow-tier checkpoint redirects (the system worked), tasks the user simply changed their mind on (not a failure).
