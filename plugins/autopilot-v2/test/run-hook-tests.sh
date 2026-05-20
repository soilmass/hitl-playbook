#!/usr/bin/env bash
# Hook regression suite for the autopilot-v2 plugin guard.
# Ported from plugins/autopilot/test/run-hook-tests.sh (v1) per the
# v2-followup tracked in plugins/autopilot-v2/README.md.
#
# All 88 v1 cases (77 bash + 8 write + 3 redact) port AS-IS because
# v2's BASH_PATTERNS (red block list) and checkWrite + redact paths
# are byte-equivalent to v1. Added: 2 v2-specific nudge cases that
# exercise the registry-driven yellow-tier path (new in v2).
#
# Runs the LIVE guard.mjs against fixture cases. No regex duplication —
# if the guard changes, this suite catches regressions.
#
# Usage: bash plugins/autopilot-v2/test/run-hook-tests.sh
# Exit:  0 if all pass, 1 if any fail.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
GUARD="$PLUGIN_DIR/hooks/guard.mjs"

if [ ! -f "$GUARD" ]; then
  echo "FATAL: guard not found at $GUARD" >&2
  exit 1
fi

PASS=0
FAIL=0
FAILED_CASES=()

# JSON-escape a string via python (stdlib, present on all CI runners).
json_escape() {
  python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()), end="")'
}

