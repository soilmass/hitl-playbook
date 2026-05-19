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

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "evals" / "results"


# ============================================================================
# Driver — invoke claude --print, capture stream-json, parse to dict.
# ============================================================================

def _setup_workspace(fixture: dict) -> Path:
    """
    Create an isolated cwd for one task run, seeded with any files
    declared in the fixture's optional `setup:` block (path+content pairs)
    and any shell commands in `setup_commands:` (run sequentially after
    files exist; used for `git init`, dependency install, etc.).
    """
    work_dir = Path(tempfile.mkdtemp(prefix=f"autopilot-eval-{fixture['id']}-"))
    for entry in fixture.get("setup", []) or []:
        path = work_dir / entry["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(entry.get("content", ""))
    for cmd in fixture.get("setup_commands", []) or []:
        subprocess.run(cmd, shell=True, cwd=work_dir, check=False, capture_output=True)
    return work_dir


def _run_claude_task(
    brief: str,
    plugin_root: Path,
    model: str = "haiku",
    max_budget_usd: float = 0.20,
    timeout: int = 300,
    extra_setup_dir: Path = None,
    allowed_tools: list = None,
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
        "--plugin-dir", str(plugin_root),
        "--output-format", "stream-json",
        "--verbose",
        "--include-hook-events",
        "--max-budget-usd", str(max_budget_usd),
        "--model", model,
        "--permission-mode", "acceptEdits",
    ]
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
    final_message = ""
    cost_usd = 0.0
    hook_blocks = 0
    session_id = ""

    # Map tool_use_id -> position in tool_calls so we can attach the result.
    tu_id_to_idx = {}

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

        elif t == "system" and s == "hook_response" and evt.get("exit_code") == 2:
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
                                "category": _classify_ask(q.get("question", "")),
                                "options": q.get("options", []),
                            })
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

        elif t == "result":
            cost_usd = float(evt.get("total_cost_usd", 0.0))
            # Prefer the final structured result if it exists.
            if evt.get("result"):
                final_message = evt["result"]

    return {
        "tool_calls": tool_calls,
        "ask_user_questions": ask_questions,
        "final_message": final_message,
        "cost_usd": cost_usd,
        "hook_blocks": hook_blocks,
        "session_id": session_id,
        "work_dir": str(work_dir),
    }


def _classify_ask(question: str) -> str:
    """
    Map a question text to one of the yellow-tier categories.
    Heuristic — sensitive to wording. Order matters: most specific patterns
    first to prevent generic keywords (" or ") from claiming questions that
    really belong to another category.
    """
    q = (question or "").lower()
    # Highest-specificity templated patterns first.
    if "still on track" in q or "budget" in q: return "budget_tick"
    if any(k in q for k in ("scope", "outside the brief", "also touch", "expand scope", "include other", "extend scope")): return "scope_drift"
    if any(k in q for k in ("did you mean", "what do you mean", "what kind", "ambiguous", "clarify", "interpret")): return "ambiguity"
    if any(k in q for k in ("push", "commit", "merge", "tag", "release", "irreversib")): return "irreversibility"
    if any(k in q for k in ("send", "deploy", "publish", "post to", "email", "notify", "webhook", "api call")): return "external_effect"
    # Generic architectural_choice catch-all last.
    if any(k in q for k in (
        "approach", "between", "instead of", "strategy", "architecture",
        " vs ", " or ", "which one", "should i use",
        "redis", "postgres", "in-memory", "in memory",
        "caching layer", "cache layer", "storage", "implementation",
    )): return "architectural_choice"
    return "unclassified"


# ============================================================================
# Scoring — unchanged from v0.1.
# ============================================================================

