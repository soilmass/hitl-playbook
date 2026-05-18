# 11 — Architecture Decision Records (ADRs)

**Purpose:** capture *why* significant decisions were made so they aren't silently re-litigated when the original people are gone.
**Anchors:** [Michael Nygard's ADR pattern (2011)](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) · [adr.github.io](https://adr.github.io) · [Joel Parker Henderson's ADR collection](https://github.com/joelparkerhenderson/architecture-decision-record)
**Tier:** Operations

---

## Why this procedure exists

The most expensive question in software is: "Why did we do it this way?" Without ADRs:

- A decision made in a PR comment 8 months ago has no findable record.
- New contributors propose changes that reverse the decision, requiring the original argument to be re-made (often poorly, since the original constraints are forgotten).
- Refactors that "modernize" the code lose the context that the original approach existed for good reasons.
- Tribal knowledge concentrates in a few heads; when those people leave, the project's reasoning leaves with them.

ADRs are a lightweight, durable, searchable record. Cost: 15 minutes per decision. Payoff: every future question that ADR answers without a round-trip.

**Failure modes when this procedure is missing:**

- "Why do we use Vue instead of React?" — answered by guessing.
- A new dev refactors the CSP nonce strategy "to simplify"; doesn't realize the complexity is intentional.
- The team makes the same architectural mistake twice because the first lesson wasn't written down.
- Decisions that should be reversible (because constraints changed) aren't, because nobody knows what the original constraints were.

---

## The standard

### What deserves an ADR

Not every decision needs one. ADRs are for decisions that:

- **Affect architecture or technology choice** (framework, database, hosting, language)
- **Establish a non-obvious convention** (we always X, never Y)
- **Trade off competing concerns** in a way that won't be obvious to future readers
- **Reverse a previous decision** (supersedes an earlier ADR)
- **Will be re-asked about** if not written down

NOT for:

- Style choices (lint rule debates)
- Implementation details that are obvious from the code
- Decisions you'd be happy to revisit at any time

A useful test: if a new contributor next year would ask "why this and not the obvious alternative?", write an ADR.

### Format — Michael Nygard's template

Each ADR is a short Markdown file: `docs/adr/NNNN-title-kebab-case.md`. Numbered sequentially.

```markdown
# NNNN. Title (verb + noun)

Date: YYYY-MM-DD

## Status

Proposed | Accepted | Deprecated | Superseded by ADR-NNNN

## Context

What's the situation? What constraints, requirements, or pressures are
forcing a decision? Don't argue here; describe.

## Decision

What did we decide? Active voice: "We will X."

## Consequences

What becomes easier? What becomes harder? What other decisions does
this constrain? Honest about trade-offs.
```

That's it. 4 sections. Most ADRs are 100–300 lines including code samples or links.

### Statuses

- **Proposed** — open for discussion; not yet decided.
- **Accepted** — the team agreed; the decision is in effect.
- **Deprecated** — no longer recommended but not actively replaced.
- **Superseded by ADR-NNNN** — a later ADR reverses or replaces this one. Both stay in the record.

ADRs are append-only. **Never delete an ADR**; if a decision changes, supersede it with a new one.

### Example

```markdown
# 0007. Use server-side rendering with hydration islands

Date: 2025-01-15

## Status

Accepted

## Context

We need to support:
- Strong SEO (every marketing page indexed)
- Sub-2s LCP on 4G mobile
- Some interactive components (forms, dialogs)
- Future scale to ~50 marketing pages without per-route hand-tuning

Pure SPA (everything client-rendered) tanks LCP and SEO. Pure SSG
(everything static) doesn't handle dynamic forms or per-user content.

## Decision

We will use Astro 5 with `output: "server"` and `export const prerender
= true` on marketing pages. Interactive components are React islands
hydrated with the lightest `client:*` directive that works.

## Consequences

Easier:
- SEO is correct by default — no extra rendering harness.
- LCP is fast on every marketing page because they're prerendered.
- Adding a new marketing page is one file.

Harder:
- New contributors need to understand the Astro/React island boundary.
- Some React libraries don't play well with SSR (window refs at module load).
- We commit to Astro's ecosystem; framework migration would be invasive.

Mitigation:
- Document the island boundary in our code-style standard.
- Inline a debug-gotcha for window-at-module-load in the debugging standard.
- Treat the framework choice as a long-term decision; revisit if Astro's
  trajectory changes (this ADR would then be superseded).
```

### When to write an ADR

Three triggers:

1. **A PR makes an architectural decision** — write the ADR before or alongside the PR. The PR description can link to the ADR.
2. **A discussion concludes with a decision** — even if no code change yet, capture the decision now. Memory fades fast.
3. **You're refactoring against an unwritten decision** — pause; write the ADR for the original choice; then either re-confirm or supersede with the new one.

### How ADRs interact with other docs

- **SPEC.md** — the canonical "what to build." ADRs explain "why this approach."
- **HANDOFF.md / CONTRIBUTING.md** — operating mechanics. ADRs underpin them.
- **Git commit messages** — for small "why"; ADRs are for large "why."
- **Code comments** — for hyper-local "why this line"; ADRs for cross-cutting "why this approach."

### ADR storage and discovery

- Directory: `docs/adr/` (or `docs/decisions/`, `decisions/`, etc. — pick one)
- Numbering: zero-padded 4-digit (`0001-`, `0002-`, …) — sorts correctly in `ls`
- Filename: number + kebab-case title (`0007-use-server-side-rendering-with-hydration-islands.md`)
- Index: `docs/adr/README.md` listing all ADRs by number with title and status. Optional but useful for discovery.

Tools that automate ADR creation:

- [`adr-tools`](https://github.com/npryce/adr-tools) — Bash CLI
- [`adr-manager`](https://github.com/adr/adr-manager) — web UI
- [`madr`](https://adr.github.io/madr/) — Markdown variant with richer metadata

### Common mistakes

- **ADRs that argue.** They should record what was decided, not litigate it. Move the argument to the PR / issue.
- **ADRs that are too long.** Over ~500 lines = too much detail. Link to supporting docs.
- **ADRs that get amended in place.** If you change the decision, *supersede*, don't edit. The original ADR is the historical record.
- **ADRs for trivial decisions.** Every dependency upgrade doesn't need an ADR.
- **Backfilling ADRs for every prior decision.** Write going forward. Backfill only the decisions still load-bearing.

---

## PROJECT-SPECIFIC — fill these in

```markdown
## ADR location

Path: docs/adr/

## Naming convention

NNNN-kebab-case-title.md (4-digit zero-padded number)

## Index

[Either a docs/adr/README.md listing all ADRs, OR rely on alphabetical ls]

## What deserves an ADR on this project

[Project-specific examples — e.g., "framework choice, hosting choice,
data model, security architecture, third-party integrations >$X/month"]

## Template

[Either copy the Nygard format above, or link to a project template file]

## ADR-1: <first ADR title>

[Brief list of ADRs by number + status + title]
```

---

## Cross-references

- [`02-git.md`](./02-git.md) — PR descriptions link to their ADRs
- [`05-style.md`](./05-style.md) — style decisions worth preserving become ADRs
- [`11-adrs.md`](./11-adrs.md) — meta: this very standard is an ADR pattern
- [`12-agents.md`](./12-agents.md) — agents read ADRs to understand project context

External:
- [Michael Nygard: Documenting Architecture Decisions (2011)](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) — the original
- [adr.github.io](https://adr.github.io) — collection of ADR resources
- [Joel Parker Henderson: ADR examples + templates](https://github.com/joelparkerhenderson/architecture-decision-record)
- [Spotify Engineering: How we structure decisions](https://engineering.atspotify.com/2020/04/when-should-i-write-an-architecture-decision-record/)
- [ThoughtWorks Tech Radar: ADRs](https://www.thoughtworks.com/radar/techniques/lightweight-architecture-decision-records) — "Adopt" rating

---

## Maintenance cadence

- **Per significant decision:** write the ADR within 1 week of the decision.
- **Per PR that touches architecture:** link the ADR in the PR description.
- **Quarterly:** review the ADR list. Any "Accepted" ADRs that no longer reflect reality? Either supersede or mark deprecated.
- **Annually:** add an entry to the project's main README pointing to `docs/adr/`.
- **Owner:** the project's tech lead owns the format; every contributor owns the ADRs for their own decisions.
