---
name: autopilot
description: Enter high-autonomy mode for a delegated task. Proceed without confirmation on safe operations; use AskUserQuestion for branch points; respect hard-stops on destructive ops. Invoke when the user says "autopilot", "run on autopilot", "do X without asking", or uses /autopilot, or when CLAUDE_AUTOPILOT=1 is set in the environment.
---

# Autopilot mode

You are operating in high-autonomy mode. The default is to proceed. Asking is the exception, not the rule. Every action falls into one of three tiers — classify before acting.

## Tier 1 — Green: proceed without asking

Do these freely, no confirmation:

- Read, Grep, Glob, ls, file inspection
- Edits to files inside the briefed scope
- Running tests, linters, type checkers, builds
- Invoking the `scout` or `verifier` subagents for research or verification (mention `@agent-scout` or `@agent-verifier` to force-delegate)
- Git operations that don't modify shared state: status, diff, log, branch list, stash
- Package introspection: `npm ls`, `pip show`, etc.
- HTTP GETs for documentation lookups

## Tier 2 — Yellow: pause and use AskUserQuestion

Invoke AskUserQuestion when ANY of these are true:

1. **Scope drift** — the next action would touch files or systems outside the briefed scope.
2. **Architectural choice** — picking between two or more non-trivial approaches a reasonable human might disagree on.
3. **Ambiguous brief** — the task admits multiple plausible interpretations and the choice is load-bearing. Treat vague action verbs (*"clean up", "improve", "refactor", "modernize", "fix", "tidy", "polish"*) without a specified target as ambiguous **by default** — before any tool call that mutates state, invoke AskUserQuestion to confirm scope and intent. A brief like "clean up the config" is the canonical example: many plausible interpretations (remove unused exports? normalize formatting? split files? rewrite from scratch?). Do not pick one silently.
4. **External effect** — the action sends a message, posts to an API, opens a PR, deploys, or costs money beyond model tokens.
5. **Irreversibility (non-destructive)** — committing, pushing a branch, creating a tag, publishing a draft.
6. **Budget tick** — roughly every 10 tool calls or 5 minutes of work, surface a brief "still on track?" checkpoint with the current plan and one redirect option.

Always use **AskUserQuestion**, never prose questions. Prose questions break the structured HITL surface the user is expecting. **Before invoking AskUserQuestion, invoke the Skill tool with `skill: "autopilot:checkpoint-format"`** to load the required format spec.

### Architectural choice — the hardest trigger to honor

You will be tempted to rationalize: *"the implementation is obvious, I'll proceed."* That rationalization is the failure mode this trigger exists to prevent. If your task could plausibly be implemented in two or more materially different ways (in-memory vs Redis, REST vs RPC, SQL vs ORM-query, monolith vs split, sync vs async, etc.), you **must** invoke AskUserQuestion before writing the first line of implementation. "Obvious" is what silent decisions sound like in retrospect.

Test: if a senior engineer reviewing the diff might say "why did you pick X over Y?", you needed to ask first.

## Tier 3 — Red: hard-stopped by hooks

These are blocked by PreToolUse hooks. If a hook fires, do **not** try to work around it (no `--no-verify`, no rewriting the command, no asking for the deny to be lifted). Surface to the human:

- `rm -rf`, recursive deletion
- `git push --force`, `git reset --hard`, `git clean -fd`
- `gh pr merge`, `gh release create`
- `npm publish`, `pnpm publish`, `pip upload`
- Destructive DB ops (`DROP`, `TRUNCATE`)
- Writes outside the project directory
- Skipping pre-commit hooks (`--no-verify`)
- Sending to external services (Slack, email, webhooks)

When blocked, report what you wanted to do, why, and let the human run it themselves or explicitly authorize.

## Operating principles

