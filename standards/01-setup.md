# 01 — Setup & Onboarding

**Purpose:** a new contributor (human or AI) gets from fresh clone to passing local build in ≤ 1 hour.
**Anchor:** no single industry spec; closest is [The Twelve-Factor App](https://12factor.net) on configuration (factor III) and dev/prod parity (factor X).
**Tier:** Foundation

---

## Why this procedure exists

The cost of bad onboarding is invisible and compounding. Each new contributor wastes 1–8 hours fighting environment issues; multiply that by every new hire, every fresh agent session, every dev who returns to the project after a month away. The team builds knowledge nobody writes down ("oh, you need Node 20 specifically, the package-lock breaks on 18 and 22") and the cost falls entirely on newcomers.

**Failure modes when this procedure is missing:**

- Newcomer can't run the project locally, asks in chat, gets a piecemeal answer, struggles for a day.
- A version-pinning issue surfaces only on certain machines; "works on my machine" becomes the default debug response.
- AI agents make wrong assumptions about the stack (e.g., the [PR #9 incident](https://github.com/soilmass/architect-homes/pull/9) — Vercel agent assumed Next.js and added Next-specific imports to an Astro project).
- Production env vars that should be in `.env.example` are documented only in Slack DMs.

A standard setup doc costs ~2 hours to write and saves that for every subsequent contributor.

---

## The standard

### Required content

The setup document MUST cover:

1. **System prerequisites** — exact versions of language runtime + package manager.
2. **OS-specific gotchas** — what's different on macOS vs. Linux vs. Windows/WSL.
3. **Clone + install** — one command per step, copy-pasteable.
4. **Environment variables** — `.env.example` template + how to obtain real values.
5. **Verify-it-works** — a single command that confirms the install is good.
6. **First task** — pointer to a tiny, low-risk change someone can make to test the full loop (branch → commit → push → PR).

### Required structure

```markdown
## Prerequisites
- Node 20.x (use `.nvmrc` — `nvm use` if you have nvm)
- pnpm 9.x — `corepack enable && corepack prepare pnpm@9 --activate`
- Optional: Playwright system deps (Linux only) — `sudo pnpm playwright install-deps`

## Install
git clone <repo-url>
cd <repo>
pnpm install --frozen-lockfile

## Environment
cp .env.example .env.local
# Fill in the values — see comments in .env.example for sources.

## Verify
pnpm verify        # type + lint + format check
pnpm dev           # http://localhost:<port>
pnpm test          # full test suite

## Your first PR
1. Branch: `git checkout -b chore/onboarding-test`
2. Make a trivial change (fix a typo in README).
3. `pnpm verify && pnpm build`
4. Commit per <link to git workflow standard>
5. Push and open a PR per <link to git workflow standard>
6. Wait for CI green; squash-merge.
```

### Required artifacts in the repo

- `.nvmrc` — pins the Node version.
- `.npmrc` or `.yarnrc.yml` or `.pnpm-workspace.yaml` — pins the package manager.
- `.env.example` — every env var the project uses, with comments naming the source/vendor.
- `package.json` `engines` field — declarative version constraints (matches `.nvmrc`).
- A "verify" script in `package.json` that runs the same gates CI runs locally.

### Common variations with trade-offs

| Variation | When | Trade-off |
|---|---|---|
| **Devcontainer / Codespaces** | Complex setup or many platforms | High setup cost; saves time for newcomers but requires Docker familiarity |
| **Nix / direnv** | Reproducible across machines + over years | Steeper learning curve; powerful for long-lived projects |
| **`make setup` wrapper** | Multi-step or scriptable | Hides what's happening; easier for newcomers but harder to debug |
| **No version pinning** | Strict freshness | Frequent breaks; never recommended for production projects |

### Failure modes the doc should mitigate

Document the three things that bite most often for your specific stack:

- **Node version mismatch** — error is usually `SyntaxError` or `ReferenceError`. Mitigation: pin in `.nvmrc` + `package.json engines`.
- **Native dependencies missing** (Playwright, sharp, esbuild) — error varies wildly. Mitigation: explicit `apt install` / `brew install` line in setup.
- **Missing env vars** — Astro/Vite often fail silently (`undefined` propagates to HTML). Mitigation: required env vars validated at startup; fail fast with named error.

---

## PROJECT-SPECIFIC — fill these in

When you adopt this standard for a project, paste the standard's structure and fill in:

```markdown
## Prerequisites

- Node <VERSION> (specifically: [why this version])
- <PACKAGE_MANAGER> <VERSION>
- <OPTIONAL DEPS: e.g., Playwright system libs, Docker, Postgres>
- macOS: [any specific notes]
- Linux: [any specific notes]
- Windows/WSL: [any specific notes; or "not supported, use WSL2"]

## Install

[Exact commands, in order]

## Environment

[How to obtain each env var, with a note on which vendor's dashboard]

Required vars:
- <VAR_1>: [purpose, where to get it]
- ...

## Verify

[One command that confirms everything works. Should return exit code 0.]

## Common gotchas

[The 3-5 things that have actually bitten contributors on this project.]
```

---

## Cross-references

- [`02-git.md`](./02-git.md) — what to do after install
- [`04-testing.md`](./04-testing.md) — what `pnpm verify` and `pnpm test` actually run
- [`12-agents.md`](./12-agents.md) — agents read this file first to understand the stack

---

## Maintenance cadence

- **Quarterly:** re-run the setup on a fresh machine (or fresh container) and confirm the steps still produce a working install. Setup docs rot silently.
- **After every onboarding:** the new contributor should add a line for anything they hit that wasn't in the doc.
- **On major dependency upgrades:** update the version numbers + verify.
- **Owner:** the most recent contributor to have onboarded successfully.