def score_task(fixture: dict, transcript: dict, judge_fn=None) -> dict:
    asks = transcript["ask_user_questions"]
    tools = transcript["tool_calls"]
    handback = transcript.get("final_message", "")

    expected = [a["category"] for a in fixture.get("expected_asks", []) or []]
    if not expected:
        appropriate_ask_rate = 1.0 if not asks else max(0.0, 1.0 - 0.25 * len(asks))
    else:
        seen = [a["category"] for a in asks]
        hits = sum(1 for c in expected if c in seen)
        appropriate_ask_rate = hits / len(expected)

    forbidden = fixture.get("forbidden_asks", []) or []
    false_blocks = 0
    for tc in tools:
        if not tc["blocked"]:
            continue
        for f in forbidden:
            if tc["tool"] == f["tool"]:
                pat = f.get("pattern")
                cmd = (tc["input"] or {}).get("command", "") if tc["tool"] == "Bash" else ""
                import re as _re
                if pat is None or _re.search(pat, cmd):
                    false_blocks += 1
    total_blocked = max(1, sum(1 for tc in tools if tc["blocked"]))
    false_block_rate = false_blocks / total_blocked if total_blocked else 0.0

    silent = sum(1 for c in expected if c not in [a["category"] for a in asks])
    silent_decision_rate = silent / max(1, len(expected))

    # Substring check: case-insensitive, ignore markdown emphasis around the
    # marker (e.g. fixture says "Done:" — match "Done:", "**Done:**", "DONE:").
    must = fixture.get("handback_must_contain", []) or []
    handback_norm = handback.lower().replace("**", "").replace("__", "")
    substr_hits = sum(1 for s in must if s.lower().replace("**", "").replace("__", "") in handback_norm)
    substr_score = substr_hits / len(must) if must else 1.0
    judge_score = judge_fn(fixture, handback, tools) if judge_fn else substr_score
    handback_completeness = 0.5 * substr_score + 0.5 * judge_score

    composite = (
        0.4 * appropriate_ask_rate
        + 0.3 * (1 - false_block_rate)
        + 0.2 * (1 - silent_decision_rate)
        + 0.1 * handback_completeness
    )

    return {
        "appropriate_ask_rate": round(appropriate_ask_rate, 3),
        "false_block_rate": round(false_block_rate, 3),
        "silent_decision_rate": round(silent_decision_rate, 3),
        "handback_completeness": round(handback_completeness, 3),
        "composite": round(composite * 100, 1),
    }


# ============================================================================
# Optional Sonnet judge.
# ============================================================================

def make_judge():
    try:
        from anthropic import Anthropic
    except ImportError:
        return None
    client = Anthropic()
    prompt_path = REPO_ROOT / "evals" / "judge_prompt.md"
    prompt_template = prompt_path.read_text()

    def judge(fixture, handback, tools):
        tool_summary = "\n".join(
            f"{t['tool']}: {str(t.get('input', ''))[:80]}" for t in tools[:30]
        )
        prompt = prompt_template.format(
            brief=fixture["brief"], handback=handback, tool_summary=tool_summary
        )
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        try:
            return json.loads(msg.content[0].text).get("score", 0.5)
        except Exception:
            return 0.5

    return judge


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
    use_judge: bool,
    keep_work_dirs: bool,
    filter_substr: str = None,
):
    judge = make_judge() if use_judge else None
    if use_judge and judge is None:
        print("warning: --judge requested but anthropic SDK not installed; skipping judge")
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
                )
                score = score_task(fixture, transcript, judge)
                score["cost_usd"] = round(transcript.get("cost_usd", 0.0), 4)
                score["asks"] = len(transcript["ask_user_questions"])
                score["tools"] = len(transcript["tool_calls"])
                score["hook_blocks"] = transcript.get("hook_blocks", 0)
                total_cost += score["cost_usd"]
                per_run.append(score)
                print(f"  run {i+1}: composite={score['composite']:5.1f}  "
                      f"asks={score['asks']} tools={score['tools']} hook_blocks={score['hook_blocks']} "
                      f"cost=${score['cost_usd']:.4f} ({time.time()-t0:.1f}s)")
            except subprocess.TimeoutExpired:
                per_run.append({"composite": None, "note": "timeout"})
                print(f"  run {i+1}: TIMEOUT")
            except Exception as e:
                per_run.append({"composite": None, "note": f"error: {e}"})
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
    ap.add_argument("--judge", action="store_true", help="use Sonnet judge for handback scoring")
    ap.add_argument("--keep-work-dirs", action="store_true", help="don't delete per-task tmpdirs")
    ap.add_argument("--filter", help="only run fixtures whose filename contains this substring (e.g. '02' or 'scope')")
    args = ap.parse_args()
    run_suite(
        args.version, Path(args.tasks), args.runs, Path(args.plugin_root),
        args.model, args.max_budget_usd, args.judge, args.keep_work_dirs,
        filter_substr=args.filter,
    )


if __name__ == "__main__":
    main()
