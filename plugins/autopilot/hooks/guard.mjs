#!/usr/bin/env node
// autopilot plugin hook guard.
// Modes: pretool-bash | pretool-write | posttool-log | session-start
// Invoked from hooks.json. Reads JSON on stdin. Exit 0 = allow, 2 = block.
//
// NOT a real security boundary. Stops accidents and well-behaved agents;
// a determined or compromised agent can bypass via tool substitution
// (python -c, perl -e, etc. are blocked; novel indirection paths are not).
// Real enforcement requires OS-level sandboxing.

import { readFileSync, realpathSync, mkdirSync, appendFileSync, existsSync, writeFileSync } from 'node:fs';
import { resolve, sep, dirname, join, basename } from 'node:path';
import { tmpdir } from 'node:os';

const BUDGET_YELLOW = Number(process.env.AUTOPILOT_BUDGET_YELLOW) || 50;
const BUDGET_RED = Number(process.env.AUTOPILOT_BUDGET_RED) || 150;

// Defang the hook environment: ignore caller's PATH and preload shims.
process.env.PATH = '/usr/bin:/bin:/usr/local/bin';
delete process.env.LD_PRELOAD;
delete process.env.BASH_ENV;
delete process.env.PROMPT_COMMAND;

const mode = process.argv[2];

function readStdin() {
  try { return JSON.parse(readFileSync(0, 'utf8')); }
  catch { return {}; }
}

function block(msg) {
  process.stderr.write(`autopilot: ${msg}\n`);
  process.exit(2);
}

// --- pretool-bash ---------------------------------------------------------

// Boundary that marks "start of a command position" — beginning of string,
// or after a real command separator (semicolon, pipe, &&, ||, backgrounding).
// Whitespace alone does NOT count, so `echo eval is risky` doesn't trip
// the eval rule.
const CMD_START = `(^|[;|&]\\s*|\\|\\|\\s*|&&\\s*)`;

