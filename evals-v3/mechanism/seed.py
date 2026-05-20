#!/usr/bin/env python3
"""
Seed cached transcripts for v3 mechanism-track replay.

Why this exists (and not just `run.py --keep`): run.py emits the SCORED
shape (asks count, tool_summary preview) to results/, not the FULL
transcript shape that scorer.criteria.score_v2 consumes. The mechanism
track needs the full transcript so replay.py can re-score offline.

Usage:
    python3 evals-v3/mechanism/seed.py [--filter 01,02] [--model haiku]

Cost: ~$0.10 per fixture on haiku. Default seeds all 7 (~$0.70).

Per-fixture output: evals-v3/mechanism/cached-transcripts/<id>-canonical.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = Path(__file__).resolve().parent / "cached-transcripts"
FIXTURES_DIR = REPO_ROOT / "evals-v2" / "fixtures"

# Reuse v2 runner internals — single source of truth for the driver.
sys.path.insert(0, str(REPO_ROOT / "evals-v2"))
from run import _run_claude_task, _setup_workspace, FixtureSetupError  # noqa: E402


def seed_one(fixture_path: Path, model: str, max_budget_usd: float) -> dict:
    fixture = yaml.safe_load(fixture_path.read_text())
    plugin_root = REPO_ROOT / "plugins" / "autopilot-v2"
    work = _setup_workspace(fixture)
    try:
        transcript = _run_claude_task(
            fixture["brief"], plugin_root,
            model=model, max_budget_usd=max_budget_usd,
            extra_setup_dir=work,
            allowed_tools=fixture.get("allowed_tools"),
            fixture_env=fixture.get("env"),
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)
    # Drop work_dir — it's tmpdir-specific and not load-bearing for scoring.
    transcript.pop("work_dir", None)
    return transcript


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--filter", help="comma-separated id prefixes (e.g. '01,02')")
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--max-budget-usd", type=float, default=0.20)
    args = ap.parse_args()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tokens = [t.strip() for t in (args.filter or "").split(",") if t.strip()]

    fixtures = sorted(FIXTURES_DIR.glob("*.yaml"))
    if tokens:
        fixtures = [
            f for f in fixtures
            if any(f.name.startswith(f"{t.zfill(2)}-") for t in tokens if t.isdigit())
        ]

    if not fixtures:
        sys.exit("seed: no fixtures matched filter")

    for fp in fixtures:
        fid = yaml.safe_load(fp.read_text())["id"]
        print(f"\nseeding {fid} ...")
        try:
            transcript = seed_one(fp, args.model, args.max_budget_usd)
        except FixtureSetupError as e:
            print(f"  SETUP_FAILED: {e}")
            continue
        out = CACHE_DIR / f"{fid}-canonical.json"
        out.write_text(json.dumps(transcript, indent=2))
        print(f"  wrote {out.relative_to(REPO_ROOT)}  "
              f"(asks={len(transcript['ask_user_questions'])} "
              f"tools={len(transcript['tool_calls'])} "
              f"cost=${transcript['cost_usd']:.4f})")


if __name__ == "__main__":
    main()
