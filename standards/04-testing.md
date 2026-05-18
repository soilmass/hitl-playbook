# 04 — Testing

**Purpose:** changes don't regress what works; the team can move faster because the tests catch obvious breaks.
**Anchors:** [Mike Cohn's test pyramid](https://martinfowler.com/articles/practical-test-pyramid.html) · [Kent C. Dodds: testing trophy](https://kentcdodds.com/blog/the-testing-trophy-and-testing-classifications) · [Testing Library principles](https://testing-library.com/docs/guiding-principles) · [Playwright best practices](https://playwright.dev/docs/best-practices)
**Tier:** Foundation

---

## Why this procedure exists

Tests are an investment in *future velocity*. Without them, every change carries fear of regression, which translates to slower review, smaller PRs, and over-cautious refactoring. With them, contributors can move confidently because the suite catches the obvious mistakes.

But tests have a quality of their own. Bad tests are worse than no tests — they create false confidence, they flake, they break on every refactor, they require their own maintenance budget. The standard isn't "have tests"; it's "have the right kinds of tests in the right places, run them reliably, fix them when they break."

**Failure modes when this procedure is missing:**

- 80% line coverage but the critical paths aren't exercised
- Tests that are tightly coupled to implementation details, so every refactor cascades
- Flaky tests that get re-run until they pass instead of fixed
- No clear answer to "where do I add the test for this change?"
- Visual / accessibility regressions land in production because the suite doesn't catch them

---

## The standard

### Test pyramid (or trophy)

Mike Cohn's pyramid has three layers; Kent C. Dodds' trophy adds a fourth ("static"). Both work. The principle: more cheap fast tests at the base, fewer expensive slow tests at the top.

```
        ┌────────┐
        │  e2e   │  ← few, slow, high confidence, brittle
        ├────────┤
        │  int   │  ← integration: real network/db
        ├────────┤
        │  unit  │  ← many, fast, focused
        ├────────┤
        │ static │  ← typecheck, lint, format — free, instant
        └────────┘
```

Per layer, what to test:

| Layer | What it catches | Speed | When to add |
|---|---|---|---|
| **Static** (TypeScript, ESLint, Prettier) | Type errors, syntax, style | Sub-second | Always |
| **Unit** | Single function / module logic | <100ms each | Pure functions; complex transformations |
| **Integration** | Modules collaborating; real HTTP / DB; rendering | 100ms–10s | API contracts, query logic, component+state |
| **E2E** | Full user flow through the rendered UI | Seconds | Critical paths only — login, checkout, primary CTA |

Most web projects under-invest in static (free) and over-invest in unit tests of trivial getters. Right-size the pyramid for your stack.

### What to test, in priority order

1. **Critical conversion paths.** What does failure here cost? If the answer is revenue or a major user impact, test it at multiple layers.
2. **Logic with branches.** Anything with `if` / `switch` / ternary. Each branch should have a test that exercises it.
3. **Public APIs.** Any function/component that other modules call. Contract testing.
4. **Bug fixes.** Every bug becomes a regression test before it's fixed.
5. **Visual regressions.** Snapshot the key pages at the breakpoints you support; diff against baseline.
6. **Accessibility regressions.** axe-core in your e2e suite catches ~40% of WCAG 2.2 AA issues automatically; see [`08-accessibility.md`](./08-accessibility.md).

### What NOT to test

- **Third-party library internals.** Trust the library; if it breaks, that's its problem (and you'll catch it via integration tests).
- **Trivial getters / setters.**
- **Configuration.** If your test confirms `config.timeout === 5000`, you're not testing logic.
- **Implementation details.** Test behavior, not internal state. (Testing Library principle: "The more your tests resemble the way your software is used, the more confidence they can give you.")

### Test writing rules

1. **AAA: Arrange, Act, Assert.** Three-section test structure makes intent legible.
2. **One assertion per test, or one logical concept.** Multi-assertion tests fail with unclear cause.
3. **Test names describe behavior.** `it("returns null when the user is logged out")` not `it("test login")`.
4. **Deterministic.** No `Math.random`, `Date.now`, network, or filesystem in the test path. Mock them. Use frozen-time libraries.
5. **Independent.** Each test sets up its own state. No test relies on another running first.
6. **Fast.** If a unit test takes >100ms, it's actually an integration test — move it up the pyramid.

### Visual regression tests

Playwright + screenshot diff is the de-facto standard. Capture baselines per browser project (Chromium, Firefox, WebKit) per breakpoint (mobile, tablet, desktop). Diff against committed baselines on every PR.

