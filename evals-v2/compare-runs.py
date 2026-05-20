#!/usr/bin/env python3
"""
Diff two autopilot eval results JSON files.

v2 (per ADR-0017 PR-5): per-criterion paired bootstrap CI on Δp̂.
Regression flagged iff CI(Δp̂) excludes 0 AND |Δp̂| ≥ 0.15 (effect-size
floor; replaces the 5-point composite rule).

Usage:
  python3 evals/compare-runs.py <baseline.json> <candidate.json>
  python3 evals/compare-runs.py --latest             # diff two newest
  python3 evals/compare-runs.py --schema v1          # legacy 5-point rule
  python3 evals/compare-runs.py --schema v2          # per-criterion CI (default)

Exit 0 if no per-criterion regression. Exit 1 if any criterion's
Δp̂ CI excludes 0 AND |Δ| ≥ 0.15.
"""

import argparse
import json
import sys
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scorer.stats import paired_bootstrap_delta, variance_flag, wilson_ci  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "evals-v2" / "results"


# ============================================================================
# v2: per-criterion bootstrap CI
# ============================================================================

def collect_criteria(result: dict) -> dict:
    """
    Reshape result JSON into: {fixture_id: {criterion_id: [(passed, skipped) per run]}}.
    Only includes fixtures+criteria present in this result.
    """
    out: dict[str, dict[str, list[tuple[bool, bool]]]] = {}
    for fid, runs in result.get("tasks", {}).items():
        per_crit: dict[str, list[tuple[bool, bool]]] = {}
        for r in runs:
            c2 = r.get("criteria_v2", {})
            for cid, info in c2.items():
                per_crit.setdefault(cid, []).append(
                    (bool(info.get("passed")), bool(info.get("skipped")))
                )
        if per_crit:
            out[fid] = per_crit
    return out


def _applicable_passes(records: list[tuple[bool, bool]]) -> list[bool]:
    """Extract pass-rate booleans excluding skipped runs."""
    return [p for (p, sk) in records if not sk]


def _skipped_count(records: list[tuple[bool, bool]]) -> int:
    return sum(1 for (_, sk) in records if sk)


def diff_v2(baseline: dict, candidate: dict) -> int:
    b_crit = collect_criteria(baseline)
    c_crit = collect_criteria(candidate)

    print(f"\n{baseline.get('version','?'):30s}  ({baseline.get('model','?')})")
    print("vs")
    print(f"{candidate.get('version','?'):30s}  ({candidate.get('model','?')})")
    print("regression rule: per-criterion CI(Δp̂) excludes 0 AND |Δp̂| ≥ 0.15")
    print()

    all_fixtures = sorted(set(b_crit) | set(c_crit))
    any_regress = False
    target_failure_counts: dict[str, int] = {}

    for fid in all_fixtures:
        b_run = b_crit.get(fid, {})
        c_run = c_crit.get(fid, {})
        all_crit = sorted(set(b_run) | set(c_run))
        if not all_crit:
            continue
        print(f"\n  {fid}")
        for cid in all_crit:
            b_records = b_run.get(cid, [])
            c_records = c_run.get(cid, [])
            b_runs = _applicable_passes(b_records)
            c_runs = _applicable_passes(c_records)
            b_skipped = _skipped_count(b_records)
            c_skipped = _skipped_count(c_records)
            b_rate = sum(b_runs) / len(b_runs) if b_runs else None
            c_rate = sum(c_runs) / len(c_runs) if c_runs else None
            # If both sides are entirely skipped, the criterion isn't
            # discriminating in this comparison; show 'n/a' instead of
            # forcing a 0=0 stable verdict.
            if not b_runs and not c_runs:
                print(f"    · {cid:<42}   n/a (skipped both sides: {b_skipped}/{c_skipped})")
                continue
            boot = paired_bootstrap_delta(b_runs, c_runs)
            verdict = "stable"
            mark = "·"
            if boot["regressed"]:
                verdict = f"REGRESSION  delta={boot['delta']:+.2f}  CI=[{boot['ci_low']:+.2f},{boot['ci_high']:+.2f}]"
                mark = "✗"
                any_regress = True
            elif b_rate is not None and c_rate is not None and (c_rate - b_rate) >= 0.15 and boot["ci_low"] > 0:
                verdict = f"IMPROVEMENT  delta={boot['delta']:+.2f}  CI=[{boot['ci_low']:+.2f},{boot['ci_high']:+.2f}]"
                mark = "✓"
            else:
                verdict = f"stable       delta={boot['delta']:+.2f}  CI=[{boot['ci_low']:+.2f},{boot['ci_high']:+.2f}]"
            v_b = variance_flag(b_runs)
            v_c = variance_flag(c_runs)
            noisy = "  ⚠NOISY" if (v_b["noisy"] or v_c["noisy"]) else ""
            br = f"{b_rate:.2f}" if b_rate is not None else " - "
            cr = f"{c_rate:.2f}" if c_rate is not None else " - "
            skip = ""
            if b_skipped or c_skipped:
                skip = f"  (skipped {b_skipped}/{c_skipped})"
            print(f"    {mark} {cid:<42}  {br}→{cr}  {verdict}{noisy}{skip}")
            if boot["regressed"]:
                # Find target_artifact in the candidate transcript
                for tid_runs in candidate.get("tasks", {}).get(fid, []):
                    info = (tid_runs.get("criteria_v2") or {}).get(cid)
                    if info:
                        tgt = info.get("target_artifact", "unknown")
                        target_failure_counts[tgt] = target_failure_counts.get(tgt, 0) + 1
                        break

    if target_failure_counts:
        print("\n  Regression target_artifacts (open these files first):")
        for tgt, count in sorted(target_failure_counts.items(), key=lambda x: -x[1]):
            print(f"    {count}x  {tgt}")

    b_cost = baseline.get("total_cost_usd", 0)
    c_cost = candidate.get("total_cost_usd", 0)
    print(f"\nCost: baseline ${b_cost:.4f}  candidate ${c_cost:.4f}")

    return 1 if any_regress else 0


