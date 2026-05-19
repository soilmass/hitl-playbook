#!/usr/bin/env python3
"""
Replay the LLM judge over human-labeled transcripts and compute
Gwet's AC2 inter-rater agreement (per ADR-0017 PR-6).

If AC2 ≥ 0.7 the rubric is calibrated and run.py will use the
judge in scoring. Otherwise the criterion is reported as
'judge_uncalibrated' (skipped, not failed).

Usage:
  python3 evals/judge/calibrate.py --rubric handback_done_quality_v1
  python3 evals/judge/calibrate.py --all

Writes evals/judge/calibration.json with the per-rubric AC2 +
confusion matrix.
"""

import argparse
import json
import sys
from pathlib import Path
from collections import Counter

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
JUDGE_DIR = REPO_ROOT / "evals" / "judge"
CALIBRATION_PATH = JUDGE_DIR / "calibration.json"


def gwet_ac2(labels_a: list[str], labels_b: list[str]) -> float:
    """
    Compute Gwet's AC2 (gamma) for two raters on a binary task.
    More robust than Cohen's kappa under class skew.

    AC2 = (Pa - Pe) / (1 - Pe), where
      Pa = observed agreement
      Pe = chance agreement = sum_k pi_k * (1 - pi_k) for binary
                              where pi_k = marginal probability of category k
    """
    if len(labels_a) != len(labels_b):
        raise ValueError("rater lists must be equal length")
    n = len(labels_a)
    if n == 0:
        return 0.0
    # Observed agreement
    agree = sum(1 for a, b in zip(labels_a, labels_b) if a == b)
    Pa = agree / n
    # Marginal probabilities pooled across both raters
    all_labels = labels_a + labels_b
    counts = Counter(all_labels)
    K = len(counts)  # number of categories (typically 2 for binary)
    if K < 2:
        return 1.0 if Pa == 1.0 else 0.0
    pi = {k: counts[k] / (2 * n) for k in counts}
    Pe = sum(pi_k * (1 - pi_k) for pi_k in pi.values()) / (K - 1)
    if Pe >= 1.0:
        return 1.0
    return (Pa - Pe) / (1 - Pe)


def parse_rubric_prompt(rubric_path: Path) -> str:
    """Extract the prompt template from a rubric markdown file.
    Convention: the template lives after '## Judge prompt template' heading."""
    text = rubric_path.read_text()
    marker = "## Judge prompt template"
    idx = text.find(marker)
    if idx == -1:
        sys.exit(f"rubric {rubric_path.name} missing '## Judge prompt template' heading")
    return text[idx + len(marker):].strip()


def ask_judge(client, prompt_template: str, brief: str, handback: str) -> dict:
    """Call Sonnet with the rubric prompt, return parsed JSON {label, reason}."""
    # Substitute template variables. Use literal-string replacement to avoid
    # KeyError if the template has stray braces.
    prompt = prompt_template.replace("{brief}", brief).replace("{handback}", handback)
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()
    # Strip code fences if the judge wrapped its JSON
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(line for line in lines if not line.startswith("```"))
    try:
        return json.loads(raw)
    except Exception as e:
        return {"label": "n/a", "reason": f"parse error: {e}", "raw": raw[:200]}


def calibrate_rubric(rubric_id: str) -> dict:
    rubric_path = JUDGE_DIR / "rubrics" / f"{rubric_id}.md"
    labels_path = JUDGE_DIR / "labels" / f"{rubric_id}.jsonl"
    if not rubric_path.exists():
        sys.exit(f"rubric not found: {rubric_path}")
    if not labels_path.exists():
        return {"rubric": rubric_id, "n": 0, "error": "no labels file"}

    prompt = parse_rubric_prompt(rubric_path)
    try:
        from anthropic import Anthropic
    except ImportError:
        sys.exit("install anthropic SDK to run calibration: pip install anthropic")
    client = Anthropic()
    print(f"calibrating {rubric_id} …")
    print(f"  labels file: {labels_path}")

    human_labels = []
    judge_labels = []
    judgments = []
    cost_estimate = 0.0
    for line in labels_path.read_text().splitlines():
        if not line.strip(): continue
        rec = json.loads(line)
        if rec.get("human_label") not in ("yes", "no"):
            continue
        judge = ask_judge(client, prompt,
                          rec.get("brief_excerpt", ""),
                          rec.get("handback_excerpt", ""))
        judge_label = judge.get("label", "n/a")
        human_labels.append(rec["human_label"])
        judge_labels.append(judge_label if judge_label in ("yes", "no") else "n/a")
        judgments.append({
            "fixture": rec.get("fixture"),
            "run_idx": rec.get("run_idx"),
            "human": rec["human_label"],
            "judge": judge_label,
            "judge_reason": judge.get("reason", ""),
        })
        cost_estimate += 0.002  # very rough — Sonnet 256 max_tokens

    # Confusion matrix
    confusion = Counter((h, j) for h, j in zip(human_labels, judge_labels))
    ac2 = gwet_ac2(human_labels, judge_labels)
    calibrated = ac2 >= 0.7

    result = {
        "rubric": rubric_id,
        "n": len(human_labels),
        "ac2": round(ac2, 4),
        "calibrated": calibrated,
        "threshold": 0.7,
        "confusion": {f"{h}|{j}": c for (h, j), c in confusion.items()},
        "judgments": judgments,
        "estimated_cost_usd": round(cost_estimate, 4),
    }
    print(f"  n={result['n']}, AC2={result['ac2']}, "
          f"{'CALIBRATED' if calibrated else 'NOT calibrated (< 0.7)'}")
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rubric", help="rubric ID to calibrate")
    ap.add_argument("--all", action="store_true", help="calibrate every rubric with a labels file")
    args = ap.parse_args()

    rubrics_to_run = []
    if args.all:
        rubrics_to_run = [p.stem for p in (JUDGE_DIR / "labels").glob("*.jsonl")]
    elif args.rubric:
        rubrics_to_run = [args.rubric]
    else:
        ap.error("provide --rubric ID or --all")

    # Load existing calibration if any
    if CALIBRATION_PATH.exists():
        all_cal = json.loads(CALIBRATION_PATH.read_text())
    else:
        all_cal = {}

    for rid in rubrics_to_run:
        all_cal[rid] = calibrate_rubric(rid)

    CALIBRATION_PATH.write_text(json.dumps(all_cal, indent=2))
    print(f"\nWrote {CALIBRATION_PATH}")
    print(f"Calibrated rubrics ({sum(1 for v in all_cal.values() if v.get('calibrated'))}/{len(all_cal)}):")
    for rid, info in all_cal.items():
        mark = "✓" if info.get("calibrated") else "✗"
        print(f"  {mark} {rid:<40} AC2={info.get('ac2','?')} n={info.get('n',0)}")


if __name__ == "__main__":
    main()
