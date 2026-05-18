# 09 — Dependencies

**Purpose:** third-party code stays current, audited, size-budgeted, and license-compliant.
**Anchors:** [npm audit](https://docs.npmjs.com/cli/v10/commands/npm-audit) · [SPDX License List](https://spdx.org/licenses/) · [OSV.dev](https://osv.dev) · [Dependabot docs](https://docs.github.com/en/code-security/dependabot)
**Tier:** Operations

---

## Why this procedure exists

Every dependency is a bet that someone else will maintain it. Sometimes the bet pays off (React); sometimes it doesn't (left-pad). Without explicit hygiene:

- **CVEs accumulate.** A package with a known critical vulnerability sits in `package.json` for months because nobody owns triage.
- **Bundle bloat goes unnoticed.** A 200KB library gets added to do a job a 10-line function would handle.
- **License obligations are missed.** GPL code in a proprietary project; missing attribution; license incompatibility at deploy time.
- **Major version drift.** The team avoids upgrading because "nobody knows what'll break"; six months later the gap is too big to cross safely.
- **Supply-chain attacks.** Compromised packages (event-stream, ua-parser-js) ship malicious code; an updated dependency hijacks the build.

A standard converts dependency management from ad-hoc to procedural.

---

## The standard

### Three questions before adding any dependency

Every `npm install <new-package>` should be a decision, not a reflex.

1. **Do we need it?** Can we do this in 10–50 lines of our own code? Smaller is almost always easier to maintain than a dep with its own surface area, bugs, and bundle cost.
2. **Is it healthy?** Recent releases? Active issues being addressed? Reasonable test coverage? Documentation? Last commit in the last 6 months?
3. **Is the cost acceptable?** Size (gzipped, on [Bundlephobia](https://bundlephobia.com)), runtime overhead, peer dep complexity, license compatibility.

If the answer to any is no, don't add it. Write the 30 lines yourself.

### Pinning strategy

Three options:

| Strategy | Example | When |
|---|---|---|
| **Exact** | `"react": "19.0.0"` | Production projects where reproducibility > automatic updates. Use with Dependabot for managed upgrades. |
| **Caret** | `"react": "^19.0.0"` | Libraries you publish; signals SemVer compatibility. |
| **Tilde** | `"react": "~19.0.0"` | Rare; only patch updates auto-accepted. |

**Recommendation for application projects:** exact pins + Dependabot. The lockfile (`package-lock.json` / `pnpm-lock.yaml` / `yarn.lock`) is your source of truth.

Always commit the lockfile. Always.

### Dependabot configuration

GitHub's Dependabot handles the upgrade workflow. Configure in `.github/dependabot.yml`:

```yaml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    open-pull-requests-limit: 5
    groups:
      framework:
        patterns:
          - "react"
          - "@types/react"
          - "react-dom"
      dev-tooling:
        dependency-type: "development"
    ignore:
      - dependency-name: "*"
        update-types: ["version-update:semver-major"]

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

Key choices:

- **Weekly cadence** keeps PR volume manageable.
- **Group related packages** (e.g., React + React DOM + types) — they need to upgrade together.
- **Ignore majors** by default; handle major upgrades manually.
- **Per-ecosystem** (npm, github-actions, docker, etc.) — Dependabot covers them all.

### Triaging Dependabot PRs

Weekly Monday review:

| Update type | Action |
|---|---|
| Patch (`x.y.Z`) | CI green → merge. Should rarely break. |
| Minor (`x.Y.0`) | CI green + skim release notes → merge. |
| Grouped | CI green + each member's release notes scanned → merge or split if one fails. |
| Major | Don't auto-merge. Read the changelog. Plan a focused upgrade PR. |
| Security alert | Prioritize: critical = today, high = within 7 days. |

Stale Dependabot PRs (>2 weeks unmerged) — close them. Dependabot will re-open with the latest version on next cycle. Don't let them pile up.

### Major upgrades

Major version bumps signal breaking changes (per [SemVer](https://semver.org)). Treat them as features:

1. Open a branch (`chore/upgrade-react-19`).
2. Read the changelog + migration guide.
3. Apply the upgrade.
4. Fix the breakages.
5. Run the full test suite (visual baselines often need re-capturing).
6. Open as a draft PR; let CI catch what manual testing missed.
7. Mark ready; merge.

If the upgrade is too big to do in one PR, consider:

- A compatibility shim that adapts the old API.
- Incremental migration (e.g., per-file with `@react-19` directives if available).
- Forking to a sustainable older version (last resort; signals you need to find a different lib).

### Security: CVE response

GitHub surfaces vulnerabilities via the Security tab. Subscribe to the project's [Security Advisories feed](https://docs.github.com/en/code-security/security-advisories) for additional alerting.

SLA recommendations:

- **Critical:** within 24 hours
- **High:** within 7 days
- **Medium / low:** with the next regular update

Per advisory:

1. Read the CVE — what does the exploit require? Are you exposed (e.g., the bug is in a code path you don't use)?
2. Is there a fixed version? If yes, upgrade.
3. If no fixed version: is there a workaround? Document it; track upstream.
4. If exploited or being exploited: hotfix immediately; rotate any exposed secrets.

Tools that scan dependencies for known vulnerabilities:

- [npm audit](https://docs.npmjs.com/cli/v10/commands/npm-audit) — built-in; run in CI
- [Snyk](https://snyk.io) — commercial, more comprehensive
- [OSV.dev](https://osv.dev) — Google's open source vulnerability database
- [GitHub Dependabot Alerts](https://docs.github.com/en/code-security/dependabot/dependabot-alerts) — automatic on GitHub repos

Enforce in CI:

```bash
pnpm audit --prod --audit-level=high
```

Fail the build on high+ findings.

### Size budgets

Per [`07-performance.md`](./07-performance.md), enforce bundle-size budgets:

- Per-route initial JS: budget set in `size-limit` or webpack-bundle-analyzer.
- Per-island (Astro / Marko / Qwik): budget per hydrated component.
- New dep that pushes over budget: blocked at PR level.

[Bundlephobia](https://bundlephobia.com) is the quick check for any candidate dep:

- Size (gzipped, bundled)
- Tree-shakability
- Composition (what does it depend on?)

### License compliance

Every dep has a license. Most permissive (MIT, Apache-2.0, BSD, ISC) are safe for any project. Copyleft licenses (GPL, AGPL, LGPL) impose obligations:

- **GPL / AGPL** — your project may need to be GPL too if you link to it. Often incompatible with proprietary projects.
- **LGPL** — okay if linked dynamically (most JS use cases are fine).
- **MPL** — file-level copyleft; usually compatible.

Tools:

- [license-checker](https://www.npmjs.com/package/license-checker) — list every dep's license
- [@npmcli/arborist](https://github.com/npm/cli) — programmatic dep tree

Run periodically (quarterly):

```bash
npx license-checker --production --summary
```

Anything unexpected → audit.

### Removing dependencies

Use `pnpm why <package>` (or `npm why`) to see who pulls a dep. If nothing in your code references it, remove it:

```bash
pnpm remove <package>
```

Audit `package.json` quarterly. Unused devDependencies are common cruft.

### Supply-chain hygiene

- **Lockfile pinning** — `pnpm install --frozen-lockfile` in CI ensures no silent drift.
- **Lockfile review** — Dependabot PRs include lockfile changes; reviewers should at least scan them.
- **Provenance** — when available, use [npm provenance](https://docs.npmjs.com/generating-provenance-statements) (verifies package was built from declared source).
- **Mirrors / proxies** — for high-security projects, mirror the registry (Verdaccio, Artifactory).

---

## PROJECT-SPECIFIC — fill these in

```markdown
## Dependency manager

- Tool: <npm | pnpm | yarn | bun>
- Lockfile path: <path>
- Pinning strategy: <exact | caret | tilde>

## Dependabot config

- Schedule: <e.g., weekly Monday 07:00 America/Denver>
- Groups: <list, e.g., react, sentry, dev-tooling>
- Ignored major versions: <list, with reasoning>

## CVE SLA

- Critical: <within X hours>
- High: <within Y days>
- Medium/low: <next regular update>

## Size budgets

[Per-entry budgets — see 07-performance.md]

## License whitelist

Allowed: <MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC>
Requires review: <MPL-2.0, EPL-2.0>
Forbidden: <GPL-3.0, AGPL-3.0>  (for proprietary projects)

## Upgrade review cadence

Weekly: <day, time, who reviews Dependabot PRs>
Quarterly: <full dependency audit; license check>
```

---

## Cross-references

- [`02-git.md`](./02-git.md) — Dependabot PRs use the same merge workflow
- [`07-performance.md`](./07-performance.md) — size budgets enforced via deps audit
- [`10-security.md`](./10-security.md) — CVE response intersects with dependency upgrades

External:
- [npm audit](https://docs.npmjs.com/cli/v10/commands/npm-audit)
- [GitHub Dependabot](https://docs.github.com/en/code-security/dependabot)
- [Bundlephobia](https://bundlephobia.com)
- [SPDX License List](https://spdx.org/licenses/)
- [OSV.dev](https://osv.dev)
- [Snyk vulnerability database](https://security.snyk.io/)

---

## Maintenance cadence

- **Weekly:** review Dependabot PRs; merge safe updates.
- **On security alert:** triage per SLA.
- **Quarterly:** full dependency audit — unused deps, license check, size review.
- **Annually:** evaluate major-version backlog; plan upgrades for any deps >1 major behind.
- **Owner:** the project's tech lead.
