# 12 — AI Agent Collaboration

**Purpose:** AI agents (Claude Code, Cursor, Copilot, Vercel agent, etc.) operate from explicit project context, not from defaults or hallucination.
**Anchors:** [agents.md (emerging convention)](https://agents.md) · vendor-specific docs (Anthropic, OpenAI, Google, Cursor, etc.)
**Tier:** Operations

---

## Why this procedure exists

AI agents are entering the development workflow whether you plan for them or not. They open PRs, propose refactors, suggest fixes, fill in test scaffolding. Without project-specific guidance, they default to whichever framework they were trained most heavily on (often Next.js for web) and apply patterns that may not match yours.

A real example: the Vercel agent opened a PR on an Astro 5 project to "Install Vercel Web Analytics" — but used the Next.js entry point (`@vercel/analytics/next`) and placed `inject()` in the Astro frontmatter (server-side), where it can't work. Two real bugs in one auto-generated PR. The fix is to give agents the context they need before they open the PR, not after.

**Failure modes when this procedure is missing:**

- Agents add Next-isms to non-Next projects
- Agents re-add configuration the project already has
- Agents bypass project conventions (commit message format, branch naming, hard rules)
- Agents apply security patches without considering the project's threat model
- Agents propose refactors that contradict existing ADRs
- Reviewers spend time triaging agent PRs that could have been right-first-time

---

## The standard

### The `AGENTS.md` convention

A growing industry pattern: a sibling to `README.md` at the repo root, written specifically as context for AI agents. (`README.md` is for humans; `AGENTS.md` is the same project but framed for an AI's first pass.)

Minimum content:

```markdown
# AGENTS.md

Project: <name>
Stack: <framework + version + hosting + key vendors>
Conventions doc index: <links to SPEC.md, HANDOFF.md, git.md, this playbook>

## Hard rules — do not violate

- <Concrete prohibitions; reference the source of authority>
- e.g., "Do not add `'unsafe-inline'` to CSP. See `10-security.md`."
- e.g., "Do not invent customer-facing copy. Owner provides content."

## Stack specifics

- Framework: <e.g., Astro 5, not Next.js. Server output via @astrojs/vercel.>
- Why this matters: <e.g., Astro frontmatter runs server-side; client-only
  code goes in `<script>` blocks or React islands.>
- Common pitfalls: <e.g., Don't import client-side libraries at module top
  level — breaks SSR.>

## Existing configuration (don't re-add)

- Web Analytics: enabled via `webAnalytics: { enabled: true }` in `astro.config.ts`
- Error monitoring: Sentry conditional on `SENTRY_DSN` env var
- Observability: OpenTelemetry via `@vercel/otel`
- <List anything an agent might "helpfully" re-implement>

## How to verify before opening a PR

1. Read `SPEC.md` and the relevant standards in `docs/playbook/standards/`.
2. Run `pnpm verify && pnpm build` locally.
3. Confirm the change doesn't duplicate existing configuration.
4. Confirm the change runs in the correct execution context (server vs. client).
5. Check that imports use the correct framework's entry point.

## Conventions to follow

- Commits: Conventional Commits per `git.md`
- Branches: `<type>/<short-description>`
- PRs: fill the auto-populated template; don't skip sections

## Failure-mode case studies

[Real examples of agent PRs that went wrong + the lesson]

- PR #N: <link>. <what went wrong>. <lesson learned>.
```

### Briefing an agent

When you task an agent with work, the briefing should include:

1. **What to build** — the concrete goal, not the abstract problem
2. **Stack context** — framework + version + key constraints
3. **Existing conventions** — naming, commit format, branch flow
4. **Hard rules** — what NOT to do
5. **Where to verify** — link to the standards / docs that govern this work
6. **Acceptance criteria** — how the agent (and you) know it's done

Example briefing:

> Implement [`docs/MONTANA_OWNER_INPUTS.md`](...) item #B1: scaffolding for a per-project case-study route at `/portfolio/[bucket]/[project]`. Astro 5 + content collections + Zod. Follow `git.md` for commit and PR conventions. Don't invent customer-facing copy — placeholder MDX should have `ownerSupplied: false`. Cross-reference `src/content/config.ts` for the existing collection patterns.

vs. the bad version:

> Add case studies

### Verifying agent output

Agent PRs deserve the same review depth as human PRs. Don't approve on autopilot just because an agent "from Vercel" or "from Anthropic" generated it.

Verification checklist (covered in [`03-code-review.md`](./03-code-review.md), plus agent-specific items):

- [ ] Does it follow project commit + branch conventions?
- [ ] Does it duplicate existing configuration?
- [ ] Does the import path match this project's framework (not the framework the agent's training data favored)?
- [ ] Does the code run in the correct execution context (server / client / build)?
- [ ] Does it violate any hard rule listed in `AGENTS.md`?
- [ ] Does it match this project's environmental conditionals (e.g., Sentry only when DSN is set, OTel only when configured)?
- [ ] Are agent-introduced comments accurate (not restating things the agent assumed)?

If multiple checkboxes fail, close the PR with a comment explaining the gaps. Future agents (reading the closed PR thread) get the context.

### Common agent failure modes

#### Framework mis-application

Agent assumes Next.js / React / generic Node patterns and applies them to Astro / Vue / Svelte / Solid. Often manifests as:

- Wrong import subpath (`@pkg/next` instead of `@pkg/astro`)
- Code placed in the wrong execution context (frontmatter vs. client script)
- Missing or extra hydration directives

**Mitigation:** in `AGENTS.md`, name the framework + version + key SSR/client boundaries explicitly.

#### Re-implementing existing configuration

Agent doesn't read the existing config and adds the same thing twice. Common with analytics, logging, error monitoring.

**Mitigation:** in `AGENTS.md`, list the existing configurations with a "don't re-add" header.

#### Inventing customer-facing copy

Agent adds plausible-sounding marketing copy, tagline, testimonials, etc. Often well-written but inaccurate.

**Mitigation:** explicit "Do not invent customer-facing copy" rule in `AGENTS.md`.

#### Bypassing review by approving its own PR

Some agent integrations have approval permissions. Lock them down.

**Mitigation:** branch protection requires CODEOWNERS approval; agent isn't in CODEOWNERS.

#### Refactoring against existing ADRs

Agent proposes a "cleaner" approach that contradicts a load-bearing architectural decision.

**Mitigation:** `AGENTS.md` points at `docs/adr/`. Agent should read the relevant ADRs before proposing structural changes.

### Multi-agent workflows

When multiple agents work on a project (e.g., one for coding, one for review, one for testing):

- Each agent reads `AGENTS.md` at session start.
- Hand-offs happen via PR comments or commit messages, not inferred state.
- The human stays in the loop on architectural decisions (those go to ADRs).

### Permissions for AI agents

When granting an agent repository access:

- **Read** is safe.
- **Write to branches other than `main`** is fine for PR-based workflows.
- **Merge to `main`** — never auto-merge agent PRs without human review.
- **Branch protection enforcement** — required for `main`; agents shouldn't bypass.
- **Secrets access** — minimize. An agent that needs API keys for some external service should use scoped tokens with expiry.

### Attribution

When an AI agent meaningfully contributes to a commit, attribute via `Co-authored-by:`:

```
Co-authored-by: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
Co-authored-by: GitHub Copilot <noreply@github.com>
```

This is honest record-keeping. It's not legally required in most contexts but it's good practice.

---

## PROJECT-SPECIFIC — fill these in

```markdown
## AGENTS.md location

Path: <repo root>

## Agents currently working on this project

- <e.g., Claude Code (Anthropic) — owner-driven development>
- <e.g., GitHub Copilot — autocomplete in IDE>
- <e.g., Dependabot — dependency updates>
- <e.g., Vercel agent — vendor integration suggestions>

## Permissions matrix

[Per-agent: what each can do]

## Hard rules (lift the top 5-10 into AGENTS.md verbatim)

- <Rule 1>
- <Rule 2>
- ...

## Stack-specific context for agents

- Framework: <name + version>
- Common agent mistakes for this stack: <list>
- Existing configuration (don't re-add): <list>

## Verification before merging an agent PR

[The checklist from this standard, customized.]

## Failure-mode case studies (your real examples)

- PR #<num>: <link>. <what happened>. <lesson>.
```

---

## Cross-references

- [`02-git.md`](./02-git.md) — agents follow the same git workflow as humans
- [`03-code-review.md`](./03-code-review.md) — agent PRs reviewed with same depth
- [`11-adrs.md`](./11-adrs.md) — agents respect existing ADRs; new agent-proposed architecture changes become new ADRs

External:
- [agents.md](https://agents.md) — emerging convention site
- [Anthropic: Claude Code](https://www.anthropic.com/news/introducing-claude-code)
- [OpenAI: Code Interpreter / SWE-Bench](https://openai.com/index/openai-codex/)
- [Google: Jules](https://jules.google.com/)
- [GitHub Copilot docs](https://docs.github.com/en/copilot)
- [Cursor docs](https://cursor.sh/docs)

---

## Maintenance cadence

- **Per agent PR that goes wrong:** add to the failure-mode case studies section.
- **Quarterly:** review the AGENTS.md against current agent landscape — new agents, new failure modes, new conventions.
- **On framework upgrade:** update stack-specific context (e.g., Astro 5 → 6 might change agent guidance).
- **When new agent joins the workflow:** add to the permissions matrix; brief on the project; first PR gets extra-close review.
- **Owner:** the project's tech lead.
