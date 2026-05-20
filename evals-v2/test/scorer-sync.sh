#!/usr/bin/env bash
# scorer-sync.sh — encode the "v1↔v2 scorer must stay byte-identical" intent
# as a test, not a comment.
#
# Per ADR-0018 + docs/design/autopilot-v2.md: v2's scorer + auditor are
# intentional copies of v1's. They must not drift. If anyone edits one
# tree and forgets the other, this test fails.
#
# When you DELIBERATELY want them to diverge (because v2 needs a real
# scorer change), update both trees in the same commit. If divergence
# is intentional and permanent, delete this test and capture the reason
# in an ADR.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "=== scorer-sync ==="

# scorer/ trees must match.
echo "[1/2] evals/scorer/ vs evals-v2/scorer/..."
if ! diff -rq --exclude=__pycache__ --exclude='*.pyc' evals/scorer evals-v2/scorer >/dev/null 2>&1; then
  echo "  FAIL: scorer trees diverged."
  diff -rq --exclude=__pycache__ --exclude='*.pyc' evals/scorer evals-v2/scorer || true
  echo
  echo "Either re-sync (copy one tree over the other) or, if divergence is"
  echo "intentional, update both deliberately and document in ADR-0018+."
  exit 1
fi
echo "  OK: byte-identical."

# audit.py / auditor.py: same file under different names.
echo "[2/2] evals/audit.py vs evals-v2/auditor.py..."
if ! diff -q evals/audit.py evals-v2/auditor.py >/dev/null 2>&1; then
  echo "  FAIL: audit.py and auditor.py diverged."
  diff -u evals/audit.py evals-v2/auditor.py || true
  exit 1
fi
echo "  OK: byte-identical."

echo "=== PASS ==="
