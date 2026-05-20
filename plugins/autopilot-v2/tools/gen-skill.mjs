#!/usr/bin/env node
// Regenerate skills/autopilot/SKILL.md from triggers/*.json.
//
// Per ADR-0018: SKILL.md is a projection of the trigger registry, not
// a hand-edited file. Drift is structurally impossible because both
// guard.mjs (detection) and this generator (model-facing text) read
// the same source.
//
// Usage: node tools/gen-skill.mjs
//        node tools/gen-skill.mjs --check   # exit 1 if generated != on-disk

import { readFileSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadTriggers } from '../hooks/lib/triggers.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const SKILL_PATH = join(HERE, '..', 'skills', 'autopilot', 'SKILL.md');

function render(triggers) {
  const lines = [];
  lines.push('---');
  lines.push('name: autopilot');
  lines.push('description: High-autonomy operating mode. Proceed by default; pause via AskUserQuestion at categorical yellow-tier triggers; respect hook blocks on destructive ops.');
  lines.push('---');
  lines.push('');
  lines.push('# autopilot (v2)');
  lines.push('');
  lines.push('**GENERATED FROM `triggers/*.json` — do not hand-edit.** Regenerate via `node tools/gen-skill.mjs`. See [ADR-0018](../../../../docs/adr/0018-rebuild-from-lessons-learned.md) for why.');
  lines.push('');
  lines.push('## Operating model');
  lines.push('');
  lines.push('- **Green (default): proceed silently.** Reads, in-scope edits, tests, lints, subagent spawns.');
  lines.push('- **Yellow: pause via `AskUserQuestion`.** Fires when the hook injects an `AUTOPILOT TRIGGER [<id>]:` line via `additionalContext`, OR when you recognize the trigger conditions yourself. Use the templates in `checkpoint-format/SKILL.md`.');
  lines.push('- **Red: hard-stopped by the hook.** You will see `AUTOPILOT_GATE: blocked ...` on stderr. Do not retry; surface to the human in handback.');
  lines.push('');
  lines.push('Class-B (brief-content-only) triggers from v1 are deliberately absent. Their function is subsumed by the `Assumed:` section of handback per `handback/SKILL.md`: enumerate every load-bearing decision you made without asking.');
  lines.push('');
  lines.push('## Yellow-tier triggers (registry-generated)');
  lines.push('');
  for (const t of triggers) {
    lines.push(`### \`${t.id}\` (class ${t.class})`);
    lines.push('');
    lines.push(t.description);
    lines.push('');
    if (t.detection.type === 'bash_pattern') {
      lines.push(`**Detection**: Bash command matches one of ${t.detection.patterns.length} regex pattern(s) in \`triggers/${pad2(triggers.indexOf(t)+1)}-${t.id}.json\`.`);
    } else if (t.detection.type === 'state_counter') {
      const tools = (t.detection.tools || []).join(', ');
      const counter = t.detection.counter;
      const thresh = t.detection.thresholds ? `yellow=${t.detection.thresholds.yellow}, red=${t.detection.thresholds.red}` : `threshold=${t.detection.threshold}`;
      lines.push(`**Detection**: state counter \`${counter}\` over tools [${tools}]; ${thresh}.`);
    }
    lines.push('');
    lines.push(`**On fire**: ${t.advisory_text}`);
    lines.push('');
  }
  lines.push('## Handback');
  lines.push('');
  lines.push('End every task with the format in `handback/SKILL.md`. The `Assumed:` section is load-bearing — it is the audit trail for every silent decision you made without firing a trigger.');
  lines.push('');
  return lines.join('\n');
}

function pad2(n) { return String(n).padStart(2, '0'); }

const triggers = loadTriggers();
const generated = render(triggers);

if (process.argv.includes('--check')) {
  let current = '';
  try { current = readFileSync(SKILL_PATH, 'utf8'); } catch {}
  if (current.trim() !== generated.trim()) {
    process.stderr.write('SKILL.md is stale vs triggers/*.json. Run: node tools/gen-skill.mjs\n');
    process.exit(1);
  }
  process.stdout.write('SKILL.md matches registry.\n');
} else {
  writeFileSync(SKILL_PATH, generated);
  process.stdout.write(`wrote ${SKILL_PATH} (${triggers.length} triggers)\n`);
}
