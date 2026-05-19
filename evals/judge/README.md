# Judge calibration harness (PR-6 / ADR-0017)

Subjective rubrics (judge_binary criteria) can enter the v2 scoring formula
only after they're calibrated: AC2 ≥ 0.7 between the LLM judge and human
labels across ≥20 labeled transcripts. Uncalibrated rubrics auto-skip
(reported as `judge_uncalibrated`, not failed).

## Why

Substring-match criteria (`ask_present`, `handback_section`) are brittle
on subjective qualities. They miss agent phrasings we didn't anticipate
(criteria-self-bias). An LLM judge with a binary rubric scales — but only
if its judgments agree with a human ground-truth at usable rates. The
calibration threshold (Gwet's AC2 ≥ 0.7) is the gate.

## Workflow

```bash
# 1. Establish the rubric (one binary y/n question, ≤200 words).
#    See rubrics/handback_done_quality_v1.md as a template.

# 2. Run baselines to seed labelable transcripts. run.py persists
#    final_message + tool_summary in results JSON for every run.

# 3. Label ≥20 (ideally 30+) transcripts for the rubric.
python3 evals/judge/label.py --rubric handback_done_quality_v1
# Walks past results JSON files, presents (brief, handback, tool_summary)
# per run, prompts y/n/s/q. Resumes where you left off — won't re-prompt
# already-labeled (results_file, fixture, run_idx) tuples.

# 4. Compute AC2 between the LLM judge and your labels.
python3 evals/judge/calibrate.py --rubric handback_done_quality_v1
# Writes evals/judge/calibration.json with per-rubric AC2 + confusion matrix.

# 5. The rubric is now usable in fixtures:
#      criteria:
#        - id: handback_quality_judge
#          kind: judge_binary
#          rubric_id: handback_done_quality_v1
#          target_artifact: plugins/autopilot/skills/handback/SKILL.md
#    If AC2 ≥ 0.7, the judge runs and scores. Else the criterion skips.

# 6. Re-calibrate periodically as rubric or judge model versions change.
```

## Layout

```
evals/judge/
├── README.md                              this file
├── label.py                               interactive labeling CLI
├── calibrate.py                           replays judge + Gwet's AC2
├── calibration.json                       per-rubric AC2 + confusion (auto-gen)
├── rubrics/<id>.md                        binary rubric (one per criterion)
└── labels/<id>.jsonl                      append-only human labels per rubric
```

## Conventions

- **Binary rubrics only** — per ADR-0017 PR-6, Likert and fractional
  fallbacks are off the table. The judge returns `{"label":"yes"|"no",
  "reason":"<one sentence>"}`.
- **Pin rubrics** — each rubric file is its own version (handback_done_quality_v1).
  Changes to the rubric require a new version + re-calibration. Don't
  edit `_v1` in place once labels exist; create `_v2`.
- **Label conservatively** — when in doubt, skip rather than guess. The
  AC2 metric punishes labeled-but-uncertain ambiguity worse than skipping.
- **Aim for class balance** — at least 30% of labels should be the
  minority class. All-yes or all-no label sets produce degenerate AC2.

## Cost

- Labeling: 1–2 minutes per label. 20 labels ≈ 30 minutes; 30 labels
  ≈ 45 minutes. Human time, no API spend.
- Calibration: ~$0.002 per labeled transcript replayed through the judge
  (Sonnet, 256 max_tokens). 30 labels ≈ $0.06.

## What's calibrated today

See `calibration.json` (created after the first `calibrate.py --all` run).
At repo creation time: nothing — all judge_binary criteria auto-skip
until a rubric is calibrated.

Currently shipped rubric template:
- `handback_done_quality_v1` — replaces the substring `handback_done_nonempty`
  for higher-recall judgment of whether a `Done:` section is substantive.
  Status: uncalibrated; ready to label.
