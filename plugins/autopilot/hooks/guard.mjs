#!/usr/bin/env node
// autopilot plugin hook guard.
// Modes: pretool-bash | pretool-write | session-start
// Invoked from hooks.json. Reads JSON on stdin. Exit 0 = allow, 2 = block.
//
// NOT a real security boundary. Stops accidents and well-behaved agents;
// a determined or compromised agent can bypass via tool substitution
// (python -c, perl -e, etc. are blocked; novel indirection paths are not).
// Real enforcement requires OS-level sandboxing.

import { readFileSync, realpathSync, mkdirSync } from 'node:fs';
import { resolve, sep } from 'node:path';
import { tmpdir } from 'node:os';

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

function checkWrite(input) {
  const filePath = String(input?.tool_input?.file_path ?? '');
  if (!filePath) return;

  let realPath, realCwd, realTmp;
  try {
    // realpath the parent if file doesn't exist yet
    const resolved = resolve(filePath);
    try { realPath = realpathSync(resolved); }
    catch { realPath = resolved; } // file doesn't exist; use resolved path
    realCwd = realpathSync(process.cwd());
    realTmp = realpathSync(tmpdir());
  } catch (e) {
    block(`could not resolve paths for Write check: ${e.message}`);
  }

  const inCwd = realPath === realCwd || realPath.startsWith(realCwd + sep);
  const inTmp = realPath === realTmp || realPath.startsWith(realTmp + sep);

  if (!inCwd && !inTmp) {
    block(`blocked Write to '${realPath}' (outside project dir '${realCwd}' and tmp '${realTmp}'). Surface to the human.`);
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

switch (mode) {
  case 'pretool-bash':   checkBash(readStdin()); break;
  case 'pretool-write':  checkWrite(readStdin()); break;
  case 'session-start':  sessionStart(); break;
  default:
    process.stderr.write(`autopilot guard: unknown mode '${mode}'\n`);
    process.exit(1);
}
