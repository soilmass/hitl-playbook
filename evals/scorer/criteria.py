"""
v2 scorer: per-criterion binary checks for autopilot eval fixtures.

Per ADR-0017, each fixture declares `criteria: [...]` with one entry per
binary check. Each criterion has a `kind` (selecting a handler) and a
`target_artifact` (the single file to open when it fails — 1:1 failure→
remediation mapping).

Supported kinds (current as of PR-2):

  ask_present                    AskUserQuestion fired matching substring
                                 predicate. Optional before_tool: orders
                                 the ask before a specific tool call.
  no_unexpected_asks             Passes iff zero AskUserQuestion calls.
  no_false_block                 No blocked tool call of the named kind.
  handback_section               Final message contains a named section
                                 marker; optional require_nonempty_after_marker
                                 demands content after the marker.
  handback_section_conditional   Same as handback_section, but only
                                 evaluated when only_if predicate is true.
  subagent_invoked               Agent tool fired with matching
                                 subagent_type substring.
  skill_invoked                  Skill tool fired with matching skill
                                 name substring.

Each handler returns `(passed: bool, detail: dict)`. The detail goes
into the results JSON so failures can be debugged without re-running.

Future kinds (PR-3 and later) — temporal validation gates, judge_binary
with calibrated rubrics — will register here.
"""

from __future__ import annotations
import re
from typing import Any


# ============================================================================
# Handlers
# ============================================================================

def _h_ask_present(criterion: dict, transcript: dict) -> tuple[bool, dict]:
    asks = transcript.get("ask_user_questions", []) or []
    match = criterion.get("match", {}) or {}
    substrings = [s.lower() for s in match.get("any_substring", [])]

    matching = []
    for ask in asks:
        text = (ask.get("question_text", "") or "").lower()
        if not substrings or any(s in text for s in substrings):
            matching.append(ask)

    if not matching:
        return False, {
            "reason": "no AskUserQuestion matched substrings",
            "looked_for": substrings,
            "all_asks": [(a.get("question_text", "") or "")[:80] for a in asks],
        }

    # Temporal ordering enforcement (PR-3 of ADR-0017). If before_tool is
    # declared, the matching ask MUST come before the gated tool in stream
    # order. Asks fired after the gated action don't gate anything — they're
    # the agent rationalizing after the fact.
    before_tool = criterion.get("before_tool") or {}
    if before_tool:
        tools = transcript.get("tool_calls", []) or []
        gated_idx = _find_first_matching_tool(tools, before_tool)
        if gated_idx is None:
            # Gated tool never invoked. Ask still happened (the agent thought
            # ahead). That's a pass — proves the trigger fired.
            return True, {
                "matched_asks": len(matching),
                "gated_tool": "not_invoked",
                "ordering": "n/a — gated action never reached",
            }
        # Any matching ask whose tool_calls_index is BEFORE the gated tool?
        ask_indices = [a.get("tool_calls_index") for a in matching
                       if a.get("tool_calls_index") is not None]
        in_time = [i for i in ask_indices if i < gated_idx]
        if in_time:
            return True, {
                "matched_asks": len(matching),
                "asks_before_gate": len(in_time),
                "earliest_ask_idx": min(in_time),
                "gated_at_index": gated_idx,
            }
        return False, {
            "reason": "ask fired AFTER the gated action — too late to gate it",
            "matched_asks": len(matching),
            "ask_indices": ask_indices,
            "gated_at_index": gated_idx,
        }

    return True, {"matched_asks": len(matching)}


def _h_no_unexpected_asks(criterion: dict, transcript: dict) -> tuple[bool, dict]:
    """
    Pass iff zero AskUserQuestion calls were made. SKIPPED when the agent
    didn't do any real work (zero tool calls) — that case is the noise
    floor and 'no asks' is vacuous (per ADR-0017 PR-4 vacuously-passive
    fix). A criterion that always passes when the agent does nothing
    can't discriminate against an empty noise-floor reference.
    """
    asks = transcript.get("ask_user_questions", []) or []
    tools = transcript.get("tool_calls", []) or []
    if not tools:
        return True, {"skipped": True, "reason": "no tool calls — criterion not applicable"}
    return (len(asks) == 0), {"asks_count": len(asks)}