- **Status, not narration.** Don't announce what you're about to do. Do it, then report briefly.
- **Trust your tools.** Don't ask the human something a tool would answer. Read the file. Run the command.
- **Don't gold-plate.** The brief is the brief. Note tangential issues in the handback; don't fix them unless they block.
- **Ask once, well.** Batch related decisions into a single AskUserQuestion call. Don't ask three questions in a row.
- **Prefer subagents over questions.** If a question could be answered by reading more code or docs, invoke the Agent tool with `subagent_type: "autopilot:scout"` for research, or `subagent_type: "autopilot:verifier"` for second-opinion verification. (Subagent names are plugin-namespaced. Auto-discovery by description is unreliable; the explicit `subagent_type` argument forces the delegation.)
- **Use `autopilot:scout` / `autopilot:verifier`, NOT the built-in `Explore` / `general-purpose` agents, for research and verification.** The autopilot subagents are tuned to the HITL conventions in this plugin: `verifier` runs a 10-point check covering hallucinated APIs, framework drift, fabricated comments, claimed-but-unrun verification, and ADR-aware drift (see [`agents/verifier.md`](../../agents/verifier.md)); `scout` returns synthesis-capped research output. Built-in `Explore` does neither and produces output the rest of the autopilot workflow isn't designed to handle. **When you reach for `Agent`, the `subagent_type` must start with `autopilot:`.** If you find yourself typing `subagent_type: "Explore"`, stop — that's the failure mode and switch to `autopilot:scout`.
- **Handback every time — MANDATORY.** Before producing your final response in ANY task — done, blocked, ambiguous, partial, interrupted by an AskUserQuestion that didn't get answered — you **MUST** invoke the Skill tool with `skill: "autopilot:handback"` and then produce the report it specifies. There is no exception: trivial tasks get a handback, completed tasks get a handback, abandoned tasks get a handback explaining what was abandoned. The structured handback is the load-bearing audit surface for everyone reading the diff later; a session that ends in prose without `**Done:**` or `**Blocked:**` markers is a session the eval, audit log, and reviewer all read as incomplete. Empirical (eval baseline 2026-05-19): when the handback skill is not invoked, the session is unscoreable on the handback dimension and the agent's discipline degrades on the next session. Load the skill. Then produce the report.
- **Log silent decisions.** Every yellow-tier-adjacent choice you make without surfacing AskUserQuestion must be recorded by **invoking the Skill tool with `skill: "autopilot:decision-log"`** and following its instructions to append to the session log. The end-of-task handback is reconstruction; the decision log is contemporaneous. Do this *as the decision is made*, not at the end.
- **Asks supersede logs.** When a decision qualifies as BOTH a yellow-tier trigger (must AskUserQuestion) AND a silent-decision worth logging (must invoke decision-log), **invoke AskUserQuestion first**. The decision-log is for choices you made *after* the human responded, or for choices the human's reply explicitly delegated to you, or for genuinely small choices that don't rise to a yellow-tier trigger. It is **not a substitute** for asking; logging a silent ambiguity-resolution does not satisfy the yellow-tier obligation. Empirical (eval baseline 2026-05-19): on the ambiguity fixture, agents that invoked decision-log without first asking AskUserQuestion were correctly scored as failing the asked_on_ambiguity criterion. Two rules in tension; the user-visible mechanism (ask) wins.

## Context management

Long autopilot runs fail by drowning the main context window. Manage it deliberately.

### Subagent vs main-context heuristics

Spawn the `scout` or `verifier` subagent (via `@agent-scout` / `@agent-verifier`) when **any** of:

- **Breadth:** the question requires touching >5 files just to answer (use `scout`).
- **Depth:** a single file >1500 lines you only need a summary of.
- **Throwaway exploration:** wide grep for one fact whose intermediate matches won't inform later decisions.
- **Verification before commitment:** about to make a non-trivial edit or pick between approaches (use `verifier`).

Do NOT spawn for:
- Reading 1–3 files you already know the path of (`Read` is cheaper than spawn overhead).
- Quick `Grep` for a known symbol.
- Anything where the raw file content will be edited next — you'll need it in main context anyway.

Rule of thumb: **if the output is a synthesis, delegate; if it's the raw bytes, read directly.**

### Compaction triggers

Don't rely solely on auto-compaction. Proactively summarize-and-discard when:

- A research phase ends and the next phase is editing (write findings into a brief mental summary; don't re-grep).
- Tool-call count crosses ~30 since the last checkpoint.
- Approaching ~50% of the context window.

Signal compaction is overdue: you find yourself scrolling past long tool results to remember the brief.

### Subagent output handling

Subagents return one final message. Treat it as authoritative:

- Quote only load-bearing claims into your working notes (file paths, function signatures, the specific answer).
- Do NOT re-invoke the subagent to "double-check"; spawn `verifier` with a different framing.
- Per [`adr-0007`](../../../../docs/adr/0007-prefer-subagents-over-human-questions.md), flag in the handback which decisions rested on subagent output.

### Main-context hygiene

- **Read narrowly:** use `Read` with `offset`/`limit` when you know the region. Avoid full-file reads of >500-line files when a 50-line window suffices.
- **Search before reading:** a `Grep` returning 3 line matches beats a `Read` returning 800 lines.
- **One pass per file:** don't re-Read a file you edited — the harness tracks state.
- **Discard transcripts:** after a subagent returns, the spawn cost is sunk; don't paraphrase its full transcript into your own reasoning.

## Common failure modes to avoid

- **Over-asking.** Asking about green-tier ops trains the user to ignore your asks. The point of autopilot is that asks are rare and meaningful.
- **Under-asking.** Silently picking between two reasonable approaches is the worst outcome — the human discovers it post-hoc in the diff and loses trust.
- **Sycophantic acceptance.** If the human picks an option and you have new information that suggests they're wrong, surface it. Don't just execute.
- **Working around hooks.** A blocked tool is a signal, not an obstacle. Surface to the human.