assert_bash() {
  local expect="$1" cmd="$2"
  local payload rc
  payload=$(printf '{"tool_input":{"command":%s}}' "$(printf '%s' "$cmd" | json_escape)")
  echo "$payload" | node "$GUARD" pretool-bash >/dev/null 2>&1
  rc=$?
  local got; [ $rc -eq 2 ] && got=BLOCK || got=ALLOW
  if [ "$got" = "$expect" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    FAILED_CASES+=("  bash  want=$expect got=$got rc=$rc  $cmd")
  fi
}

assert_write() {
  local expect="$1" path="$2"
  local payload rc
  # JSON-escape via the same helper as assert_bash — a path containing
  # `"`, `\`, or other JSON-special chars would otherwise produce
  # malformed JSON, which the hook silently swallows (false PASS).
  payload=$(printf '{"tool_input":{"file_path":%s}}' "$(printf '%s' "$path" | json_escape)")
  echo "$payload" | node "$GUARD" pretool-write >/dev/null 2>&1
  rc=$?
  local got; [ $rc -eq 2 ] && got=BLOCK || got=ALLOW
  if [ "$got" = "$expect" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    FAILED_CASES+=("  write want=$expect got=$got rc=$rc  $path")
  fi
}

# ===== Bash: destructive (must BLOCK) =====
assert_bash BLOCK "rm -rf /tmp/foo"
assert_bash BLOCK "rm -fr build"
assert_bash BLOCK "rm -r node_modules"
assert_bash BLOCK "\\rm -rf /"
assert_bash BLOCK "/bin/rm -rf /"
assert_bash BLOCK "/usr/bin/rm -rf /"

assert_bash BLOCK "git push --force origin main"
assert_bash BLOCK "git push -f"
assert_bash BLOCK "git push -fu"
assert_bash BLOCK "git push -uf"
assert_bash BLOCK "git push origin main -f"
assert_bash BLOCK "git push --force-with-lease"
assert_bash BLOCK "git push --mirror origin"
assert_bash BLOCK "git push --delete origin main"
assert_bash BLOCK "git reset --hard HEAD~1"
assert_bash BLOCK "git clean -fd"
assert_bash BLOCK "git commit --no-verify -m x"
assert_bash BLOCK "git -c alias.x='!rm -rf .' x"

assert_bash BLOCK "gh pr merge 123"
assert_bash BLOCK "gh release create v1.0"
assert_bash BLOCK "gh api -X DELETE repos/owner/repo"

assert_bash BLOCK "npm publish"
assert_bash BLOCK "pnpm publish --tag latest"
assert_bash BLOCK "yarn publish"
assert_bash BLOCK "cargo publish"

assert_bash BLOCK "find . -delete"
assert_bash BLOCK "find / -name foo -delete"
assert_bash BLOCK "dd if=/dev/zero of=/dev/sda"
assert_bash BLOCK "shred -u important.txt"
assert_bash BLOCK "truncate -s0 file"

assert_bash BLOCK "psql -c 'DROP TABLE users'"
assert_bash BLOCK "mysql -e 'DROP DATABASE prod'"
assert_bash BLOCK "sqlite3 db 'DELETE FROM users'"

assert_bash BLOCK "eval \"\$(echo cm0gLXJmIC8K | base64 -d)\""
assert_bash BLOCK "bash -c 'rm -rf /'"
assert_bash BLOCK "sh -c 'echo hi'"
assert_bash BLOCK "python -c 'import os; os.system(\"rm -rf /\")'"
assert_bash BLOCK "perl -e 'unlink glob \"*\"'"
assert_bash BLOCK "source ./evil.sh"
assert_bash BLOCK ". ./evil.sh"
assert_bash BLOCK "cd ..; . evil.sh"
assert_bash BLOCK "base64 -d evil.txt | bash"

assert_bash BLOCK "PATH=/tmp/evil:\$PATH"
assert_bash BLOCK "LD_PRELOAD=/tmp/x.so"

# ===== Bash: safe (must ALLOW) =====
assert_bash ALLOW "ls -la"
assert_bash ALLOW "pwd"
assert_bash ALLOW "cat README.md"
assert_bash ALLOW "git status"
assert_bash ALLOW "git diff HEAD"
assert_bash ALLOW "git log --oneline"
assert_bash ALLOW "git branch"
assert_bash ALLOW "git push"
assert_bash ALLOW "git push origin main"
assert_bash ALLOW "git push origin feature-branch"
assert_bash ALLOW "git push origin feature-fix"
assert_bash ALLOW "git push origin my-foo-branch"
assert_bash ALLOW "git push origin force-release"
assert_bash ALLOW "git push -u origin main"
assert_bash ALLOW "git push -v origin main"
assert_bash ALLOW "git push --set-upstream origin feat/sessions"
assert_bash ALLOW "git commit -m 'fix: dropdown'"
assert_bash ALLOW "git commit -m 'fix dropdown'"
assert_bash ALLOW "rm file.txt"
assert_bash ALLOW "npm test"
assert_bash ALLOW "npm run build"
assert_bash ALLOW "pnpm run build"
assert_bash ALLOW "node script.js"
assert_bash ALLOW "python script.py"
assert_bash ALLOW "find . -name '*.ts'"
assert_bash ALLOW "echo 'rm is a command'"
assert_bash ALLOW "echo 'drop table is bad'"
assert_bash ALLOW "echo eval is risky"
assert_bash ALLOW "echo source is good"
assert_bash ALLOW "ls find"
assert_bash ALLOW "cd ."
assert_bash ALLOW "git log -p ."
assert_bash ALLOW "ls ./src"

# ===== Write: setup throwaway cwd =====
TMPCWD="$(mktemp -d -t autopilot-test-XXXXXX)"
mkdir -p "$TMPCWD/sub"
pushd "$TMPCWD" >/dev/null

assert_write ALLOW "$TMPCWD/foo.txt"
assert_write ALLOW "$TMPCWD/sub/bar.txt"
assert_write ALLOW "/tmp/some-file.txt"

assert_write BLOCK "/etc/passwd"
assert_write BLOCK "/root/file"
assert_write BLOCK "/home/$USER/.ssh/id_rsa"
assert_write BLOCK "$TMPCWD/../../etc/passwd"
assert_write BLOCK "/tmp/../etc/passwd"

popd >/dev/null
rm -rf "$TMPCWD"

# ===== Redaction regression (from dogfood-bugfix audit, 2026-05-19) =====
# Path segments that happen to be 32+ chars of [A-Za-z0-9_-] must NOT
# be treated as opaque tokens. Verifies the (?<!\/)...(?!\/) lookbehind
# in SECRET_PATTERNS.
assert_redact() {
  local expect="$1" inp="$2"
  # Build a fake PostToolUse payload, feed to posttool-log, scrape the
  # resulting input field from the JSONL.
  local tmp=$(mktemp -d -t autopilot-redact-XXXXXX)
  local sid="redact-test-$$"
  local payload
  payload=$(printf '{"tool_name":"Read","tool_input":{"file_path":%s},"session_id":"%s"}' \
    "$(printf '%s' "$inp" | json_escape)" "$sid")
  echo "$payload" | CLAUDE_PROJECT_DIR="$tmp" CLAUDE_CODE_SESSION_ID="$sid" \
    node "$GUARD" posttool-log >/dev/null 2>&1
  # Distinguish "ran successfully but didn't redact" (KEEP) from "log file
  # missing / unparseable" (ERROR). The previous `|| echo ""` collapsed
  # both into KEEP, so a broken posttool-log path would vacuously pass
  # every KEEP assertion. Use a sentinel and check explicitly.
  local jsonl="$tmp/.claude/autopilot-logs/$sid.jsonl"
  local logged got
  if [ ! -s "$jsonl" ]; then
    got=ERROR
    logged="(jsonl missing or empty)"
  else
    logged=$(node -e "const l=require('fs').readFileSync('$jsonl','utf8').trim().split('\n').pop(); console.log(JSON.parse(l).input);" 2>&1)
    if [ $? -ne 0 ]; then
      got=ERROR
    elif echo "$logged" | grep -q '\*\*\*'; then
      got=REDACT
    else
      got=KEEP
    fi
  fi
  if [ "$got" = "$expect" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    FAILED_CASES+=("  redact want=$expect got=$got input='$inp' logged='$logged'")
  fi
  rm -rf "$tmp"
}

# Path segments — should NOT be redacted even if 32+ chars.
# Original bug: tempdir names like 'autopilot-eval-07-budget-tick-1d3jcl6o'
# (40 chars, all [A-Za-z0-9_-]) were being redacted as opaque tokens.
assert_redact KEEP   "/tmp/autopilot-eval-07-budget-tick-1d3jcl6o/src/db/users.ts"
# Real opaque secrets — MUST be redacted
assert_redact REDACT "sk-ant-api03-9aBcDeFgHiJkLmNoPqRsTuVwXyZ012345"
# Plain short paths — neither
assert_redact KEEP   "/tmp/foo.txt"
# Known limitation NOT asserted: paths with very long hyphen-rich
# segments (e.g. /home/user/some-long-project-name-with-hyphens-aaaa/...)
# can still have an inner substring redacted because \b matches at every
# hyphen. Perfect path-vs-token discrimination is beyond what this regex
# can do; the FIRST SECRET_PATTERN (api_key=, bearer=, etc.) is the real
# defense for labeled secrets, and the audit log isn't a security
# boundary regardless (ADR-0006).

# ===== v2-only: registry-driven yellow-tier nudge =====
# v1's irreversibility nudge was hardcoded in guard.mjs. v2 moves it to
# triggers/01-irreversibility.json and projects through emitNudge(). These
# cases verify the wire contract: exit 0, stdout is JSON with the
# `AUTOPILOT TRIGGER [<id>]` prefix in additionalContext, and that benign
# commands produce no nudge payload at all.
assert_nudge() {
  local expect="$1" cmd="$2"  # expect: NUDGE | NONE
  local payload out rc got
  payload=$(printf '{"tool_input":{"command":%s}}' "$(printf '%s' "$cmd" | json_escape)")
  out=$(echo "$payload" | node "$GUARD" pretool-bash 2>/dev/null)
  rc=$?
  if [ $rc -ne 0 ]; then
    FAIL=$((FAIL + 1))
    FAILED_CASES+=("  nudge want=$expect got=EXIT$rc cmd=$cmd")
    return
  fi
  if echo "$out" | grep -q 'AUTOPILOT TRIGGER \['; then got=NUDGE; else got=NONE; fi
  if [ "$got" = "$expect" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    FAILED_CASES+=("  nudge want=$expect got=$got cmd=$cmd out=$out")
  fi
}

# git push: matches the irreversibility trigger's bash_pattern → nudge.
assert_nudge NUDGE "git push origin main"
# Plain ls: no trigger matches → no stdout payload.
assert_nudge NONE  "ls -la"

# ===== Summary =====
TOTAL=$((PASS + FAIL))
echo
echo "autopilot hook tests: $PASS/$TOTAL passed"
if [ "$FAIL" -gt 0 ]; then
  echo
  echo "Failures:"
  printf '%s\n' "${FAILED_CASES[@]}"
  exit 1
fi
exit 0
