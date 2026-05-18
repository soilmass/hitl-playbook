#!/usr/bin/env python3
"""
Diff two autopilot eval results JSON files. Prints a per-task table
showing how each metric moved, plus a regression verdict.

Usage:
  python3 evals/compare-runs.py <baseline.json> <candidate.json>
  python3 evals/compare-runs.py --latest       # diff the two newest

Exit 0 if no metric regresses by more than --threshold (default 5 points).
Exit 1 if any does. Useful as a pre-merge gate.
"""

import argparse
import json
import sys
from pathlib import Path
from statistics import mean

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "evals" / "results"


def task_means(result: dict) -> dict:
    """Per-task mean of each metric across all runs in one result file."""
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


def diff_table(baseline: dict, candidate: dict, threshold: float) -> int:
    """Print the diff, return exit code (0 ok, 1 regression)."""
    b_means = task_means(baseline)
    c_means = task_means(candidate)
    all_tasks = sorted(set(b_means) | set(c_means))

    print(f"\n{baseline.get('version','?'):30s}  ({baseline.get('model','?')})")
    print(f"vs")
    print(f"{candidate.get('version','?'):30s}  ({candidate.get('model','?')})")
    print(f"regression threshold: {threshold} composite points\n")

    print(f"{'task':<28} {'baseline':>10} {'candidate':>10} {'delta':>8}   verdict")
    print("-" * 72)
    regressed = False
    for task in all_tasks:
        b = b_means.get(task)
        c = c_means.get(task)
        if b is None or c is None:
            bs = "-" if b is None else f"{b['composite']:.1f}"
            cs = "-" if c is None else f"{c['composite']:.1f}"
            print(f"{task:<28} {bs:>10} {cs:>10} {'?':>8}   skipped (missing in one)")
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

    # Aggregate
    b_overall = mean(v["composite"] for v in b_means.values() if v)
    c_overall = mean(v["composite"] for v in c_means.values() if v)
    delta = c_overall - b_overall
    print("-" * 72)
    print(f"{'OVERALL':<28} {b_overall:>10.1f} {c_overall:>10.1f} {delta:>+8.1f}")

    # Per-metric breakdown for changed tasks
    print()
    for task in all_tasks:
        b = b_means.get(task); c = c_means.get(task)
        if not b or not c: continue
        if abs(c["composite"] - b["composite"]) < 1: continue
        print(f"  {task} detail:")
        for m in ("appropriate_ask", "false_block", "silent_decision", "handback", "asks", "tools"):
            bv, cv = b[m], c[m]
            d = cv - bv
            if abs(d) > 0.01:
                print(f"    {m:<22} {bv:>8.3f} -> {cv:>8.3f}  ({d:+.3f})")

    # Cost report
    b_cost = baseline.get("total_cost_usd", 0)
    c_cost = candidate.get("total_cost_usd", 0)
    print(f"\nCost: baseline ${b_cost:.4f}  candidate ${c_cost:.4f}")

    return 1 if regressed else 0


def find_latest_two() -> tuple:
    files = sorted(RESULTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if len(files) < 2:
        sys.exit("need at least 2 result files in evals/results/")
    return files[1], files[0]  # baseline = older, candidate = newer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("baseline", nargs="?", help="baseline results JSON")
    ap.add_argument("candidate", nargs="?", help="candidate results JSON")
    ap.add_argument("--latest", action="store_true", help="diff the two newest result files")
    ap.add_argument("--threshold", type=float, default=5.0, help="composite-point regression threshold")
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
    sys.exit(diff_table(baseline, candidate, args.threshold))


if __name__ == "__main__":
    main()
