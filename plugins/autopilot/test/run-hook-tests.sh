#!/usr/bin/env bash
# Hook regression suite for the autopilot plugin guard.
# Runs the LIVE guard.mjs against fixture cases. No regex duplication —
# if the guard changes, this suite catches regressions.
#
# Usage: bash plugins/autopilot/test/run-hook-tests.sh
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
  local rc
  printf '{"tool_input":{"file_path":"%s"}}' "$path" | node "$GUARD" pretool-write >/dev/null 2>&1
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