# ============================================================================
# v1: legacy 5-point composite rule (preserved for back-compat)
# ============================================================================

def task_means(result: dict) -> dict:
    out = {}
    for task_id, runs in result.get("tasks", {}).items():
        valid = [r for r in runs if r.get("composite") is not None]
        if not valid:
            out[task_id] = None
            continue
        out[task_id] = {
            "composite": mean(r["composite"] for r in valid),
            "appropriate_ask": mean(r["appropriate_ask_rate"] for r in valid),
            "false_block": mean(r["false_block_rate"] for r in valid),
            "silent_decision": mean(r["silent_decision_rate"] for r in valid),
            "handback": mean(r["handback_completeness"] for r in valid),
            "asks": mean(r.get("asks", 0) for r in valid),
            "tools": mean(r.get("tools", 0) for r in valid),
            "cost_usd": sum(r.get("cost_usd", 0) for r in valid) / len(valid),
            "n": len(valid),
        }
    return out


def diff_v1(baseline: dict, candidate: dict, threshold: float) -> int:
    b_means = task_means(baseline)
    c_means = task_means(candidate)
    all_tasks = sorted(set(b_means) | set(c_means))

    print(f"\n{baseline.get('version','?'):30s}  ({baseline.get('model','?')})")
    print("vs")
    print(f"{candidate.get('version','?'):30s}  ({candidate.get('model','?')})")
    print(f"v1 regression threshold: {threshold} composite points\n")
    print(f"{'task':<28} {'baseline':>10} {'candidate':>10} {'delta':>8}   verdict")
    print("-" * 72)
    regressed = False
    for task in all_tasks:
        b = b_means.get(task)
        c = c_means.get(task)
        if b is None or c is None:
            bs = "-" if b is None else f"{b['composite']:.1f}"
            cs = "-" if c is None else f"{c['composite']:.1f}"
            print(f"{task:<28} {bs:>10} {cs:>10} {'?':>8}   skipped")
            continue
        delta = c["composite"] - b["composite"]
        if delta < -threshold:
            verdict = f"REGRESSION ({delta:+.1f})"
            regressed = True
        elif delta > threshold:
            verdict = f"improvement ({delta:+.1f})"
        else:
            verdict = "stable"
        print(f"{task:<28} {b['composite']:>10.1f} {c['composite']:>10.1f} {delta:>+8.1f}   {verdict}")
    b_overall = mean(v["composite"] for v in b_means.values() if v)
    c_overall = mean(v["composite"] for v in c_means.values() if v)
    delta = c_overall - b_overall
    print("-" * 72)
    print(f"{'OVERALL':<28} {b_overall:>10.1f} {c_overall:>10.1f} {delta:>+8.1f}")
    return 1 if regressed else 0


# ============================================================================
# CLI
# ============================================================================

def find_latest_two() -> tuple:
    files = sorted(RESULTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if len(files) < 2:
        sys.exit("need at least 2 result files in evals/results/")
    return files[1], files[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("baseline", nargs="?")
    ap.add_argument("candidate", nargs="?")
    ap.add_argument("--latest", action="store_true")
    ap.add_argument("--schema", choices=["v1", "v2"], default="v2",
                    help="v2: per-criterion bootstrap CI (default); v1: legacy 5-point composite rule")
    ap.add_argument("--threshold", type=float, default=5.0,
                    help="v1 only: composite-point regression threshold")
    args = ap.parse_args()

    if args.latest:
        baseline_path, candidate_path = find_latest_two()
    elif args.baseline and args.candidate:
        baseline_path, candidate_path = Path(args.baseline), Path(args.candidate)
    else:
        ap.error("provide both baseline and candidate, or --latest")

    print(f"baseline:  {baseline_path.name}")
    print(f"candidate: {candidate_path.name}")
    baseline = json.loads(baseline_path.read_text())
    candidate = json.loads(candidate_path.read_text())

    if args.schema == "v2":
        sys.exit(diff_v2(baseline, candidate))
    else:
        sys.exit(diff_v1(baseline, candidate, args.threshold))


if __name__ == "__main__":
    main()
