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
const SCHEMA_FILE = "$schema.json";

let _cache = null;
let _schemaCache = null;

function loadSchema() {
  if (_schemaCache) return _schemaCache;
  const raw = readFileSync(join(TRIGGERS_DIR, SCHEMA_FILE), "utf8");
  _schemaCache = JSON.parse(raw);
  return _schemaCache;
}

export function loadTriggers() {
  if (_cache) return _cache;
  const schema = loadSchema();
  const files = readdirSync(TRIGGERS_DIR)
    .filter((f) => f.endsWith(".json") && f !== SCHEMA_FILE)
    .sort();
  _cache = files.map((f) => {
    const raw = readFileSync(join(TRIGGERS_DIR, f), "utf8");
    const t = JSON.parse(raw);
    const errors = validateSchema(t, schema, f);
    if (errors.length > 0) {
      throw new Error(
        `trigger ${f} failed schema validation:\n  - ${errors.join("\n  - ")}`,
      );
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

// --- inline JSONSchema validator (stdlib only) ----------------------
//
// Plugin invariant: Node + stdlib only, no npm. This implements the
// subset of draft-07 the trigger schema actually uses: type, enum,
// required, properties, additionalProperties, oneOf, not, items,
// minItems, minLength. Returns an array of human-readable error
// strings; empty array means valid.
//
// `oneOf` is intentionally strict: exactly one branch must validate.
// For our polymorphic `detection` block, branches are keyed on the
// `type` enum, so a well-formed object matches exactly one branch and
// a typo'd `type` matches zero branches.

export function validateSchema(value, schema, label = "$") {
  return _validate(value, schema, label);
}

function _validate(value, schema, path) {
  const errs = [];
  if (schema.type) {
    const types = Array.isArray(schema.type) ? schema.type : [schema.type];
    if (!types.some((t) => _typeMatches(value, t))) {
      errs.push(`${path}: expected type ${types.join("|")}, got ${_typeOf(value)}`);
      return errs;
    }
  }
  if (schema.enum && !schema.enum.includes(value)) {
    errs.push(`${path}: value ${JSON.stringify(value)} not in enum ${JSON.stringify(schema.enum)}`);
  }
  if (typeof value === "string" && typeof schema.minLength === "number") {
    if (value.length < schema.minLength) {
      errs.push(`${path}: string shorter than minLength ${schema.minLength}`);
    }
  }
  if (Array.isArray(value)) {
    if (typeof schema.minItems === "number" && value.length < schema.minItems) {
      errs.push(`${path}: array shorter than minItems ${schema.minItems}`);
    }
    if (schema.items) {
      for (let i = 0; i < value.length; i++) {
        errs.push(..._validate(value[i], schema.items, `${path}[${i}]`));
      }
    }
  }
  if (value && typeof value === "object" && !Array.isArray(value)) {
    if (Array.isArray(schema.required)) {
      for (const key of schema.required) {
        if (!(key in value)) errs.push(`${path}: missing required field '${key}'`);
      }
    }
    if (schema.properties) {
      for (const [key, sub] of Object.entries(schema.properties)) {
        if (key in value) {
          errs.push(..._validate(value[key], sub, `${path}.${key}`));
        }
      }
    }
    if (schema.additionalProperties === false) {
      const allowed = new Set(Object.keys(schema.properties || {}));
      for (const key of Object.keys(value)) {
        if (!allowed.has(key)) errs.push(`${path}: unknown field '${key}' (additionalProperties=false)`);
      }
    }
  }
  if (Array.isArray(schema.oneOf) && schema.oneOf.length > 0) {
    const branchErrors = schema.oneOf.map((branch) => _validate(value, branch, path));
    const passing = branchErrors.filter((e) => e.length === 0).length;
    if (passing === 0) {
      // Report the branch with the fewest errors — usually the intended one.
      const best = branchErrors.reduce((a, b) => (a.length <= b.length ? a : b));
      errs.push(`${path}: oneOf matched 0 branches; closest branch errors: ${best.join("; ")}`);
    } else if (passing > 1) {
      errs.push(`${path}: oneOf matched ${passing} branches (must match exactly 1)`);
    }
  }
  if (schema.not) {
    if (_validate(value, schema.not, path).length === 0) {
      errs.push(`${path}: matched 'not' schema (should not match)`);
    }
  }
  return errs;
}

function _typeOf(v) {
  if (v === null) return "null";
  if (Array.isArray(v)) return "array";
  return typeof v;
}

function _typeMatches(v, t) {
  switch (t) {
    case "string": return typeof v === "string";
    case "number": return typeof v === "number";
    case "integer": return typeof v === "number" && Number.isInteger(v);
    case "boolean": return typeof v === "boolean";
    case "array": return Array.isArray(v);
    case "object": return v !== null && typeof v === "object" && !Array.isArray(v);
    case "null": return v === null;
    default: return false;
  }
}
