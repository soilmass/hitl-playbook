# 03 — Code Review

**Purpose:** reviews catch the right issues without becoming a bottleneck or a power dynamic.
**Anchors:** [Google Engineering Practices: Code Review](https://google.github.io/eng-practices/review/) · [Conventional Comments](https://conventionalcomments.org)
**Tier:** Foundation

---

## Why this procedure exists

Code review is the highest-leverage quality gate most teams have. It's also the most expensive and the most prone to social friction. Without explicit conventions:

- **Reviewers** become inconsistent — they nitpick style in one PR, miss security issues in the next, leave dangling comments that block merges for days.
- **Authors** can't tell which comments are blocking; they fix all of them and the PR cycle stretches.
- **The team** burns reservoirs of goodwill on bikeshed arguments that should be settled by lint rules.

A written convention separates "what to review for" (the substantive checklist) from "how to communicate during review" (the social contract). Both parts are necessary.

---

## The standard

### Author obligations

Before requesting review:

1. **Self-review the diff in the PR UI.** Read it as a stranger would. Add inline comments explaining anything that isn't obvious.
2. **Run the local equivalent of CI.** If you can't pass your own machine, don't waste reviewer time.
3. **Keep the PR small.** ~100 LoC ideal, ~1000 LoC is too large per Google's research. If you can't split, write a longer body explaining structure.
4. **Write a real PR description.** "What" and "why" at minimum. Link related issues / docs / ADRs.
5. **Mark draft if not ready.** Draft PRs run CI without notifying reviewers.

During review:

6. **Respond to every comment.** Either fix it, push back with reasoning, or convert it to a follow-up issue. Don't leave threads dangling.
7. **Mark resolved when addressed.** Use GitHub's "Resolve conversation" button so reviewers see what's still open.
8. **Don't take feedback personally.** A reviewer's job is to find issues; finding them isn't an indictment of you.
9. **Don't force-push during active review.** It makes diff-of-diff awkward. Exception: rebase-onto-main to resolve conflicts (use `--force-with-lease`).

### Reviewer obligations

When you receive a review request:

1. **Respond within one business day.** Stale PRs rot — the author loses context, the branch drifts.
2. **Read the PR description first.** Then the diff. Then run the code locally if the change is non-trivial.
3. **Use a checklist** (next section). Don't review by vibes.
4. **Be specific.** "This is wrong" is useless. "On line 42, `entry.id` should be `entry.data.id` — these are different keys; see schema in src/content/config.ts" is reviewable.
5. **Be kind.** Even critical feedback can be specific without being condescending. The author is your colleague tomorrow.
6. **Label comments with severity** (next section). Authors should be able to tell what blocks merge.
7. **Approve when good enough to merge**, not when perfect. Perfect is the enemy of shipped.

### Review checklist — what to actually look for

Use this in order. Stop at the first failing category and request changes; the rest doesn't matter until earlier categories pass.

1. **Correctness** — does the code do what the description says? Are obvious edge cases handled (null, empty array, network failure)?
2. **Tests** — is the change tested? At the right level (unit / integration / e2e)? If not testable, is "untested" explicitly justified?
3. **Security** — secrets in diff? Inputs validated? Auth checks correct? SQL/HTML/shell injection guarded? See [`10-security.md`](./10-security.md).
4. **Performance** — N+1 queries? Bundle size impact? CWV implications? Sync work that should be async? See [`07-performance.md`](./07-performance.md).
5. **Accessibility** — semantic HTML? ARIA where needed? Keyboard reachable? Color contrast? See [`08-accessibility.md`](./08-accessibility.md).
6. **API surface** — public-facing changes (URLs, response shapes, env vars) need extra care; do they need SemVer major bump?
7. **Style** — does the code read like the rest of the codebase? Comments explain *why*? Naming descriptive? See [`05-style.md`](./05-style.md).
8. **Documentation** — does the PR update docs that describe the changed behavior? README? API reference?
9. **Reversibility** — if this is wrong in production, how do we roll back?

### Comment labels — Conventional Comments

[Conventional Comments](https://conventionalcomments.org) defines 9 labels. Use them as a prefix so authors can sort responses by severity at a glance:

| Label | Meaning |
|---|---|
| `praise:` | Call out something good (worth doing — encouragement matters) |
| `nitpick:` | Trivial, preference-based — non-blocking by definition |
| `suggestion:` | Concrete proposed improvement with rationale |
| `issue:` | A specific problem you've identified |
| `todo:` | A small, necessary change |
| `question:` | Actually asking, not implying |
| `thought:` | A non-blocking idea worth surfacing |
| `chore:` | A small process task (rebase, add a label) |
| `note:` | A non-blocking call-out worth attention |

Optional decorators: `(blocking)`, `(non-blocking)`, `(if-minor)`. Example:

```
issue (blocking): The function returns `undefined` when `users` is empty;
the caller dereferences `.length` on the result.

suggestion (if-minor): Could extract the regex to a constant — only
worth it if you're touching this function anyway.
```

The shorthand `nit:` is widely understood but the spec-canonical label is `nitpick:`.

### When author and reviewer disagree

1. **Discuss in PR comments first.** Often a 2-message back-and-forth resolves it.
2. **If unresolved, hop on a call or async DM.** Long PR comment threads are bad for everyone.
3. **The author has the final say on style.** The reviewer has the final say on correctness. Style is taste; correctness is testable.
4. **Anything genuinely ambiguous escalates** to the project owner / tech lead. Don't merge over unresolved disagreement.

### Approval semantics

A GitHub "Approve" means: "I've reviewed this, I believe it's safe to merge, I take partial responsibility if it breaks in production."

It does NOT mean: "I read 30% of the diff and trusted the rest."

If you're approving without having read the whole change, say so explicitly:

```
approve (partial): I reviewed the new ContactForm logic carefully (correct).
I didn't review the lockfile changes (Dependabot's grouped bump).
```

---

## PROJECT-SPECIFIC — fill these in

```markdown
## Review SLA

Reviewers respond within: <N business hours / days>
Stale review threshold: <after which Slack the reviewer / re-assign>

## Required reviewers

CODEOWNERS file at: <path>
Catch-all reviewer: <@username>
Security-critical paths (require additional reviewer): <list>

## Comment label conventions

We use [Conventional Comments](https://conventionalcomments.org/).
Common shortcuts in this team: <e.g., "nit:" accepted as shorthand for "nitpick:">

## What to look for, in priority order

[Customize the 9-category checklist with project-specific concerns.]

## When to escalate

Disagreements that aren't resolved in 2 back-and-forth comments → <how to escalate>
```

---

## Cross-references

- [`02-git.md`](./02-git.md) — PR workflow and merge mechanics
- [`05-style.md`](./05-style.md) — what "style" issues to call out vs. let go
- [`07-performance.md`](./07-performance.md), [`08-accessibility.md`](./08-accessibility.md), [`10-security.md`](./10-security.md) — the substantive categories reviewers must check

External:
- [Google Engineering Practices: Reviewer Guide](https://google.github.io/eng-practices/review/reviewer/)
- [Google Engineering Practices: Developer Guide](https://google.github.io/eng-practices/review/developer/)
- [Conventional Comments](https://conventionalcomments.org/)

---

## Maintenance cadence

- **Per PR retro:** if a review comment frequently appears across PRs, lift it into the checklist or a lint rule.
- **Quarterly:** review whether the convention is being followed. Sample 5 random PRs from the last quarter — were the right things checked? Were comments labeled?
- **On team growth:** when the team grows beyond a few people, re-examine SLA expectations.
- **Owner:** the project's tech lead / maintainer.
