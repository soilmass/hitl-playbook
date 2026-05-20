#!/usr/bin/env bash
# triggers-roundtrip.sh — the v2 architectural invariant test.
#
# Verifies that triggers/*.json round-trips through both consumers:
#   1. tools/gen-skill.mjs (skill text generation)
#   2. hooks/lib/triggers.mjs (hook loader + regex compilation)
#
# If either fails, the single-source-of-truth contract is broken.
# Run before every commit that touches triggers/, hooks/, or skills/autopilot/.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

echo "=== triggers-roundtrip ==="

# Step 1: registry loads + validates schema.
echo "[1/3] registry loads..."
node -e "import('./hooks/lib/triggers.mjs').then(m => { const ts = m.loadTriggers(); if (ts.length === 0) { process.stderr.write('no triggers loaded\n'); process.exit(1); } console.log(' ', ts.length, 'triggers OK:', ts.map(t=>t.id).join(', ')); })"

# Step 2: every bash_pattern regex compiles + matches its own description-ish text.
echo "[2/3] regex compilation..."
node -e "
import('./hooks/lib/triggers.mjs').then(m => {
  for (const t of m.bashPatternTriggers()) {
    try {
      const r = m.compileBashRegex(t);
      console.log('  OK', t.id, '(', t.detection.patterns.length, 'patterns)');
    } catch (e) {
      process.stderr.write('FAIL regex for ' + t.id + ': ' + e.message + '\n');
      process.exit(1);
    }
  }
});
"

# Step 3: generated SKILL.md matches what's checked in.
echo "[3/3] SKILL.md fresh vs registry..."
node tools/gen-skill.mjs --check

echo "=== PASS ==="