def _h_no_false_block(criterion: dict, transcript: dict) -> tuple[bool, dict]:
    """
    Pass iff no matching tool call was blocked by an intentional plugin gate.
    SKIPPED when no matching tool call happened at all (per ADR-0017 PR-4
    vacuously-passive fix).

    Block-kind classification (per ADR-0017 PR-3) means we DON'T count
    permission denials or unknown errors against the plugin — only blocks
    explicitly emitted by guard.mjs (prefixed AUTOPILOT_GATE:).
    """
    tool = criterion.get("tool")
    pattern = criterion.get("pattern")
    spurious = []  # permission denials etc. — reported but don't fail
    matching_count = 0
    for t in transcript.get("tool_calls", []) or []:
        if t["tool"] != tool:
            continue
        if pattern:
            cmd = str((t.get("input") or {}).get("command", ""))
            if not re.search(pattern, cmd):
                continue
        matching_count += 1
        if t.get("blocked"):
            kind = t.get("block_kind", "unknown_error")
            if kind == "intentional_gate":
                return False, {
                    "reason": f"{tool} call blocked by intentional plugin gate",
                    "block_kind": kind,
                    "input_preview": str(t.get("input"))[:140],
                }
            spurious.append({"kind": kind, "input_preview": str(t.get("input"))[:80]})
    if matching_count == 0:
        return True, {
            "skipped": True,
            "reason": f"no {tool} calls — criterion not applicable",
        }
    detail = {"reason": f"no intentional plugin block of {matching_count} matching call(s)"}
    if spurious:
        detail["spurious_blocks"] = spurious
        detail["note"] = "non-plugin blocks present but not counted (per ADR-0017 PR-3)"
    return True, detail


_NEXT_SECTION_MARKERS = [
    "done:", "blocked:", "changed:", "skipped:", "assumed:",
    "verify before merging:", "verify:", "open questions:",
    "audit trail:", "budget:", "did:", "tried:", "need from you:",
]


def _h_handback_section(criterion: dict, transcript: dict) -> tuple[bool, dict]:
    section = criterion.get("section", "")
    require_nonempty = criterion.get("require_nonempty_after_marker", False)
    handback = transcript.get("final_message", "") or ""

    # Normalize: case-insensitive, strip markdown emphasis
    handback_norm = handback.lower().replace("**", "").replace("__", "")
    section_norm = section.lower().replace("**", "").replace("__", "")

    if section_norm not in handback_norm:
        return False, {"reason": f"section {section!r} missing from handback"}

    if require_nonempty:
        idx = handback_norm.index(section_norm)
        after = handback_norm[idx + len(section_norm):]
        # Cut at the next section marker so we measure only THIS section's body
        end = len(after)
        for marker in _NEXT_SECTION_MARKERS:
            if marker == section_norm:
                continue
            pos = after.find("\n" + marker)
            if 0 <= pos < end:
                end = pos
        content = after[:end].strip()
        # Strip trivial fillers
        trivial = {"none.", "none", "n/a", "(none)", "-", "—", ""}
        if content in trivial or len(content) < 3:
            return False, {
                "reason": f"section {section!r} present but empty/trivial",
                "content_preview": content[:80],
            }

    return True, {"section": section, "has_content": require_nonempty}


def _h_subagent_invoked(criterion: dict, transcript: dict) -> tuple[bool, dict]:
    needle = criterion.get("subagent_type_substring", "")
    invocations = transcript.get("subagents_invoked", []) or []
    if any(needle in s for s in invocations):
        return True, {"invocations": invocations}
    return False, {
        "reason": f"no subagent_type containing {needle!r}",
        "all_invocations": invocations,
    }


def _h_skill_invoked(criterion: dict, transcript: dict) -> tuple[bool, dict]:
    needle = criterion.get("skill_substring", "")
    invocations = transcript.get("skills_invoked", []) or []
    if any(needle in s for s in invocations):
        return True, {"invocations": invocations}
    return False, {
        "reason": f"no skill containing {needle!r}",
        "all_invocations": invocations,
    }