Deterministic capture requires:

- `reducedMotion: 'reduce'` in Playwright config (eliminates animation flake)
- Wait for fonts (`document.fonts.ready`)
- Wait for images (`naturalWidth > 0` on every `<img loading="lazy">`)
- Disable timed animations (carousels, etc.) during test runs

When a baseline intentionally changes (a UI redesign), update it deliberately:

```bash
pnpm playwright test --update-snapshots
git add tests/**/*-snapshots/
```

Reviewer's job: open the snapshot PNGs in the PR and confirm the visual change is intended.

### Accessibility tests

Run [`@axe-core/playwright`](https://playwright.dev/docs/accessibility-testing) on every visual baseline test. Fail on any WCAG 2.2 AA violation.

Important: axe catches ~40% of issues per [WebAIM research](https://webaim.org/projects/million/). The other 60% require manual testing — keyboard pass, screen reader pass, color in dynamic states. See [`08-accessibility.md`](./08-accessibility.md).

### CI integration

Tests run on every PR:

- Static + unit: required, fast, runs in seconds
- Integration: required, runs in 1–5 minutes
- E2E + visual + a11y: required, runs in 5–15 minutes; uploads playwright report as artifact

Tests block merge: status checks on `main`'s branch protection rule. If a test is broken, the PR doesn't land — fix the test or fix the code.

### Flake handling

A test is flaky when it sometimes passes and sometimes fails without code changes. **Flake is a bug class, not a tolerable quirk.**

- **Default:** retry once in CI, mark with `[FLAKY]` in test name, file an issue.
- **If flake rate > 5%:** quarantine the test (`test.skip` with a TODO comment) and prioritize fixing it.
- **Don't:** add `--retries=5` to make a flaky test "pass". You're hiding a bug.

Most flakes are timing-related — async race conditions, animations not gated, network mocks not awaited. The Playwright docs have a [debugging guide](https://playwright.dev/docs/debug).

### Coverage

Coverage as a primary metric is misleading; coverage as a *minimum floor* with attention to which lines are uncovered is useful.

- **Don't enforce** a specific percentage in CI (e.g., "must be >80%"). That incentivizes meaningless tests.
- **Do review** the coverage report periodically. Uncovered branches in critical code are the actionable signal.
- **Coverage** is a tool for finding what you've missed, not a goal in itself.

---

## PROJECT-SPECIFIC — fill these in

```markdown
## Test runner(s)

[e.g., Vitest for unit, Playwright for e2e + visual + a11y]

## CI integration

Status check names:
- "<unit + lint name>"
- "<integration name>"
- "<e2e + visual + a11y name>"

## Test file conventions

Unit: <pattern, e.g., `*.test.ts` next to source>
Integration: <pattern>
E2E: <pattern, e.g., `tests/e2e/*.spec.ts`>

## Visual baseline storage

Path: <e.g., `tests/e2e/visual.spec.ts-snapshots/`>
Projects (browsers × devices): <list>

## Flake quarantine list

[Tests currently quarantined + their tracking issue]

## Coverage targets (informational only, not enforced)

[Per-area expectations, e.g., "API handlers should have all branches tested"]
```

---

## Cross-references

- [`02-git.md`](./02-git.md) — tests must pass before PR can merge
- [`06-debugging.md`](./06-debugging.md) — when tests fail, diagnose; common failure modes
- [`07-performance.md`](./07-performance.md) — Lighthouse CI as a perf test
- [`08-accessibility.md`](./08-accessibility.md) — axe + manual a11y workflow

External:
- [Practical Test Pyramid (Martin Fowler)](https://martinfowler.com/articles/practical-test-pyramid.html)
- [Testing Trophy (Kent C. Dodds)](https://kentcdodds.com/blog/the-testing-trophy-and-testing-classifications)
- [Testing Library Guiding Principles](https://testing-library.com/docs/guiding-principles)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
- [Axe-core Playwright integration](https://playwright.dev/docs/accessibility-testing)

---

## Maintenance cadence

- **Per PR:** new code should include tests at the appropriate layer.
- **Weekly:** review flaky-test issues; quarantine or fix.
- **Quarterly:** review the coverage report; identify gaps in critical paths.
- **On dependency upgrades:** update test runner versions; regenerate baselines if browser rendering changed.
- **Owner:** the project's tech lead; per-test ownership goes to the last contributor who touched the corresponding code.
