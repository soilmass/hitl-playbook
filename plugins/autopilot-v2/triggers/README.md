# triggers/ — single source of truth

Every yellow-tier trigger is defined in one JSON file here. Both `hooks/guard.mjs` (for tool-layer detection) and `skills/autopilot/SKILL.md` (for the model-facing decision tree) are derived from this directory. They cannot drift because they're projections of the same source.

## Schema (per trigger)

Authoritative schema: [`$schema.json`](./$schema.json). It is enforced at load
time by `hooks/lib/triggers.mjs` — any file in this directory that violates it
fails the roundtrip test and never reaches the hook. `additionalProperties` is
`false` so a misspelled field (e.g. a stale namespace string) is rejected
rather than silently ignored.

Common envelope (every trigger):

```json
{
  "id": "kebab-case-id",
  "class": "A" | "A-hybrid",
  "description": "one-line summary for SKILL.md generation",
  "detection": { "type": "...", "...": "..." },
  "action": "nudge" | "block",
  "checkpoint_template_id": "<template-id>" | null,
  "advisory_text": "Text shown to the agent via additionalContext when triggered.",
  "fixture_id": "02-irreversibility"
}
```

`detection` is polymorphic on `type` (the schema uses `oneOf`); fields from
different branches MUST NOT be mixed:

`bash_pattern` — regex match over Bash command input:

```json
{ "type": "bash_pattern", "tools": ["Bash"], "patterns": ["regex1", "regex2"] }
```

`state_counter` — per-session counter over the listed tools; requires exactly
one of `threshold` (single tier) or `thresholds` (two-tier yellow/red):

```json
{ "type": "state_counter", "tools": ["Edit"], "counter": "writes-since-dlog",
  "threshold": 3, "threshold_env_override": "AUTOPILOT_DLOG_THRESHOLD",
  "reset_on": { "tool": "Skill", "skill_substring": "..." } }
```

```json
{ "type": "state_counter", "tools": ["*"], "counter": "tool-calls",
  "thresholds": { "yellow": 50, "red": 150 } }
```

See `$schema.json` for the full contract.

## Per-class detection contract

- **`A` (tool-layer detectable)**: `detection.type` is `bash_pattern` (regex over Bash command input) or `external_effect` (matcher over tool name + input shape). Fires deterministically in PreToolUse.
- **`A-hybrid` (state-tracked)**: `detection.type` is `state_counter` (e.g. writes-since-last-skill-invocation). Hook maintains per-session counter file; threshold trips the nudge.

Class B (brief-content-only) triggers are explicitly excluded from v2. They become items the agent must enumerate in the handback `Assumed:` section, not enforcement points. See [`../../docs/design/autopilot-v2.md`](../../docs/design/autopilot-v2.md) section "Skill-text-only triggers are a tax, not a feature."

## Adding a trigger

1. Write `triggers/NN-<id>.json`.
2. Add a fixture under `../../evals-v2/fixtures/`.
3. Run `node tools/gen-skill.mjs` to regenerate `skills/autopilot/SKILL.md`.
4. Run `bash test/triggers-roundtrip.sh` — the gate that confirms registry, generated skill, and hook regex all parse and agree.
5. Run `python3 ../../evals-v2/auditor.py` on the diff.

A trigger that fails any step doesn't ship. The roundtrip test exists precisely because v1 had skill-text vs hook-regex drift.
