# Web Engineering Playbook — Specification

**Status:** v0.1 — initial draft. Stabilizes to v1.0.0 once at least three real projects have fully adopted it and reported back.
**Scope:** developer-side procedural standards for web projects, framework-agnostic.
**Out of scope:** product strategy, design systems, hiring, vendor management, legal/compliance. Those are real concerns but not what this playbook addresses.

---

## Why this exists

Most web projects accumulate convention by accident. A developer makes a decision; the next developer follows the implicit pattern; six months later nobody can articulate the rule but everyone breaks it occasionally, and reviewers spend energy litigating the same issues that were already settled.

A written, shared, standards-anchored procedural framework prevents this. The cost is the initial write-up; the saving is every subsequent decision that doesn't require a round-trip discussion.

This playbook is the framework that document set should follow. It defines:

- **The 12 universal developer procedures** every web project has, whether documented or not.
- **The relationships between them** — which procedures inform which, where they hand off.
- **The minimum-viable-doc per procedure** so a project can adopt the standard without rewriting it from scratch.
- **The industry anchor** for each, so the standard is verifiable against an authoritative source.

A project adopts the playbook by copying the relevant standards, filling in the project-specific values, and treating the result as the canonical reference.

---

## The 12 procedures

| # | Standard | Tier | One-line purpose |
|---|---|---|---|
| 01 | [Setup & onboarding](./standards/01-setup.md) | Foundation | New contributor productive in ≤ 1 hour |
| 02 | [Git workflow](./standards/02-git.md) | Foundation | Commits, branches, PRs, releases follow a single convention |
| 03 | [Code review](./standards/03-code-review.md) | Foundation | Reviews catch the right issues without becoming a bottleneck |
| 04 | [Testing](./standards/04-testing.md) | Foundation | Changes don't regress what works |
| 05 | [Code style](./standards/05-style.md) | Quality | Codebase reads as if one person wrote it |
| 06 | [Debugging](./standards/06-debugging.md) | Quality | Common failure modes have known diagnoses |
| 07 | [Performance](./standards/07-performance.md) | Quality | Core Web Vitals stay in the green |
| 08 | [Accessibility](./standards/08-accessibility.md) | Quality | WCAG 2.2 AA holds for every user |
| 09 | [Dependencies](./standards/09-dependencies.md) | Operations | Third-party code stays current, audited, and small |
| 10 | [Security](./standards/10-security.md) | Operations | OWASP Top 10 + supply chain + disclosure path |
| 11 | [Decision records](./standards/11-adrs.md) | Operations | "Why" is captured before memory fades |
| 12 | [AI agent collaboration](./standards/12-agents.md) | Operations | Agents brief from facts, not hallucination |

---

## The three tiers

### Foundation (1–4): how work happens

These four define the daily-work loop: get set up → branch → write code → review → merge → release. Every project needs all four. Without them, contributors invent their own workflow and nothing is reproducible.

### Quality (5–8): standards work must meet

These four define what "done" means for a code change. Code that compiles isn't necessarily done — it has to meet style, performance, accessibility, and be diagnosable when it breaks. These standards are gates the Foundation procedures hand work into.

### Operations (9–12): ongoing health

These four define how the project stays healthy after the work ships. Dependencies decay, security threats evolve, decisions need re-explaining, and AI collaborators arrive. Without operations procedures, a project that shipped well still rots quietly.

---

## How they link

```
                    ┌───────────────────────────────────────┐
                    │           FOUNDATION                  │
                    │                                       │
              ┌─────┤  01 Setup ─► 02 Git ─► 03 Review      │
              │     │      └─► 04 Testing  ◄──┘             │
              │     └──────────────┬────────────────────────┘
              │                    │
              │                    ▼  every PR is gated by
              │     ┌──────────────────────────────────────┐
              │     │            QUALITY                   │
              │     │                                      │
              │     │  05 Style    07 Performance          │
              │     │  06 Debug    08 Accessibility        │
              │     └──────────────┬───────────────────────┘
              │                    │
              │                    ▼  ongoing maintenance via
              │     ┌──────────────────────────────────────┐
              │     │           OPERATIONS                 │
              │     │                                      │
              │     │  09 Dependencies   11 ADRs           │
              │     │  10 Security       12 AI Agents      │
              │     └──────────┬───────────────────────────┘
              │                │
              └────────────────┘  feedback loop: ops findings
                                  update Foundation + Quality
```

### Specific cross-references between standards

| From | To | Why |
|---|---|---|
| 01 Setup | 02 Git | After install, first thing a contributor does is branch |
| 02 Git | 03 Review | Every PR triggers review |
| 02 Git | 04 Testing | Tests run on every push (CI) and before every merge |
| 03 Review | 05 Style + 07 Perf + 08 A11y | Reviewers check work against these standards |
| 04 Testing | 06 Debugging | Failing tests are debugged via the diagnostic methodology |
| 04 Testing | 07 + 08 | Perf + a11y are testable; tests enforce the gates |
| 05 Style | 11 ADRs | Style decisions worth preserving become ADRs |
| 09 Dependencies | 10 Security | Dependency upgrades are the most common security vector |
| 10 Security | 02 Git | Security paths have stricter CODEOWNERS / review rules |
| 11 ADRs | All standards | ADRs document deviations from the playbook defaults |
| 12 AI Agents | All standards | Agents read all standards as project context |

---

## Adoption levels

Not every project needs every standard. Pick the right level for your project's stage and scale.

### Level 1 — Personal site / weekend project

Minimum viable. Take these 4:

- `01-setup.md` (so the project can still run in 6 months when you've forgotten)
- `02-git.md` (so your commit history is readable)
- `04-testing.md` (at the level of "smoke test before deploy")
- `10-security.md` (no secrets in git, basic header hygiene)

Skip the rest. Add them when the project grows.

### Level 2 — Small production site (1–3 contributors)

Add to Level 1:

- `03-code-review.md` (when you have collaborators, even part-time)
- `08-accessibility.md` (legal exposure for public sites; ethical imperative regardless)
- `09-dependencies.md` (CVE response within a documented SLA)

### Level 3 — Mature small team (4–15 contributors)

Add to Level 2:

- `05-style.md` (review bottleneck starts to bite without it)
- `06-debugging.md` (knowledge transfer becomes harder; common gotchas need writing down)
- `07-performance.md` (real users on real networks; SLO discipline matters)
- `11-adrs.md` (decisions get re-litigated as new contributors arrive)

### Level 4 — AI-augmented team (any size, agents in the loop)

Add to your existing level:

- `12-agents.md` (mandatory — agents need explicit context or they invent it)

---

## Standard structure

Each of the 12 standard documents follows the same template so they're predictable:

### 1. Title + purpose (~30 lines)

- One-sentence purpose
- Industry anchor (with link)
- One-paragraph "why this exists" (the failure mode it prevents)

### 2. Why this procedure (~60 lines)

- The class of problem it solves
- Common failure modes when it's absent
- The hidden cost of not having it

### 3. The standard (~150 lines)

- The universal procedure (framework-agnostic)
- Concrete examples
- Common variations with trade-offs

### 4. Project-specific filling (~50 lines)

- Template for the project's own version
- Marked sections like `[PROJECT-SPECIFIC: list your CI status check names here]`

### 5. Cross-references (~10 lines)

- Pointers to other standards that connect to this one
- External canonical sources

### 6. Maintenance cadence (~10 lines)

- How often to review the standard itself
- Who owns updates
- Change protocol

Total ~300 lines per standard. Total framework: ~3600 lines across 12 standards + ~500 lines spec + ~150 lines README = ~4250 lines.

---

## Industry anchors

Each standard is anchored to at least one authoritative external source. The playbook restates the relevant parts but defers to the canonical when there's a conflict. Per standard:

| Standard | Primary anchor(s) |
|---|---|
| 01 Setup | [12factor.net](https://12factor.net) (config); no single setup spec exists |
| 02 Git | [Conventional Commits](https://www.conventionalcommits.org) · [SemVer](https://semver.org) · [GitHub Flow](https://docs.github.com/en/get-started/quickstart/github-flow) |
| 03 Review | [Google Engineering Practices](https://google.github.io/eng-practices/review/) · [Conventional Comments](https://conventionalcomments.org) |
| 04 Testing | [Mike Cohn test pyramid](https://martinfowler.com/articles/practical-test-pyramid.html) · [Testing Library principles](https://testing-library.com/docs/guiding-principles) |
| 05 Style | [Google Style Guides](https://google.github.io/styleguide/) · framework-specific guides |
| 06 Debugging | None universal — captures stack-specific patterns |
| 07 Performance | [web.dev/vitals](https://web.dev/vitals) · [Lighthouse CI](https://github.com/GoogleChrome/lighthouse-ci) |
| 08 Accessibility | [WCAG 2.2](https://www.w3.org/TR/WCAG22/) · [WAI-ARIA APG](https://www.w3.org/WAI/ARIA/apg/) |
| 09 Dependencies | [npm audit](https://docs.npmjs.com/cli/v10/commands/npm-audit) · [SPDX license list](https://spdx.org/licenses/) · [OSV.dev](https://osv.dev) |
| 10 Security | [OWASP Top 10](https://owasp.org/Top10/) · [OWASP Cheat Sheets](https://cheatsheetseries.owasp.org/) · [RFC 9116](https://www.rfc-editor.org/rfc/rfc9116.html) |
| 11 ADRs | [Michael Nygard's ADR](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) · [adr.github.io](https://adr.github.io) |
| 12 AI Agents | [agents.md](https://agents.md) (emerging convention) |

---

## Maintenance of this playbook itself

The playbook is meta-versioned (SemVer). Changes to the playbook should:

1. Be opened as a PR against this repo, not silently amended in a downstream project.
2. Cite the real-world case that prompted the change.
3. Update the affected standard(s) + bump version.
4. Tag a release with notes.

Cadence:

- **Per standard:** owners review the standard yearly, more often if their domain (e.g., WCAG version bump) changes.
- **The framework:** annual review by the project maintainer to consider whether new procedure categories deserve standards (e.g., observability, feature flags, ML/AI tooling).

---

## Out of scope (explicit)

This playbook does not address:

- **Product / business strategy** — what to build, for whom. That's a separate discipline.
- **Design systems** — visual language, brand. Touches code style but a full design system is its own framework (Material, Carbon, etc.).
- **Hiring and team structure** — interviewing, leveling, performance management.
- **Vendor procurement** — choosing Vercel vs. Netlify vs. CloudFlare. Project-specific.
- **Compliance** (GDPR, CCPA, SOC 2) — touches security (`10-security.md`) but full compliance programs need legal review beyond what code-procedures cover.
- **Operational runbooks** (incident response, on-call, SLO management) — touches Quality but full ops practice belongs in a separate ops playbook anchored to [Google SRE](https://sre.google/sre-book/).

If your project needs any of the above, treat this playbook as a complement, not a replacement.