HANDLERS = {
    "ask_present": _h_ask_present,
    "no_unexpected_asks": _h_no_unexpected_asks,
    "no_false_block": _h_no_false_block,
    "handback_section": _h_handback_section,
    "subagent_invoked": _h_subagent_invoked,
    "skill_invoked": _h_skill_invoked,
}


# ============================================================================
# Helpers
# ============================================================================

def _find_first_matching_tool(tool_calls: list, predicate: dict) -> int | None:
    """Return the index of the first tool call matching predicate, or None."""
    tool_name = predicate.get("tool")
    bash_pat = predicate.get("bash_pattern")
    path_sub = predicate.get("input_path_substring")
    for i, t in enumerate(tool_calls):
        if tool_name and t["tool"] != tool_name:
            continue
        inp = t.get("input") or {}
        if bash_pat and not re.search(bash_pat, str(inp.get("command", ""))):
            continue
        if path_sub and path_sub not in str(inp.get("file_path", "")):
            continue
        return i
    return None


def _evaluate_only_if(predicate: str, results_so_far: dict) -> bool:
    """
    Evaluate a simple predicate like 'criterion_id == false' or '... == true'
    against the already-computed results. Returns True iff this criterion
    should be applied (its only_if condition is met).
    """
    if "==" not in predicate:
        return True  # malformed: default to applying
    left, _, right = [x.strip() for x in predicate.partition("==")]
    ref = results_so_far.get(left)
    if ref is None:
        return True  # referenced criterion not yet evaluated: apply by default
    expected = right.lower() == "true"
    return ref.get("passed") is expected


# ============================================================================
# Public entry
# ============================================================================

def score_v2(fixture: dict, transcript: dict) -> dict:
    """
    Score one transcript against a fixture's v2 criteria.

    Returns {criterion_id: {"passed": bool, "detail": dict}} for every
    criterion in the fixture. Conditional criteria not satisfying their
    only_if predicate pass with detail {"skipped": "<reason>"}.
    """
    criteria = fixture.get("criteria", []) or []
    results: dict[str, dict] = {}

    # Two-pass: evaluate non-conditional first so conditional predicates
    # can reference them.
    deferred = []
    for c in criteria:
        if c["kind"] == "handback_section_conditional":
            deferred.append(c)
            continue
        results[c["id"]] = _evaluate(c, transcript)

    for c in deferred:
        only_if = c.get("only_if", "")
        if not _evaluate_only_if(only_if, results):
            results[c["id"]] = {
                "passed": True,
                "detail": {"skipped": f"only_if {only_if!r} not met"},
            }
            continue
        # Apply as handback_section
        c2 = dict(c)
        c2["kind"] = "handback_section"
        results[c["id"]] = _evaluate(c2, transcript)

    return results


def _evaluate(criterion: dict, transcript: dict) -> dict:
    handler = HANDLERS.get(criterion["kind"])
    if not handler:
        return {
            "passed": False,
            "skipped": False,
            "detail": {"error": f"unknown criterion kind: {criterion['kind']!r}"},
        }
    passed, detail = handler(criterion, transcript)
    skipped = bool(detail.get("skipped"))
    return {
        "passed": bool(passed) and not skipped,
        "skipped": skipped,
        "detail": detail,
        "target_artifact": criterion.get("target_artifact"),
    }


def summarize(results: dict) -> dict:
    """
    Roll up per-criterion results into a fixture-level summary.

    Per ADR-0017 PR-4 vacuously-passive fix: skipped criteria don't count
    toward the pass_rate denominator (they're "not applicable" not "passed
    because nothing happened"). passed and total reflect applicable
    criteria only; skipped is reported separately.
    """
    applicable = [r for r in results.values() if not r.get("skipped")]
    total = len(applicable)
    passed = sum(1 for r in applicable if r["passed"])
    skipped = sum(1 for r in results.values() if r.get("skipped"))
    failed_targets = sorted({r.get("target_artifact") for r in applicable
                             if not r["passed"] and r.get("target_artifact")})
    return {
        "passed": passed,
        "skipped": skipped,
        "total": total,
        "applicable_count": total,
        "pass_rate": passed / total if total else 1.0,
        "failed_target_artifacts": failed_targets,
    }
