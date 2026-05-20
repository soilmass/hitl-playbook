# triggers/ — single source of truth

Every yellow-tier trigger is defined in one JSON file here. Both `hooks/guard.mjs` (for tool-layer detection) and `skills/autopilot/SKILL.md` (for the model-facing decision tree) are derived from this directory. They cannot drift because they're projections of the same source.

## Schema (per trigger)

```json
{
  "id": "kebab-case-id",
  "class": "A" | "A-hybrid",
  "description": "one-line summary for SKILL.md generation",
  "detection": {
    "type": "bash_pattern" | "state_counter" | "external_effect",
    "patterns": ["regex1", "regex2"],
    "tools": ["Bash", "Edit"],
    "threshold": 3
  },
  "action": "nudge" | "block",
  "checkpoint_template_id": "irreversible" | "external" | "decision-log",
  "advisory_text": "Text shown to the agent via additionalContext when triggered.",
  "fixture_id": "02-irreversibility"
}
```

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
