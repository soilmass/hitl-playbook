#!/usr/bin/env python3
"""
autopilot eval runner.

Runs a task fixture suite against the live `claude` CLI with the autopilot
plugin installed, parses the resulting transcript, and scores against
fixture expectations. Writes results to evals/results/<version>-<ts>.json.

Prereqs: claude CLI authenticated, pyyaml (and `anthropic` if using the
Sonnet judge — optional).

Limitation by design (see docs/adr/0014):
  AskUserQuestion does not work in `claude --print` mode (no interactive
  user to answer). The eval measures INTENT — whether the agent called
  AskUserQuestion at the right moments — not response. The tool_result
  comes back as is_error, the agent then reverts to prose; we count the
  call itself as the signal.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("install pyyaml: pip install pyyaml")

# v2 scorer (per ADR-0017) — dual-write alongside v1 composite.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scorer import criteria as crit_v2  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "evals" / "results"


# ============================================================================
# Driver — invoke claude --print, capture stream-json, parse to dict.
# ============================================================================

class FixtureSetupError(RuntimeError):
    """Raised when a fixture's setup_commands fail. Per ADR-0017 PR-4,
    setup failures are NOT confused with low scores — they're a
    distinct SETUP_FAILED status surfaced in the results JSON."""


def _setup_workspace(fixture: dict) -> Path:
    """
    Create an isolated cwd for one task run, seeded with any files
    declared in the fixture's optional `setup:` block (path+content pairs)
    and any shell commands in `setup_commands:` (run sequentially after
    files exist; used for `git init`, dependency install, etc.).

    Setup commands run with check=True (per ADR-0017 PR-4) so silent
    failures (e.g., git init not running) surface as FixtureSetupError
    rather than corrupting downstream scoring with confused signal.
    """
    work_dir = Path(tempfile.mkdtemp(prefix=f"autopilot-eval-{fixture['id']}-"))
    for entry in fixture.get("setup", []) or []:
        path = work_dir / entry["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(entry.get("content", ""))
    for cmd in fixture.get("setup_commands", []) or []:
        result = subprocess.run(
            cmd, shell=True, cwd=work_dir, check=False, capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise FixtureSetupError(
                f"fixture {fixture.get('id')} setup_command failed: {cmd!r}\n"
                f"  exit={result.returncode}\n"
                f"  stdout: {result.stdout.strip()[:300]}\n"
                f"  stderr: {result.stderr.strip()[:300]}"
            )
    return work_dir


def _run_claude_task(
    brief: str,
    plugin_root: Path,
    model: str = "haiku",
    max_budget_usd: float = 0.20,
    timeout: int = 300,
    extra_setup_dir: Path = None,
    allowed_tools: list = None,
    fixture_env: dict = None,
    no_plugin: bool = False,
) -> dict:
    """
    Run one task via `claude --print` and return the parsed transcript.

    `allowed_tools` is a list of strings passed via --allowedTools. Use it
    in fixtures that need specific Bash commands the agent must be able to
    invoke without prompting (e.g. fixture 05 needs `Bash(git *)` so the
    irreversibility trigger has a chance to fire).
    """
    work_dir = extra_setup_dir or Path(tempfile.mkdtemp(prefix="autopilot-eval-bare-"))
    cmd = [
        "claude", "--print",
        "--output-format", "stream-json",
        "--verbose",
        "--include-hook-events",
        "--max-budget-usd", str(max_budget_usd),
        "--model", model,
        "--permission-mode", "acceptEdits",
    ]
    # --baseline-mode noplugin omits --plugin-dir so the run is "what
    # would claude do without the autopilot plugin at all?" — the
    # noise-floor reference per ADR-0017 PR-4. Per-criterion deltas
    # whose CI crosses 0 between with-plugin and no-plugin indicate
    # a non-discriminating fixture (it can't tell whether the plugin
    # helps).
    if not no_plugin:
        cmd += ["--plugin-dir", str(plugin_root)]
    if allowed_tools:
        # --allowedTools is variadic (<tools...>) and slurps subsequent args
        # including the brief. Use `--` to terminate the option list.
        cmd += ["--allowedTools"] + list(allowed_tools) + ["--", brief]
    else:
        cmd.append(brief)
    env = {
        **os.environ,
        "CLAUDE_AUTOPILOT": "1",
        "CLAUDE_PROJECT_DIR": str(work_dir),
        **(fixture_env or {}),
    }
    proc = subprocess.run(
        cmd, cwd=work_dir, env=env, capture_output=True, text=True, timeout=timeout
    )
    return _parse_stream_json(proc.stdout, work_dir)


def _parse_stream_json(stream: str, work_dir: Path) -> dict:
    """
    Parse Claude Code's stream-json output into the shape score_task expects.

    Actual shape (verified live via dogfood probes 2026-05-18):
      - {type:"system", subtype:"init", ...}       — session init
      - {type:"system", subtype:"hook_*", ...}     — hook lifecycle
      - {type:"assistant", message:{content:[      — agent turn
            {type:"text", text:...},               — prose
            {type:"tool_use", name:..., input:...} — tool calls
        ]}}
      - {type:"user", message:{content:[           — tool results back
            {type:"tool_result", is_error:bool, content:...}
        ]}}
      - {type:"result", subtype:"success", total_cost_usd:..., result:...}
    """
    tool_calls = []        # ordered list of {tool, input, blocked, result}
    ask_questions = []     # AskUserQuestion calls (treated as the "asks")
    subagents_invoked = [] # subagent_type strings from Agent tool calls
    skills_invoked = []    # skill name strings from Skill tool calls
    final_message = ""
    cost_usd = 0.0
    hook_blocks = 0
    session_id = ""

    # Map tool_use_id -> position in tool_calls so we can attach the result.
    tu_id_to_idx = {}
    # Most-recent hook_response.stderr keyed by hook_id, so we can attribute
    # an exit-2 block to its actual stderr message (for block classification).
    hook_stderr_by_id = {}

    for line in stream.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue

        t = evt.get("type")
        s = evt.get("subtype", "")

        if t == "system" and s == "init":
            session_id = evt.get("session_id", "")

        elif t == "system" and s == "hook_response":
            # Track stderr for every hook_response (not just exit 2) so we
            # can correlate with tool_result.is_error later. PR-3 per
            # ADR-0017.
            hid = evt.get("hook_id", "")
            if hid:
                hook_stderr_by_id[hid] = evt.get("stderr", "") or ""
            if evt.get("exit_code") == 2:
                hook_blocks += 1

        elif t == "assistant":
            for blk in evt.get("message", {}).get("content", []) or []:
                if blk.get("type") == "tool_use":
                    idx = len(tool_calls)
                    tool_calls.append({
                        "tool": blk.get("name", ""),
                        "input": blk.get("input", {}),
                        "blocked": False,  # filled in when we see the result
                        "tool_use_id": blk.get("id", ""),
                    })
                    if blk.get("id"):
                        tu_id_to_idx[blk["id"]] = idx
                    if blk.get("name") == "AskUserQuestion":
                        for q in blk.get("input", {}).get("questions", []):
                            ask_questions.append({
                                "question_text": q.get("question", ""),
                                "options": q.get("options", []),
                                # Position in tool_calls — temporal ordering signal
                                # for the v2 ask_present criterion (PR-3 / ADR-0017).
                                "tool_calls_index": idx,
                                # Note: the v1 'category' field was deleted in PR-8
                                # along with _classify_ask. The v2 ask_present criterion
                                # matches on question_text substrings directly.
                            })
                    elif blk.get("name") == "Agent":
                        st = blk.get("input", {}).get("subagent_type", "")
                        if st:
                            subagents_invoked.append(st)
                    elif blk.get("name") == "Skill":
                        sk = blk.get("input", {}).get("skill", "")
                        if sk:
                            skills_invoked.append(sk)
                elif blk.get("type") == "text":
                    # The last text block is the agent's final message.
                    final_message = blk.get("text", "")

        elif t == "user":
            for blk in evt.get("message", {}).get("content", []) or []:
                if blk.get("type") == "tool_result":
                    tu_id = blk.get("tool_use_id", "")
                    idx = tu_id_to_idx.get(tu_id)
                    if idx is not None and blk.get("is_error"):
                        tool_calls[idx]["blocked"] = True
                        # Classify the block source (per ADR-0017 PR-3) using
                        # any hook stderr we captured + the tool_result content
                        # as fallback. Stored as block_kind on the tool_call.
                        from scorer.blocks import classify_block
                        # Use most-recent hook stderr — heuristic, but the
                        # block typically immediately follows its hook_response.
                        last_hook_stderr = next(
                            iter(reversed(list(hook_stderr_by_id.values()))), ""
                        )
                        content_text = ""
                        if isinstance(blk.get("content"), str):
                            content_text = blk["content"]
                        elif isinstance(blk.get("content"), list):
                            content_text = " ".join(
                                str(c.get("text", "")) for c in blk["content"]
                                if isinstance(c, dict)
                            )
                        tool_calls[idx]["block_kind"] = classify_block(
                            last_hook_stderr, content_text
                        )

        elif t == "result":
            cost_usd = float(evt.get("total_cost_usd", 0.0))
            # Prefer the final structured result if it exists.
            if evt.get("result"):
                final_message = evt["result"]

    return {
        "tool_calls": tool_calls,
        "ask_user_questions": ask_questions,
        "subagents_invoked": subagents_invoked,
        "skills_invoked": skills_invoked,
        "final_message": final_message,
        "cost_usd": cost_usd,
        "hook_blocks": hook_blocks,
        "session_id": session_id,
        "work_dir": str(work_dir),
    }


# ============================================================================
# v1 scoring REMOVED in PR-8 (per ADR-0017). Use scorer.criteria.score_v2
# directly. Past results JSON files retain their v1 composite scores for
# back-compat reading by compare-runs.py --schema v1 (also deprecated).
# ============================================================================


# ============================================================================
# CLI
# ============================================================================

def run_suite(
    version: str,
    tasks_dir: Path,
    runs: int,
    plugin_root: Path,
    model: str,
    max_budget_usd: float,
    keep_work_dirs: bool,
    filter_substr: str = None,
    no_plugin: bool = False,
):
    results = {
        "version": version,
        "model": model,
        "ts": datetime.now(timezone.utc).isoformat(),
        "tasks": {},
        "total_cost_usd": 0.0,
    }

    total_cost = 0.0
    fixture_paths = sorted(tasks_dir.glob("*.yaml"))
    if filter_substr:
        fixture_paths = [p for p in fixture_paths if filter_substr in p.name]
        if not fixture_paths:
            sys.exit(f"no fixture in {tasks_dir} matched filter '{filter_substr}'")
    for fixture_path in fixture_paths:
        fixture = yaml.safe_load(fixture_path.read_text())
        task_id = fixture["id"]
        per_run = []
        print(f"\n{task_id}: {fixture.get('purpose','')[:80]}")
        for i in range(runs):
            work = _setup_workspace(fixture)
            try:
                t0 = time.time()
                transcript = _run_claude_task(
                    fixture["brief"], plugin_root,
                    model=model, max_budget_usd=max_budget_usd,
                    extra_setup_dir=work,
                    allowed_tools=fixture.get("allowed_tools"),
                    fixture_env=fixture.get("env"),
                    no_plugin=no_plugin,
                )
                # v2-only scoring (PR-8 removed v1). Per-criterion binary
                # checks; pass/fail/skipped semantics per ADR-0017.
                score = {
                    "cost_usd": round(transcript.get("cost_usd", 0.0), 4),
                    "asks": len(transcript["ask_user_questions"]),
                    "tools": len(transcript["tool_calls"]),
                    "hook_blocks": transcript.get("hook_blocks", 0),
                    "subagents": transcript.get("subagents_invoked", []),
                    "skills": transcript.get("skills_invoked", []),
                    "final_message": transcript.get("final_message", ""),
                    "tool_summary": [
                        {"tool": t["tool"], "input_preview": str(t.get("input"))[:120]}
                        for t in transcript.get("tool_calls", [])[:30]
                    ],
                    "schema_version": 2,
                }
                if fixture.get("criteria"):
                    v2_results = crit_v2.score_v2(fixture, transcript)
                    score["criteria_v2"] = v2_results
                    score["criteria_v2_summary"] = crit_v2.summarize(v2_results)
                total_cost += score["cost_usd"]
                per_run.append(score)
                v2_summary = score.get("criteria_v2_summary") or {}
                v2_str = (f" v2={v2_summary['passed']}/{v2_summary['total']}"
                          if v2_summary else "")
                print(f"  run {i+1}:{v2_str}  asks={score['asks']} tools={score['tools']} "
                      f"hook_blocks={score['hook_blocks']} cost=${score['cost_usd']:.4f} "
                      f"({time.time()-t0:.1f}s)")
            except FixtureSetupError as e:
                per_run.append({"note": "SETUP_FAILED", "error": str(e), "schema_version": 2})
                print(f"  run {i+1}: SETUP_FAILED — {str(e).splitlines()[0]}")
            except subprocess.TimeoutExpired:
                per_run.append({"note": "timeout", "schema_version": 2})
                print(f"  run {i+1}: TIMEOUT")
            except Exception as e:
                per_run.append({"note": f"error: {e}", "schema_version": 2})
                print(f"  run {i+1}: ERROR {e}")
            finally:
                if not keep_work_dirs:
                    shutil.rmtree(work, ignore_errors=True)
        results["tasks"][task_id] = per_run

    results["total_cost_usd"] = round(total_cost, 4)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / f"{version}-{int(time.time())}.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"\nTotal cost: ${total_cost:.4f}")
    print(f"Wrote {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True, help="label for this run (e.g. HEAD, baseline)")
    ap.add_argument("--tasks", default=str(REPO_ROOT / "evals" / "tasks"))
    ap.add_argument("--runs", type=int, default=1, help="runs per task")
    ap.add_argument("--plugin-root", default=str(REPO_ROOT / "plugins" / "autopilot"))
    ap.add_argument("--model", default="haiku", help="claude model (haiku|sonnet|opus)")
    ap.add_argument("--max-budget-usd", type=float, default=0.20, help="per-task cost cap")
    ap.add_argument("--keep-work-dirs", action="store_true", help="don't delete per-task tmpdirs")
    ap.add_argument("--filter", help="only run fixtures whose filename contains this substring (e.g. '02' or 'scope')")
    ap.add_argument("--baseline-mode", choices=["with-plugin", "noplugin"], default="with-plugin",
                    help="noplugin: omit --plugin-dir for the noise-floor reference baseline (ADR-0017 PR-4)")
    args = ap.parse_args()
    # NOTE: PR-8 (per ADR-0017) removed the v1 composite scorer and the
    # --judge flag. v2 scoring (per-criterion binary checks in
    # evals/scorer/criteria.py) is the only scorer. Judge-based criteria
    # are now per-rubric via judge_binary kind (see evals/judge/).
    run_suite(
        args.version, Path(args.tasks), args.runs, Path(args.plugin_root),
        args.model, args.max_budget_usd, args.keep_work_dirs,
        filter_substr=args.filter,
        no_plugin=(args.baseline_mode == "noplugin"),
    )


if __name__ == "__main__":
    main()
