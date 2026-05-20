#!/usr/bin/env python3
"""
Mechanism-track replay: re-score pinned transcripts against the live v2
scorer. Catches regressions in scorer logic, criteria handlers, or
fixture criteria sets — cheaply, deterministically, every PR.

This DOES NOT exercise the live model. For model-behavior drift see the
behavior track (weekly `evals-v2/run.py` canonical baseline).

Usage:
    python3 evals-v3/mechanism/replay.py              # exit 0 iff match
    python3 evals-v3/mechanism/replay.py --update-snapshot

Inputs:
    evals-v2/fixtures/*.yaml
    evals-v3/mechanism/cached-transcripts/<id>-canonical.json
    evals-v3/mechanism/snapshot-pass-rates.json

Exit codes:
    0 — replay matches snapshot AND architectural tests pass
    1 — replay diverges from snapshot, OR architectural tests fail
    2 — invocation error (missing cache, missing fixture)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = Path(__file__).resolve().parent / "cached-transcripts"
FIXTURES_DIR = REPO_ROOT / "evals-v2" / "fixtures"
SNAPSHOT_PATH = Path(__file__).resolve().parent / "snapshot-pass-rates.json"

sys.path.insert(0, str(REPO_ROOT / "evals-v2"))
from scorer import criteria as crit_v2  # noqa: E402


def _score_all() -> dict:
    """Return {fixture_id: {criterion_id: {passed, skipped}, ...}} for every cached transcript."""
    out: dict = {}
    fixtures_by_id = {
        yaml.safe_load(fp.read_text())["id"]: fp
        for fp in FIXTURES_DIR.glob("*.yaml")
    }
    for cache_path in sorted(CACHE_DIR.glob("*-canonical.json")):
        fid = cache_path.stem.removesuffix("-canonical")
        if fid not in fixtures_by_id:
            sys.exit(f"replay: cached transcript {cache_path.name} has no matching fixture")
        fixture = yaml.safe_load(fixtures_by_id[fid].read_text())
        transcript = json.loads(cache_path.read_text())
        scored = crit_v2.score_v2(fixture, transcript)
        # Snapshot only pass/skipped — detail dicts include tmpdir paths and
        # other run-specific noise that would force snapshot churn on every
        # re-seed. The pass/skipped pair is the contract.
        out[fid] = {
            cid: {"passed": bool(r["passed"]), "skipped": bool(r.get("skipped"))}
            for cid, r in scored.items()
        }
    return out


def _diff(current: dict, snapshot: dict) -> list[str]:
    msgs = []
    cur_ids = set(current)
    snap_ids = set(snapshot)
    for fid in sorted(cur_ids - snap_ids):
        msgs.append(f"+ fixture {fid}: present in replay, missing from snapshot")
    for fid in sorted(snap_ids - cur_ids):
        msgs.append(f"- fixture {fid}: in snapshot but no cached transcript replayed")
    for fid in sorted(cur_ids & snap_ids):
        cur = current[fid]
        snap = snapshot[fid]
        cur_crits = set(cur)
        snap_crits = set(snap)
        for cid in sorted(cur_crits - snap_crits):
            msgs.append(f"  {fid}: + criterion {cid} new in replay")
        for cid in sorted(snap_crits - cur_crits):
            msgs.append(f"  {fid}: - criterion {cid} missing from replay")
        for cid in sorted(cur_crits & snap_crits):
            if cur[cid] != snap[cid]:
                msgs.append(
                    f"  {fid}.{cid}: replay={cur[cid]} vs snapshot={snap[cid]}"
                )
    return msgs


def _run_arch_tests() -> bool:
    """Run the two architectural-invariant tests. Return True iff both pass."""
    tests = [
        REPO_ROOT / "plugins" / "autopilot-v2" / "test" / "triggers-roundtrip.sh",
        REPO_ROOT / "evals-v2" / "test" / "scorer-sync.sh",
    ]
    ok = True
    for t in tests:
        sys.stdout.flush()
        result = subprocess.run(["bash", str(t)], cwd=REPO_ROOT)
        if result.returncode != 0:
            print(f"  FAIL: {t.name} exited {result.returncode}")
            ok = False
    return ok


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument(
        "--update-snapshot", action="store_true",
        help="rewrite snapshot-pass-rates.json from the current replay "
             "(use after a deliberate scorer or fixture change)",
    )
    args = ap.parse_args()

    if not list(CACHE_DIR.glob("*-canonical.json")):
        sys.exit(
            f"replay: no cached transcripts in {CACHE_DIR.relative_to(REPO_ROOT)}. "
            "Run `python3 evals-v3/mechanism/seed.py` first."
        )

    current = _score_all()
    fixture_count = len(current)
    total_crits = sum(len(c) for c in current.values())
    print(f"replay: re-scored {fixture_count} fixture(s), {total_crits} criteria", flush=True)

    if args.update_snapshot:
        SNAPSHOT_PATH.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n")
        print(f"replay: wrote snapshot {SNAPSHOT_PATH.relative_to(REPO_ROOT)}")
        sys.exit(0)

    if not SNAPSHOT_PATH.exists():
        sys.exit(
            f"replay: no snapshot at {SNAPSHOT_PATH.relative_to(REPO_ROOT)}. "
            "Run with --update-snapshot to create one."
        )

    snapshot = json.loads(SNAPSHOT_PATH.read_text())
    diffs = _diff(current, snapshot)
    if diffs:
        print("\nreplay: SNAPSHOT MISMATCH")
        for m in diffs:
            print(m)
        print("\nIf the change is intentional, re-run with --update-snapshot.")
        sys.exit(1)
    print("replay: snapshot match.", flush=True)

    if not _run_arch_tests():
        sys.exit(1)
    print("\nmechanism-track PASS")


if __name__ == "__main__":
    main()