// Hardened destructive-bash patterns. Case-insensitive where it matters.
// Order: most-common first for cheap early matches.
const BASH_PATTERNS = [
  // rm and variants — match \rm, 'rm', "rm", /bin/rm, /usr/bin/rm.
  // Also catch when rm appears inside quoted git alias payloads etc.
  /(^|[\s;|&(!'"`])\\?['"]?(?:\/(?:usr\/)?bin\/)?rm['"]?\s+(?:-[a-zA-Z]*[rRf]|--recursive|--force)/i,
  // alternative deletion tools
  /(^|[\s;|&(])(?:find\b[^|;&]*\s-delete\b|dd\s+[^|]*of=\/dev\/|shred\s+-[a-zA-Z]*u|truncate\s+-s\s*0|unlink\s+\/)/i,
  /(^|[\s;|&(])>\s*\/(?:etc|var|usr|home|root|boot|sys)\b/, // truncation of system paths
  // git destructive — force-push has explicit short-flag handling
  /\bgit\s+(?:-c\s+\S+\s+)*push\s+(?:[^|;&]*\s)?(?:--force(?:-with-lease)?|--mirror|--delete\b)/i,
  /\bgit\s+(?:-c\s+\S+\s+)*push(?:\s+\S+)*\s+-[a-zA-Z]*f[a-zA-Z]*(?=\s|$)/i, // -f, -fu, -uf, -ufv, etc.
  /\bgit\s+reset\s+--hard\b/i,
  /\bgit\s+clean\s+-[a-zA-Z]*f/i,
  /\bgit\s+(?:commit|push|tag|merge)\s+(?:[^|;&]*\s)?--no-verify\b/i,
  /\bgit\s+-c\s+alias\./i, // git alias execution can hide arbitrary payload
  // gh destructive
  /\bgh\s+pr\s+merge\b/i,
  /\bgh\s+release\s+(?:create|delete)\b/i,
  /\bgh\s+api\s+(?:[^|;&]*\s)?-X\s+DELETE\b/i,
  // publish
  /\b(?:npm|pnpm|yarn)\s+publish\b/i,
  /\bpip\s+upload\b/i,
  /\bcargo\s+publish\b/i,
  // sql destructive — only block when invoked via a SQL client tool or as
  // a -c/-e argument, so prose like `echo 'drop table is bad'` doesn't match.
  /\b(?:psql|mysql|mariadb|sqlite3?|pg_dump|mongosh|redis-cli)\b[^|]*\b(?:DROP\s+(?:TABLE|DATABASE|SCHEMA|INDEX)|TRUNCATE\s+TABLE|DELETE\s+FROM)\b/i,
  /-[ce]\s+["'][^"']*\b(?:DROP\s+(?:TABLE|DATABASE|SCHEMA|INDEX)|TRUNCATE\s+TABLE|DELETE\s+FROM)\b/i,
  // indirection / eval — must be at command position, not in prose
  new RegExp(`${CMD_START}(?:eval|source|\\.)\\s+\\S`),
  new RegExp(`${CMD_START}(?:bash|sh|zsh)\\s+-c\\b`),
  new RegExp(`${CMD_START}(?:python3?|perl|ruby|node|deno)\\s+-[ce]\\b`),
  /\$\([^)]*\b(?:rm\s+-[a-zA-Z]*[rRf]|find\s+[^|]*-delete|dd\s+if=|shred\s+-)/i,
  /`[^`]*\b(?:rm\s+-[a-zA-Z]*[rRf]|find\s+[^|]*-delete|dd\s+if=|shred\s+-)/i,
  // base64-decode-then-pipe
  /base64\s+(?:-d|--decode)[^|]*\|\s*(?:bash|sh|zsh|eval)/i,
  // path/env hijack — refuse commands that set PATH/LD_PRELOAD inline
  /^\s*(?:PATH|LD_PRELOAD|BASH_ENV|IFS)\s*=/,
  // chmod/chown -R on broad paths
  /\bch(?:mod|own)\s+-[a-zA-Z]*R[a-zA-Z]*\s+\S*\/(?:$|\s)/,
];

function checkBash(input) {
  const cmd = String(input?.tool_input?.command ?? '');
  if (!cmd) return;
  for (const pat of BASH_PATTERNS) {
    if (pat.test(cmd)) {
      block(`blocked destructive command (matched ${pat.source.slice(0, 60)}...). Surface to the human; do not work around.`);
    }
  }
}

// --- pretool-write --------------------------------------------------------

// Resolve a path through symlinks even if the file doesn't exist yet.
// Walks up to the nearest existing ancestor, realpaths that, then rejoins.
function realpathOfPossiblyMissing(p) {
  const abs = resolve(p);
  let cur = abs, tail = [];
  while (true) {
    try { return tail.length ? join(realpathSync(cur), ...tail) : realpathSync(cur); }
    catch {
      const parent = dirname(cur);
      if (parent === cur) return abs; // hit root without resolving
      tail.unshift(basename(cur));
      cur = parent;
    }
  }
}

function checkWrite(input) {
  const filePath = String(input?.tool_input?.file_path ?? '');
  if (!filePath) return;

  let realPath, realCwd;
  const safeRoots = [];
  try {
    realPath = realpathOfPossiblyMissing(filePath);
    realCwd = realpathSync(process.cwd());
    safeRoots.push(realCwd);
    // Allow both /tmp (Linux + macOS symlink) and os.tmpdir() (macOS /var/folders).
    for (const t of ['/tmp', tmpdir()]) {
      try { safeRoots.push(realpathSync(t)); } catch {}
    }
  } catch (e) {
    block(`could not resolve paths for Write check: ${e.message}`);
  }

  const ok = safeRoots.some(r => realPath === r || realPath.startsWith(r + sep));
  if (!ok) {
    block(`blocked Write to '${realPath}' (outside project dir '${realCwd}' and tmp dirs). Surface to the human.`);
  }
}

// --- budget tracking -------------------------------------------------------

// Session id resolution: prefer the hook's stdin payload (set on every
// hook event by Claude Code), then the real env var name
// CLAUDE_CODE_SESSION_ID (NOT CLAUDE_SESSION_ID — that was a guess that
// turned out wrong), then a stable fallback.
function sessionIdFrom(input) {
  return input?.session_id
    || process.env.CLAUDE_CODE_SESSION_ID
    || process.env.CLAUDE_SESSION_ID
    || 'unknown-session';
}

function budgetPath(sessionId) {
  const projectDir = process.env.CLAUDE_PROJECT_DIR || process.cwd();
  return join(projectDir, '.claude', 'autopilot-logs', `${sessionId}.budget`);
}

function readBudget(sessionId) {
  try { return Number(readFileSync(budgetPath(sessionId), 'utf8')) || 0; }
  catch { return 0; }
}

function bumpBudget(sessionId) {
  try {
    const p = budgetPath(sessionId);
    mkdirSync(dirname(p), { recursive: true });
    const next = readBudget(sessionId) + 1;
    writeFileSync(p, String(next));
    return next;
  } catch { return 0; }
}

function checkBudget(input) {
  const n = readBudget(sessionIdFrom(input));
  if (n >= BUDGET_RED) {
    block(`budget exceeded (${n} tool calls; red threshold ${BUDGET_RED}). Hand back to human; do not continue.`);
  }
  if (n === BUDGET_YELLOW) {
    // Soft warning at the threshold: stderr without blocking. Agent surfaces.
    process.stderr.write(
      `autopilot: budget tick (${n}/${BUDGET_RED} tool calls). Surface a "still on track?" checkpoint via AskUserQuestion before the next tool.\n`
    );
  }
}

// --- posttool-log ---------------------------------------------------------

// Append a redacted one-line JSONL entry to the per-session log.
// Captures: timestamp, tool name, brief input summary, exit status.
// Skips: tool output (where secrets live), reads of safe files.

const SECRET_PATTERNS = [
  /(api[_-]?key|token|secret|password|bearer|authorization)[=:\s]+["']?([^"'\s,;)]+)/gi,
  /\b[A-Za-z0-9_-]{32,}\b/g, // long opaque tokens
];

function redact(s) {
  if (!s) return s;
  let out = String(s).slice(0, 200);
  for (const pat of SECRET_PATTERNS) out = out.replace(pat, (m) => '***');
  return out;
}

function summarizeInput(toolName, input) {
  if (!input) return '';
  // Pick the most informative field per tool.
  if (toolName === 'Bash') return input.command || '';
  if (toolName === 'Write' || toolName === 'Edit' || toolName === 'Read') return input.file_path || '';
  if (toolName === 'Grep') return `${input.pattern || ''} in ${input.path || '.'}`;
  if (toolName === 'Glob') return input.pattern || '';
  if (toolName === 'WebFetch' || toolName === 'WebSearch') return input.url || input.query || '';
  // Fallback: stringify first key
  const k = Object.keys(input)[0];
  return k ? `${k}=${JSON.stringify(input[k])}` : '';
}

function logToolUse(input) {
  const projectDir = process.env.CLAUDE_PROJECT_DIR || process.cwd();
  const sessionId = sessionIdFrom(input);
  const logDir = join(projectDir, '.claude', 'autopilot-logs');
  const logPath = join(logDir, `${sessionId}.jsonl`);
  try {
    mkdirSync(logDir, { recursive: true });
    const toolName = input.tool_name || 'unknown';
    const entry = {
      ts: new Date().toISOString(),
      tool: toolName,
      input: redact(summarizeInput(toolName, input.tool_input)),
      ok: input.tool_response?.is_error ? false : true,
      n: bumpBudget(sessionId),
    };
    appendFileSync(logPath, JSON.stringify(entry) + '\n');
  } catch {
    // Logging must never block a hook; swallow errors silently.
  }
}

// --- session-start --------------------------------------------------------

function sessionStart() {
  if (process.env.CLAUDE_AUTOPILOT === '1') {
    const payload = {
      hookSpecificOutput: {
        hookEventName: 'SessionStart',
        additionalContext:
          'CLAUDE_AUTOPILOT=1 is set. Load and follow the autopilot skill for this entire session. ' +
          'Default to proceeding; use AskUserQuestion only at yellow-tier branch points; respect hook blocks on destructive ops.',
      },
    };
    process.stdout.write(JSON.stringify(payload));
  }
}

// --- dispatch -------------------------------------------------------------

// Parse stdin once per invocation; pass to handlers that need it.
const stdinInput = (mode === 'session-start') ? {} : readStdin();

switch (mode) {
  case 'pretool-bash':    checkBudget(stdinInput); checkBash(stdinInput); break;
  case 'pretool-write':   checkBudget(stdinInput); checkWrite(stdinInput); break;
  case 'pretool-budget':  checkBudget(stdinInput); break;
  case 'posttool-log':    logToolUse(stdinInput); break;
  case 'session-start':   sessionStart(); break;
  default:
    process.stderr.write(`autopilot guard: unknown mode '${mode}'\n`);
    process.exit(1);
}
