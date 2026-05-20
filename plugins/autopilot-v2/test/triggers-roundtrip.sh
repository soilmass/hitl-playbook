#!/usr/bin/env bash
# triggers-roundtrip.sh — the v2 architectural invariant test.
#
# Verifies that triggers/*.json round-trips through both consumers
# without drift:
#   - hooks/lib/triggers.mjs (registry loader + schema validator
#     + bash_pattern regex compilation)
#   - tools/gen-skill.mjs (skills/autopilot/SKILL.md generation)
#
# If either fails, the single-source-of-truth contract is broken.
# Run before every commit that touches triggers/, hooks/, or skills/autopilot/.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

echo "=== triggers-roundtrip ==="

# Step 1: registry loads.
echo "[1/4] registry loads..."
node -e "import('./hooks/lib/triggers.mjs').then(m => { const ts = m.loadTriggers(); if (ts.length === 0) { process.stderr.write('no triggers loaded\n'); process.exit(1); } console.log(' ', ts.length, 'triggers OK:', ts.map(t=>t.id).join(', ')); })"

# Step 2: every trigger file validates against triggers/\$schema.json.
# Separate from step 1 because loadTriggers() also validates as a
# side effect; this step makes the contract explicit and produces
# per-file output so a future regression is easy to localise.
echo "[2/4] schema validation..."
node -e "
import('./hooks/lib/triggers.mjs').then(async m => {
  const fs = await import('node:fs');
  const path = await import('node:path');
  const dir = './triggers';
  const schema = JSON.parse(fs.readFileSync(path.join(dir, '\$schema.json'), 'utf8'));
  const files = fs.readdirSync(dir).filter(f => f.endsWith('.json') && f !== '\$schema.json').sort();
  let bad = 0;
  for (const f of files) {
    const obj = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8'));
    const errs = m.validateSchema(obj, schema, f);
    if (errs.length === 0) {
      console.log('  OK', f);
    } else {
      bad++;
      for (const e of errs) console.error('  FAIL', e);
    }
  }
  if (bad > 0) process.exit(1);
});
"

# Step 3: every bash_pattern regex compiles.
echo "[3/4] regex compilation..."
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

# Step 4: generated SKILL.md matches what's checked in.
echo "[4/4] SKILL.md fresh vs registry..."
node tools/gen-skill.mjs --check

echo "=== PASS ==="
