# autopilot-v2 eval harness

Companion to `plugins/autopilot-v2/`. Per ADR-0018, this harness drops the
v1 compatibility layer and ships only what the methodology actually requires.

## What's different from `../evals/`

| Aspect | v1 (`evals/`) | v2 (`evals-v2/`) |
|---|---|---|
| Schema | v2 schema + legacy v1 keys allowed | v2 schema only |
| `--runs` default | 3 | **required, no default** |
| Underrun behavior | writes partial results with markers | **refuses to write the file** |
| Default plugin | `plugins/autopilot` | `plugins/autopilot-v2` |
| Criteria author tracking | informal (CONTRIBUTING note) | **structural (`criteria_author` field in fixture YAML)** |
| Auditor | `evals/audit.py` (workflow step 5) | `evals-v2/auditor.py` (must run on every PR — see plugin README) |
| Class B fixtures | 3 included (02, 03, 06) | **0 — Class B is structurally rejected** |
| Judge calibration | exists but unused (PR-7 blocked) | not present; structural criteria only |

## Fixtures

7 maximum (one per Class A / A-hybrid trigger), down from 10 in v1.
The dropped fixtures (02-scope-drift, 03-architectural-fork, 06-ambiguity)
were Class B and their function is now subsumed by the handback
`Assumed:` discipline per ADR-0018.

Currently shipped:
- `01-pure-green` — over-asking detection
- `02-irreversibility` — Class A bash-pattern trigger
- `03-decision-log` — Class A-hybrid state_counter trigger

To follow (v2-followup):
- `04-budget-tick` — Class A-hybrid state_counter (budget threshold)
- `05-external-effect` — Class A, external-effect detection
- `06-verifier-trigger` — verifier subagent invocation
- `07-verifier-catches-bug` — verifier + SQL injection trap

## Running

```bash
# v2 requires explicit --runs; refuses if any fixture under-runs.
python3 evals-v2/run.py --version baseline --runs 5 --model sonnet --max-budget-usd 0.30

# Filter to a single fixture by prefix (anchored, no v1 footgun).
python3 evals-v2/run.py --version smoke --runs 5 --model sonnet --filter 02

# Independent audit on the staged diff (recommended before every commit).
python3 evals-v2/auditor.py
```

## v2 acceptance for the canonical baseline

A v2 baseline file (`results/v2-canonical-*.json`) is canonical iff:

1. `bash plugins/autopilot-v2/test/triggers-roundtrip.sh` passed before the run.
2. No fixture in the suite recorded `UNDERRUN_SKIPPED`.
3. Every fixture's `min_runs` is met.
4. `auditor.py` PASS on the plugin diff that produced it.
5. Aggregate per-criterion pass-rate equals or beats v1's published **94.7** at equal-or-stricter n.

If any of those fail, the baseline is provisional. Don't publish it as v1's successor.
