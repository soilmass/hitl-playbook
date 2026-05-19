#!/usr/bin/env python3
"""
Interactive labeling CLI for PR-6 judge calibration (per ADR-0017).

Walks past results JSON files, presents each (brief, handback, tool_summary)
to the user, prompts for a binary y/n/skip label, appends to
labels/<rubric>.jsonl. Aim for ≥20 labels with class balance before
calibrating.

Usage:
  python3 evals/judge/label.py --rubric handback_done_quality_v1
  python3 evals/judge/label.py --rubric handback_done_quality_v1 --filter 02

Resumes where you left off (won't re-prompt already-labeled
(results_file, fixture, run_idx) tuples).
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = REPO_ROOT / "evals" / "results"
JUDGE_DIR = REPO_ROOT / "evals" / "judge"


def already_labeled(labels_path: Path) -> set[tuple[str, str, int]]:
    """Return set of (results_basename, fixture_id, run_idx) already labeled."""
    if not labels_path.exists():
        return set()
    seen = set()
    for line in labels_path.read_text().splitlines():
        if not line.strip(): continue
        try:
            rec = json.loads(line)
            seen.add((rec["results_file"], rec["fixture"], rec["run_idx"]))
        except Exception:
            continue
    return seen


def iter_runs(filter_substr: str = None):
    """Iterate (results_file, fixture_id, run_idx, brief, handback, tool_summary)
    across all results JSON in evals/results/, newest first."""
    files = sorted(RESULTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for fp in files:
        try:
            d = json.loads(fp.read_text())
        except Exception:
            continue
        for fid, runs in d.get("tasks", {}).items():
            if filter_substr and filter_substr not in fid:
                continue
            for i, r in enumerate(runs):
                handback = r.get("final_message", "")
                if not handback:
                    continue
                # Need the brief — pull from the fixture YAML
                fixture_path = REPO_ROOT / "evals" / "tasks" / f"{fid}.yaml"
                brief = "<unknown brief>"
                if fixture_path.exists():
                    try:
                        import yaml
                        brief = yaml.safe_load(fixture_path.read_text()).get("brief", "<no brief>")
                    except Exception:
                        pass
                yield (fp.name, fid, i, brief.strip(), handback, r.get("tool_summary", []))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rubric", required=True,
                    help="rubric ID — must have a matching evals/judge/rubrics/<id>.md file")
    ap.add_argument("--filter", help="only label runs for fixtures matching this substring")
    ap.add_argument("--max", type=int, default=30, help="stop after this many labels")
    args = ap.parse_args()

    rubric_path = JUDGE_DIR / "rubrics" / f"{args.rubric}.md"
    labels_path = JUDGE_DIR / "labels" / f"{args.rubric}.jsonl"
    labels_path.parent.mkdir(parents=True, exist_ok=True)

    if not rubric_path.exists():
        sys.exit(f"rubric not found: {rubric_path}")

    rubric_text = rubric_path.read_text()
    seen = already_labeled(labels_path)
    print(f"Rubric: {args.rubric}")
    print(f"Existing labels: {len(seen)}")
    print(f"Output: {labels_path}")
    print()
    print("=" * 80)
    print(rubric_text[:1500])  # show the rubric (first 1500 chars)
    print("=" * 80)
    print()
    print("Commands: y=pass | n=fail | s=skip | q=quit | r=re-print rubric")
    print()

    labeled_this_session = 0
    for results_file, fid, run_idx, brief, handback, tool_summary in iter_runs(args.filter):
        if (results_file, fid, run_idx) in seen:
            continue
        if labeled_this_session >= args.max:
            print(f"\nReached --max {args.max} labels. Stop.")
            break

        print(f"\n--- {results_file}  {fid}  run {run_idx + 1} ---")
        print(f"BRIEF: {brief[:200]}")
        print()
        print("HANDBACK:")
        print(handback[:2000])
        if tool_summary:
            print()
            print(f"TOOL SUMMARY ({len(tool_summary)} calls):")
            for t in tool_summary[:10]:
                print(f"  {t['tool']:20s} {t['input_preview'][:60]}")
        print()
        while True:
            ans = input("label [y/n/s/q/r]: ").strip().lower()
            if ans == "q":
                print(f"\nLabeled {labeled_this_session} this session. Bye.")
                return
            if ans == "r":
                print(rubric_text[:1500])
                continue
            if ans in ("y", "n", "s"):
                break
            print("invalid; try y/n/s/q/r")
        if ans == "s":
            continue
        notes = input("optional notes (Enter to skip): ").strip()
        rec = {
            "results_file": results_file,
            "fixture": fid,
            "run_idx": run_idx,
            "human_label": "yes" if ans == "y" else "no",
            "notes": notes,
            "brief_excerpt": brief[:200],
            "handback_excerpt": handback[:500],
        }
        with labels_path.open("a") as f:
            f.write(json.dumps(rec) + "\n")
        labeled_this_session += 1
        print(f"  → saved ({labeled_this_session} this session, {len(seen) + labeled_this_session} total)")

    print(f"\nLabeled {labeled_this_session} this session. {len(seen) + labeled_this_session} total in {labels_path.name}.")


if __name__ == "__main__":
    main()
