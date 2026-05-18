# 02 — Git Workflow

**Purpose:** every commit, branch, PR, and release follows a single shared convention.
**Anchors:** [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) · [Semantic Versioning 2.0.0](https://semver.org) · [GitHub Flow](https://docs.github.com/en/get-started/quickstart/github-flow)
**Tier:** Foundation

---

## Why this procedure exists

Without a written git convention, every commit is a fresh negotiation. Subject lines drift in style, branch names follow personal preference, PR titles range from "stuff" to a paragraph. The cost is everywhere: `git log` becomes useless, `git blame` is harder to follow, code archaeology takes longer, automated tooling (changelog generation, semantic-release, etc.) can't run.

**Failure modes when this procedure is missing:**

- Commit history reads as "wip", "fix", "more fixes", "actually fix it", "ugh"
- PR titles don't describe the change ("Updates" / "Final version")
- Bisecting a regression is impossible because no commit on `main` is small or atomic
- Releases require manually written changelogs because no automation can infer types from messages
- Some contributors squash, some merge-commit, some force-push to shared branches

Pick one convention, write it down, enforce it through review.

---

## The standard

### Branching: GitHub Flow

One long-lived `main` branch. All work on short-lived branches off `main`, merged back via PR.

- No `develop` branch.
- No release branches.
- No long-lived feature branches (>1 week is a smell — split the work).

If your release cadence is slower than your `main` velocity (e.g., you batch releases monthly), use git tags on `main` to mark release points; don't introduce a release branch.

**Branch naming:** `<type>/<short-kebab-description>`. Examples:

- `feat/user-profile-edit`
- `fix/lightbox-focus-return`
- `docs/refresh-onboarding`
- `refactor/extract-form-helpers`
- `ci/upgrade-actions-runner`
- `chore/dependency-cleanup`

Bot-generated branches use their own format (`dependabot/<ecosystem>/<package>`). Don't rename them.

### Commits: Conventional Commits

Every commit:

```
<type>[optional scope][!]: <description>

[optional body explaining why]

[optional footer(s)]
```

The spec only mandates structure + the `!` shortcut for breaking changes + the footer token. It does NOT mandate subject case, length, or mood — those are project conventions you layer on top.

**Recommended project conventions:**

- **Imperative mood** — "fix the bug" not "fixed the bug" or "fixes the bug"
- **≤ 72 characters** — fits in `git log --oneline` without truncation
- **No trailing period**
- **Lowercase first word** after the type prefix (except proper nouns)
- **Be specific** — "fix: bug" is useless; "fix: lightbox focus not returning to trigger on close" is reviewable

**Types** (Angular-derived; project may extend):

| Type | When |
|---|---|
| `feat` | New user-facing feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `refactor` | Code restructure, no behavior change |
| `test` | Test-only changes |
| `ci` | CI workflow changes |
| `chore` | Tooling / repo hygiene |
| `perf` | Performance work |
| `style` | Formatting / whitespace |
| `deps` | Dependency bumps (often auto-generated) |

**Body** (optional but encouraged for non-trivial changes): explains *why*, not *what*. The diff shows what; the body answers questions the diff can't.

**Breaking changes** — two equivalent forms:

```
feat(api)!: require auth token on /users/me
```

OR with footer:

```
feat(api): require auth token on /users/me

BREAKING CHANGE: Existing clients must include Authorization header.
```

Both `BREAKING CHANGE:` and `BREAKING-CHANGE:` are valid per spec.

### Pull requests

1. **Branch off `main`** with `git fetch && git checkout main && git pull`.
2. **Commit as you work** — small atomic commits help review even though squash collapses them.
3. **Self-review locally** before opening — run the local equivalent of CI.
4. **Open PR.** Use `gh pr create --draft --fill` if your tool emits the PR template into the description.
5. **Mark ready** when CI is green.
6. **Respond to review** by pushing new commits (don't force-push during active review).
7. **Squash-merge** when CI green + approved + conversations resolved.
8. **Delete the branch** after merge.

**PR size:** Google's research says "100 lines is usually a reasonable size for a CL, and 1000 lines is usually too large." If your change doesn't fit, split it.

### Merge strategy: squash by default

The three GitHub options:

| Option | When | Trade-off |
|---|---|---|
| **Squash and merge** | ✅ Default | Clean `main` history; loses per-commit author granularity within the PR |
| **Rebase and merge** | Narrow: when each commit deserves to live independently on `main` | Preserves commit graph; requires clean commits |
| **Create merge commit** | When you genuinely want the branch graph (some OSS projects: Linux kernel, Postgres) | Pollutes `main` with `Merge pull request #N` lines |

Pick one as your default and document it. Squash is the most common modern choice for application code; merge commits are more common in long-running OSS.

### Releases: SemVer

`MAJOR.MINOR.PATCH`. Pre-1.0 (`0.x.y`) — anything can break. Post-1.0 — major for breaking changes, minor for backward-compatible features, patch for bug fixes.

Tag releases on `main`:

```bash
git tag -a v1.2.3 -m "release: v1.2.3"
git push origin v1.2.3
gh release create v1.2.3 --generate-notes
```

`--generate-notes` builds a changelog from the squash-merge commits on `main` since the last tag, with sections grouped by `feat:`, `fix:`, etc. (PRs labeled accordingly will sort cleanly.)

### Branch protection

Configure on `main`:

- Require pull request before merging
- Require N approvals (1 minimum; more for larger teams)
- Require CODEOWNERS review (when CODEOWNERS exists)
- Require status checks (CI must be green)
- Require branches up to date before merging
- Require conversation resolution
- Disallow force pushes
- Disallow deletions

Optional: require signed commits (GPG or SSH) — supply-chain integrity.

---

## PROJECT-SPECIFIC — fill these in

```markdown
## Branch names

Format: <type>/<short-description>

Types we use in this repo:
- [list, with project-specific examples]

## CI status checks required for merge

[List the exact `name:` field values from your CI workflow]
- "Lint + Type + Test"
- "Bundle Size Budget"
- ...

## CODEOWNERS

- Catch-all: @<owner>
- Security-critical paths: @<reviewer>

## Release tags

Pre-1.0: v0.x.y (rolling)
At launch: v1.0.0
Post-1.0: standard SemVer

## Merge strategy

Default: <squash|rebase|merge>
Why: <one-sentence rationale>

## Hotfix workflow

1. Branch off main
2. Apply minimal fix
3. PR with "Hotfix" in title body
4. Fast-track review (1 approval)
5. Monitor for 30 min after deploy
6. Roll back via <mechanism> if needed
```

---

## Cross-references

- [`03-code-review.md`](./03-code-review.md) — what happens during PR review
- [`04-testing.md`](./04-testing.md) — what CI runs as status checks
- [`10-security.md`](./10-security.md) — CODEOWNERS-protected paths
- [`11-adrs.md`](./11-adrs.md) — for non-trivial decisions, supplement the commit body with an ADR

External:
- [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/)
- [Semantic Versioning 2.0.0](https://semver.org)
- [GitHub Flow](https://docs.github.com/en/get-started/quickstart/github-flow)
- [Tim Pope: A Note About Git Commit Messages](https://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html)

---

## Maintenance cadence

- **Quarterly:** review whether the convention is being followed (`git log --oneline -50` should be reviewable). If many recent commits drift, the standard needs adjustment or enforcement.
- **On tooling change:** if you switch from `gh` to native GitHub UI or add commitlint, update accordingly.
- **Owner:** the project maintainer; minor wording PRs accepted from anyone.
