# Web Engineering Playbook

A portable set of procedural standards for web-development projects of any framework, stack, or scale. Drop the relevant standards into your repo, fill in the project-specific values, and your contributors (human or AI) operate from a written contract instead of inferred convention.

---

## What this is

12 standards covering every developer-side concern that's universal to web projects — setup, git, review, testing, style, debugging, performance, accessibility, dependencies, security, decision records, AI agent collaboration. Each standard:

- **Anchored to an industry source.** WCAG, OWASP, Conventional Commits, Google SRE, etc. The standard restates the relevant parts and tells you where to verify and go deeper.
- **Framework-agnostic.** Works for React, Vue, Astro, Next.js, plain HTML/CSS, and most non-web stacks with minor adaptation.
- **Self-contained.** Read one standard, apply it to a project, without needing to read the other eleven first.
- **Pragmatic, not dogmatic.** Recommends a default + explains when to deviate.

---

## How to use it

### For a new project

```bash
# 1. Copy the standards you need into your repo
mkdir -p docs/playbook
cp -r hitl-playbook/standards docs/playbook/

# 2. Fill in the project-specific bits (each standard has a clearly
#    marked "PROJECT-SPECIFIC" section near the end).

# 3. Add a CONTRIBUTING.md pointing to docs/playbook/ as the entry.
```

You don't have to take all 12. Smallest viable adoption (for a personal site):

- `01-setup.md` — so others can run your project
- `02-git.md` — so commits and PRs are consistent
- `04-testing.md` — so changes don't break what works
- `10-security.md` — so secrets stay out of git

Largest viable adoption (for a multi-team SaaS):

- All 12 standards plus an ADR per significant architectural decision.

### For an existing project

Find which standards you already practice implicitly, write them down (lift onto the standard's "PROJECT-SPECIFIC" section), and migrate the rest opportunistically. Don't try to retrofit all 12 in one push — that's a recipe for shelved docs no one reads.

### For an AI agent

`standards/12-agents.md` is the entry point. It points at the rest in the order an agent needs them.

---

## The 12 standards

Grouped by tier. See [`SPEC.md`](./SPEC.md) for the full framework + how they relate.

### Foundation — daily-work procedures

| # | Standard | Covers |
|---|---|---|
| 01 | [Setup & onboarding](./standards/01-setup.md) | Fresh-clone-to-first-PR in ≤ 1 hour |
| 02 | [Git workflow](./standards/02-git.md) | Branches, commits, PRs, releases |
| 03 | [Code review](./standards/03-code-review.md) | Author + reviewer obligations; comment labels |
| 04 | [Testing](./standards/04-testing.md) | Test pyramid; what to test where; flake handling |

### Quality — standards work must meet

| # | Standard | Covers |
|---|---|---|
| 05 | [Code style](./standards/05-style.md) | Naming, file org, comments, when to extract |
| 06 | [Debugging](./standards/06-debugging.md) | Common failure modes + diagnosis methodology |
| 07 | [Performance](./standards/07-performance.md) | CWV, profiling, budgets, regression triage |
| 08 | [Accessibility](./standards/08-accessibility.md) | WCAG 2.2 AA workflow; automated + manual passes |

### Operations — ongoing health

| # | Standard | Covers |
|---|---|---|
| 09 | [Dependencies](./standards/09-dependencies.md) | Add / upgrade / triage; size + license + security |
| 10 | [Security](./standards/10-security.md) | OWASP Top 10; secrets; disclosure; CVE response |
| 11 | [Decision records (ADRs)](./standards/11-adrs.md) | Capture the "why" so it isn't re-litigated |
| 12 | [AI agent collaboration](./standards/12-agents.md) | Brief; verify; common failure modes from agent PRs |

---

## Project conventions

Files in this playbook follow the same conventions they advocate:

- **Markdown** with GitHub-flavored extensions (tables, task lists, fenced code).
- **Commits** follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) — see `02-git.md`.
- **Maintenance:** each standard names its own cadence at the bottom.

---

## Project-specific extensions

Beyond the 12 standards, this repo carries a Human-in-the-Loop (HITL) extension and a working Claude Code plugin that implements it:

- **[`docs/hitl-framework.md`](./docs/hitl-framework.md)** — HITL methodology extending standard 12 (AI agent collaboration). Three-tier action classification, checkpoint mechanics, briefing & handback protocol, etc.
- **[`docs/autopilot-plugin.md`](./docs/autopilot-plugin.md)** — Canonical reference for the autopilot plugin.
- **[`plugins/autopilot/`](./plugins/autopilot/)** — Installable Claude Code plugin (`/plugin install /path/to/plugins/autopilot`) that runs Claude in autonomous-with-checkpoints mode.
- **[`docs/adr/`](./docs/adr/)** — Architecture Decision Records for the HITL extension and plugin design.

These are optional extensions, not part of the playbook's core contract. Adopting projects can take the 12 standards without them.

---

## Versioning

Pre-1.0 right now. Once the 12 standards stabilize against feedback from real adopters, this will tag `v1.0.0` and follow [SemVer](https://semver.org) — breaking changes (added required content, renamed standard) bump major; additions (new standard, new section) bump minor; clarifications bump patch.

---

## Contributing back

This playbook is opinionated but not closed. If you adopt it on a project and find a standard's recommendation doesn't fit a real-world case, open an issue or PR with the counter-example. The "Maintenance" section at the bottom of each standard explains the change protocol.

---

## License

MIT. Use it, fork it, sell it, redistribute it. The intent is wide adoption of consistent procedural language across the web-dev ecosystem.
