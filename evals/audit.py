#!/usr/bin/env python3
"""
Independent-review gate for plugin changes (ADR-0017 follow-up).

Two empirical findings from session 2026-05-19 motivate this tool:
1. Self-review by the change author missed a P0 (`_classify_ask` deleted
   in PR-8, call site left in place). An independent reviewer caught it
   in one pass over the same code.
2. Author-written substring criteria for fixture 04 capped recall at
   67 mean. Independent expansion brought it to 100 mean. No agent code
   changed.

The common thread: criteria-self-bias and self-review-bias are real and
expensive. This tool encodes the cheapest mitigation — spawn a fresh
`claude -p` over the staged diff with an audit prompt that reads what
the code actually says, not what the author thinks it says.

Usage:
  python3 evals/audit.py                  # audit unstaged + staged vs HEAD
  python3 evals/audit.py --since main     # audit current branch vs main
  python3 evals/audit.py --since HEAD~3   # audit last 3 commits

Exit codes:
  0 — auditor found no blocking issues (or only advisory ones)
  1 — auditor flagged at least one P0/P1
  2 — invocation error (no claude CLI, no diff, etc.)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Cap untracked-file bodies injected into the audit prompt. Whole-file
# injection makes per-call token cost scale with diff size instead of
# signal; the first ~500 lines are where audit-surface findings live.
UNTRACKED_BODY_LINE_CAP = 500

AUDIT_PROMPT = """\
You are an independent code reviewer auditing a diff. The author CANNOT
see your reasoning, only your final report — so be specific.

Read what the code actually says, not what you assume it does. The
author's self-review already passed; you are explicitly looking for
what they missed.

Focus on these failure modes (frequency-ranked from prior incidents):

P0 — likely-crashing or silently-failing:
  - Symbols called but no longer defined (deleted in a refactor, call
    site missed). Grep the codebase for each new/changed function call.
  - Bare `except Exception:` blocks that would swallow a NameError or
    ImportError. List every one in the diff or its callers.
  - Mutable default arguments, off-by-one in loops, unguarded array[0].

P1 — wrong-but-not-crashing:
  - Doc claims contradicted by current code (e.g. a README that says
    "supports X" when the code path was removed).
  - Stale version numbers, counts, fixture names referenced in docs.
  - Test expectations updated but the test itself never re-run.
  - Methodology contracts the code violates (e.g. a stated invariant
    the changed code now breaks).

P2 — advisory:
  - Naming, comments, style nits. Only flag if egregious.

For each finding, output a single line in this exact format:
  [P0|P1|P2] <file>:<line> — <one-sentence description>

If you find nothing in a category, output a single line:
  [P0|P1|P2] CLEAN — no findings in this category.

After your line items, output a final line:
  VERDICT: <PASS|FAIL>
PASS iff no P0 and no P1. Advisory P2 alone is PASS.

Do NOT add narration or context. Line items + verdict only.
"""


def _git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True)


def _collect_diff(since: str | None) -> tuple[str, list[str]]:
    """Return (unified diff text, list of changed file paths).

    No --since: audit uncommitted work (staged + unstaged + untracked)
    against HEAD. Untracked files matter — a brand-new audit.py is
    exactly the kind of change that most needs an outside read.

    --since <ref>: audit committed work on this branch vs <ref>. Uses
    two-dot `A..B` (in `git diff` this is identical to `git diff A B`
    — an endpoint diff). Triple-dot `A...B` would diff <ref> against
    the merge base, which gives the wrong answer when <ref> has moved
    since the branch diverged.
    """
    if since:
        diff = _git(["diff", f"{since}..HEAD", "--unified=8"])
        files_raw = _git(["diff", "--name-only", f"{since}..HEAD"])
        files = [f for f in files_raw.strip().splitlines() if f]
        return diff, files

    # Uncommitted: combine tracked diffs (staged+unstaged) with untracked.
    diff_tracked = _git(["diff", "HEAD", "--unified=8"])
    files_tracked = _git(["diff", "--name-only", "HEAD"]).strip().splitlines()
    untracked = _git(["ls-files", "--others", "--exclude-standard"]).strip().splitlines()
    files = [f for f in (files_tracked + untracked) if f]

    diff_untracked = ""
    for f in untracked:
        fp = REPO_ROOT / f
        try:
            body = fp.read_text()
        except (OSError, UnicodeDecodeError):
            continue  # binary or unreadable; skip body but still list it
        body_lines = body.splitlines()
        truncated = len(body_lines) > UNTRACKED_BODY_LINE_CAP
        if truncated:
            body_lines = body_lines[:UNTRACKED_BODY_LINE_CAP]
        diff_untracked += (
            f"\ndiff --git a/{f} b/{f}\n"
            f"new file\n"
            f"--- /dev/null\n+++ b/{f}\n"
        )
        for line in body_lines:
            diff_untracked += f"+{line}\n"
        if truncated:
            diff_untracked += f"+... [truncated at {UNTRACKED_BODY_LINE_CAP} lines for audit; full file at {f}]\n"
    return diff_tracked + diff_untracked, files


def _claude_audit(diff: str, files: list[str], model: str) -> str:
    """Spawn claude -p with the audit prompt; return its stdout text."""
    if not diff.strip():
        sys.exit("audit: no diff to review")
    file_list = "\n".join(f"- {f}" for f in files)
    prompt = (
        f"{AUDIT_PROMPT}\n\n"
        f"## Files in scope ({len(files)}):\n{file_list}\n\n"
        f"## Diff:\n```diff\n{diff}\n```\n"
    )
    try:
        proc = subprocess.run(
            [
                "claude", "-p", prompt,
                "--model", model,
                "--output-format", "text",
                "--max-turns", "12",
                "--allowed-tools", "Read,Glob,Grep,Bash",
            ],
            capture_output=True, text=True, cwd=REPO_ROOT, timeout=300,
        )
    except subprocess.TimeoutExpired:
        sys.stderr.write("audit: claude CLI exceeded 5-minute timeout\n")
        sys.exit(2)
    except FileNotFoundError:
        sys.stderr.write("audit: `claude` CLI not on PATH\n")
        sys.exit(2)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        sys.exit(2)
    return proc.stdout.strip()


def _parse_verdict(report: str) -> str:
    for line in reversed(report.splitlines()):
        line = line.strip()
        if line.startswith("VERDICT:"):
            return line.split(":", 1)[1].strip().upper()
    return "UNKNOWN"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--since", help="git ref to diff against (default: HEAD)")
    ap.add_argument("--model", default="sonnet",
                    help="claude model for audit (default sonnet; haiku is "
                         "cheaper but per ADR-0014-adjacent observations is "
                         "less reliable at adversarial review)")
    args = ap.parse_args()

    diff, files = _collect_diff(args.since)
    if not files:
        print("audit: no changed files; nothing to review")
        sys.exit(0)
    print(f"audit: reviewing {len(files)} file(s) against {args.since or 'HEAD'}...",
          file=sys.stderr)
    report = _claude_audit(diff, files, args.model)
    print(report)
    verdict = _parse_verdict(report)
    if verdict == "FAIL":
        sys.exit(1)
    if verdict == "UNKNOWN":
        sys.stderr.write("audit: no VERDICT line parsed; treating as failure\n")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
