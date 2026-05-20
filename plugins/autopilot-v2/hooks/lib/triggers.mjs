// Registry loader for triggers/*.json.
//
// Single source of truth per ADR-0018 + docs/design/autopilot-v2.md.
// Both guard.mjs (hook detection) and tools/gen-skill.mjs (skill text
// generation) consume this loader. They cannot disagree because they
// read the same JSON.

import { readFileSync, readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const TRIGGERS_DIR = join(HERE, "..", "..", "triggers");

let _cache = null;

export function loadTriggers() {
  if (_cache) return _cache;
  const files = readdirSync(TRIGGERS_DIR)
    .filter((f) => f.endsWith(".json"))
    .sort();
  _cache = files.map((f) => {
    const raw = readFileSync(join(TRIGGERS_DIR, f), "utf8");
    const t = JSON.parse(raw);
    if (!t.id) throw new Error(`trigger ${f} missing 'id'`);
    if (!["A", "A-hybrid"].includes(t.class)) {
      throw new Error(`trigger ${f} class must be A or A-hybrid; got ${t.class}`);
    }
    if (!t.detection || !t.detection.type) {
      throw new Error(`trigger ${f} missing detection.type`);
    }
    return t;
  });
  return _cache;
}

export function bashPatternTriggers() {
  return loadTriggers().filter((t) => t.detection.type === "bash_pattern");
}

export function stateCounterTriggers() {
  return loadTriggers().filter((t) => t.detection.type === "state_counter");
}

export function compileBashRegex(trigger) {
  const alts = trigger.detection.patterns.map((p) => `(?:${p})`).join("|");
  return new RegExp(alts, "i");
}

// Named accessors. Hook callers should ask for triggers by intent
// (`getStateCounterTrigger("tool-calls")`) rather than reaching into
// `.detection.counter` fields — the latter is a leaky abstraction
// that drifts if the registry schema changes.
export function getStateCounterTrigger(counterName) {
  return stateCounterTriggers().find((t) => t.detection.counter === counterName);
}

export function getBudgetTrigger() {
  return getStateCounterTrigger("tool-calls");
}

export function getDlogTrigger() {
  return getStateCounterTrigger("writes-since-dlog");
}
