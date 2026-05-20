# evals-v3 — two-track evaluation methodology

v2's canonical baseline (commit `2a3566a`) cost **$5.14 and ran 25 minutes**
for 7 fixtures × 5 runs on haiku. PR-time gating on a $5 live-model run is
infeasible, so v3 splits the eval into two tracks.

## Tracks

| Track | When it runs | Cost | Nature | What it catches |
|-------|--------------|------|--------|------------------|
| **Mechanism** | Every PR | $0 | Deterministic replay of pinned transcripts through the live scorer | Regressions in `scorer/criteria.py` handlers, fixture criteria edits, architectural-invariant breaks (`triggers-roundtrip`, `scorer-sync`) |
| **Behavior** | Weekly + before tagging a release | ~$5+ | Live `claude --print` calls, full canonical baseline (`evals-v2/run.py --runs 5 ...`) | Model behavior drift, plugin/hook real-world interactions, trigger-firing on real model output |

The mechanism track is a **PR-blocking** check. The behavior track is
periodic and treated as a metric, not a gate.

## What this catches — and what it does NOT

The mechanism track replays a frozen snapshot of model output. It catches:

- A scorer change that silently flips pass→fail on a known transcript.
- A fixture criterion edit (added/removed/changed substring) that wasn't
  intended.
- Drift between `evals/scorer/` and `evals-v2/scorer/` (via
  `scorer-sync.sh`).
- Trigger registry breakage (via `triggers-roundtrip.sh`).

It does NOT catch:

- The model behaving differently to the same prompt (that's the behavior
  track).
- Real plugin/hook interactions — the cached transcript already has the
  hook decisions baked in.
- A new fixture (you must seed and snapshot it explicitly).

## How to run

```bash
python3 evals-v3/mechanism/replay.py
```

Exits 0 iff every cached transcript re-scores identically to
`snapshot-pass-rates.json` AND both architectural-invariant tests pass.

CI runs this on every PR via `.github/workflows/v3-mechanism.yml`.

## Snapshots

`snapshot-pass-rates.json` pins `{passed, skipped}` per `(fixture,
criterion)`. Detail dicts (block kinds, ask counts, etc.) are intentionally
NOT in the snapshot — they contain tmpdir paths and other run-specific
noise that would force snapshot churn on every reseed.

### When to update the snapshot

After a **deliberate** change to:
- `evals-v2/scorer/criteria.py` (handler logic)
- `evals-v2/fixtures/*.yaml` (criteria additions/edits)

Update with:

```bash
python3 evals-v3/mechanism/replay.py --update-snapshot
```

Include the snapshot diff in your PR so a reviewer can confirm the
behavior change is intentional.

## Re-seeding cached transcripts

Cached transcripts age — when the plugin or skills change materially, the
old transcript no longer represents current behavior. Re-seed with:

```bash
python3 evals-v3/mechanism/seed.py [--filter 01,02] [--model haiku]
```

Cost: ~$0.10 per fixture (haiku, n=1). Default seeds all 7 (~$0.70).

After reseeding, re-run replay and confirm the resulting snapshot diff
matches what you expected from the plugin change. Then commit transcripts
and snapshot together.

## Files

```
evals-v3/
  README.md                          (this file)
  mechanism/
    replay.py                        re-score + arch tests; PR gate
    seed.py                          generate fresh cached transcripts
    snapshot-pass-rates.json         pinned pass/skipped per criterion
    cached-transcripts/
      01-pure-green-canonical.json   one per fixture
      02-irreversibility-canonical.json
      ...
```
