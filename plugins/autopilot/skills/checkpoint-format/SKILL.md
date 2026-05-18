---
name: checkpoint-format
description: Required format for AskUserQuestion calls during autopilot mode. Load before invoking AskUserQuestion in any autopilot-tier-2 pause.
---

# Checkpoint format

Every yellow-tier pause in [[autopilot]] mode uses AskUserQuestion. Never use prose questions for HITL gates.

## Required shape

Each AskUserQuestion call must include:

1. **Status preamble** (in the surrounding message, 1 line) — what you just did, past tense. *"Read auth.ts; noted the existing session-token flow."*
2. **The question** — concrete and specific. The actual decision the human needs to make.
3. **2–4 options**, each with:
   - A short label (≤ 5 words)
   - A one-line description: the *consequence* of choosing it
4. **Recommended option goes first** with "(Recommended)" appended to the label.

## Question types and templates

### Architectural choice

> question: "Should the new session store live in Redis or in the existing Postgres schema?"
> header: "Session store"
> - "Postgres (Recommended)" — reuses existing infra, no new ops surface
> - "Redis" — better latency, new dependency to monitor
> - "In-memory" — fastest, lost on restart

### Scope confirmation

> question: "Should I also refactor the related `tokenRefresh` helper, or leave for follow-up?"
> header: "Refactor scope"
> - "Leave for follow-up (Recommended)" — keeps this PR reviewable
> - "Refactor now" — one PR, more to review
> - "Refactor in a separate commit on this branch" — single PR, easy to revert

### Budget tick (~every 10 tool calls)

> question: "Still on track for [briefed goal]. Continue, or redirect?"
> header: "Checkpoint"
> - "Continue (Recommended)" — proceeding with [next concrete step]
> - "Redirect" — describe the new direction in notes

### Ambiguity resolution

> question: "The brief says 'fix the login bug'. I see two unrelated login issues — which did you mean?"
> header: "Which bug"
> - Option A — concrete description with file:line
> - Option B — concrete description with file:line
> - "Both" — fix both, longer-running task

### Pre-irreversible-action

> question: "Ready to push branch `feat/sessions` and open a PR?"
> header: "Push & PR"
> - "Push and open PR (Recommended)" — uses the auto-generated description below
> - "Push only" — you'll open the PR yourself
> - "Hold" — keep local, more changes coming

## Anti-patterns

- ❌ "Should I proceed?" — vague. Ask about the specific next choice.
- ❌ "Is this approach okay?" — describe two concrete approaches as options.
- ❌ Asking *after* you've done the thing — ask before, not after.
- ❌ More than 4 options — collapse, split, or pick a recommended default and offer "Other".
- ❌ Yes/no when there's a real third path — surface it as an option.
- ❌ Prose questions in chat instead of AskUserQuestion — breaks the structured HITL surface.
