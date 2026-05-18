# 06 — Debugging

**Purpose:** when something breaks, the team has a methodology and a known catalog of failure modes to consult.
**Anchor:** no single industry spec; closest is [Brian W. Kernighan & Rob Pike's *The Practice of Programming*](https://www.cs.princeton.edu/~bwk/tpop.html) on debugging discipline.
**Tier:** Quality

---

## Why this procedure exists

Most debugging time is spent figuring out *what's wrong*, not fixing it. The fix is often a one-line change; the diagnosis took 3 hours. A team with a debugging procedure cuts that diagnosis time substantially:

- Common failure modes have known causes — recognize the symptom, jump to the cause.
- A consistent methodology means you don't repeat the same exploratory dead-ends every time.
- Bugs found and diagnosed get *written down*, so the next person doesn't waste the same time.

**Failure modes when this procedure is missing:**

- Every bug is debugged from scratch even when it's a recurring class.
- "It works on my machine" → "it works in dev but not prod" → never resolved.
- Production incidents involve hours of synchronous war-rooming because nobody can reproduce.
- Subtle bugs (race conditions, hydration mismatches, CSP violations) take days to diagnose.

---

## The standard

### The methodology

When something breaks, work through these in order. Don't skip steps; the temptation to "I know what it is, just try X" is how you waste an hour on the wrong fix.

#### Step 1 — Reproduce

A bug you can't reproduce is a bug you can't fix. Get a reliable repro before doing anything else.

- Read the report. What did the user do? What did they expect? What happened?
- Reproduce on your machine. If you can't, reproduce in a fresh environment (Codespaces, dev container).
- Reduce: strip the repro to the minimum that still triggers the bug.
- If you can't reproduce: gather more information (Sentry trace, browser console, network log, screen recording).

**If you can't reproduce, stop.** Don't guess at a fix; you'll guess wrong.

#### Step 2 — Form a hypothesis

State out loud (or in a comment): "I think this is happening because X."

- Be specific. "Something with state" is not a hypothesis.
- The hypothesis should be falsifiable. "There's a race between the effect and the render" is testable.
- If you can't form a hypothesis: gather more information. Read more code. Add logging. Read the framework docs.

#### Step 3 — Test the hypothesis

Design the smallest experiment that would confirm or refute it.

- Add a `console.log` or breakpoint at the suspect site. Does the value match what you expected?
- Bisect: `git bisect` between a known-good commit and the failing one.
- Strip: comment out half the suspect code; does the bug disappear?
- Don't change two things at once; you'll never know which fixed it.

#### Step 4 — Fix

Once you've confirmed the cause:

- Write a regression test first if practical. Confirm it fails.
- Apply the fix.
- Confirm the test now passes and the bug is gone.
- Run the full test suite — make sure you didn't break anything else.

#### Step 5 — Write it down

If this bug class is novel or recurring, add it to your project's debugging knowledge:

- A line in the project's debugging doc with: symptom, cause, diagnostic step that found it, fix pattern.
- Future you (or the next agent) will find it via grep.

### Tools every web dev should know

#### Browser DevTools

| Tab | Use for |
|---|---|
| **Elements** | DOM structure, CSS computed styles, attribute values |
| **Console** | JS errors, log statements, ad-hoc expressions |
| **Sources** | Set breakpoints, step through code, scope inspection |
| **Network** | Request/response, headers, timing, size |
| **Performance** | Frame timing, long tasks, CPU profile |
| **Lighthouse** | CWV audit, accessibility, SEO, best practices |
| **Application** | Cookies, localStorage, IndexedDB, service workers |

Learn the keyboard shortcuts (Cmd+Shift+P for command palette in Chrome). They save minutes per session.

#### Framework-specific devtools

React DevTools, Vue Devtools, Redux DevTools — install them. They expose state that's invisible from the raw DOM.

#### Astro / Vue / Svelte / Next debugging

- View source on the rendered page — confirms what's SSR'd vs. client-only.
- `astro:before-preparation` / `astro:after-swap` for view-transition issues.
- Hydration mismatch errors: log SSR output vs client mount; the diff IS the bug.

#### CLI

- `curl -I <url>` — confirm response headers and status.
- `dig <domain>` — confirm DNS.
- `pnpm why <package>` — find why a transitive dep is installed.
- `git bisect` — find the offending commit between two points in history.
- `git log -S "string"` — find when a string entered or left the codebase.
- `git log -p <file>` — see every diff for a single file.

### The 8 failure modes that bite repeatedly in web stacks

Document your stack's flavor of each. Generic version:

#### 1. Server-only globals referenced at module load

**Symptom:** build fails with `window is not defined` / `document is not defined`.
**Cause:** importing a browser-only library at module top level; SSR runs the file on the server.
**Fix:** dynamic-import inside an effect; or guard with `typeof window !== "undefined"`; or import-only-types when only the types are needed at SSR.

#### 2. Hydration mismatch

**Symptom:** browser console: "Hydration failed because the initial UI does not match what was rendered on the server."
**Cause:** SSR HTML and first client render don't agree on the markup. Common causes: server uses `new Date()` (different from client), `Math.random()`, env-derived state.
**Fix:** make server and client agree by lifting time-sensitive state out of render; or `suppressHydrationWarning` (last resort) on the dynamic element.

#### 3. CSP blocking inline scripts/styles

**Symptom:** browser console: "Refused to execute inline script because it violates the Content Security Policy."
**Cause:** new third-party widget tries to inject a script tag without a nonce, or a `<style>` block without one.
**Fix:** use the per-request nonce; or whitelist a hash; never add `'unsafe-inline'`.

#### 4. Listener / observer leaks across SPA navigation

**Symptom:** behavior gets stranger as you navigate around the site; eventually a button does its action N times where N is your visit count.
**Cause:** an event listener was added but never removed; on each navigation a new listener stacks up.
**Fix:** every `addEventListener` needs a matching `removeEventListener` on cleanup (React `useEffect` return, Vue `onUnmounted`, view-transition `before-preparation`).

#### 5. Stale closure capture in effects/hooks

**Symptom:** function reads an old value of a state variable; UI shows stale data.
**Cause:** the effect captured the variable's value at the moment the closure was defined.
**Fix:** add the variable to dependency array; or use a ref for values that don't need to retrigger; or use the functional form (`setState(prev => ...)`).

#### 6. Async race conditions

**Symptom:** request A fires, request B fires, B returns first, A returns second; UI shows A's stale data.
**Cause:** no guard against out-of-order responses.
**Fix:** AbortController to cancel the previous request before issuing a new one; or check a request-ID before applying the response.

#### 7. Image / font loading order affecting LCP/CLS

**Symptom:** Lighthouse complains about LCP or CLS; the hero shifts on load.
**Cause:** no explicit width/height on `<img>`; no `font-display: swap`; LCP image not marked `fetchpriority="high"`.
**Fix:** explicit dimensions; preload critical fonts; LCP image gets `loading="eager" fetchpriority="high"`.

#### 8. Module resolution / version drift

**Symptom:** local works, CI fails (or vice versa). `Cannot find module 'X'`. Or types resolve differently.
**Cause:** mismatch between `package.json` and lockfile; or a peer dep is hoisted differently; or Node version is different.
**Fix:** `pnpm install --frozen-lockfile`; commit the lockfile; pin Node via `.nvmrc`; check `pnpm why` for unexpected duplicates.

### Anti-patterns

- **"Try something random and see if it works."** Hypothesis-free fixes get random results.
- **`console.log`-and-forget.** Leave `console.log` in the codebase and the next debug session is harder.
- **Catch-and-ignore.** `try { ... } catch {}` swallows the diagnostic information you need.
- **`--retries=10`.** Hides timing bugs; doesn't fix them.
- **"Restart and see if it goes away."** Sometimes necessary; never the diagnosis.

---

## PROJECT-SPECIFIC — fill these in

```markdown
## Stack-specific failure modes

Document the 6-10 things that bite repeatedly on this project.
Each entry: symptom → cause → diagnostic → fix pattern.

### 1. [Failure mode name]

**Symptom:** [what the developer sees]
**Cause:** [why it happens]
**Diagnostic:** [step that confirms it's this]
**Fix:** [the pattern that resolves it]

### 2. [next failure mode]
...

## Logging conventions

[Where logs go — stdout? Sentry? structured JSON?]
[Log level discipline — when to use error / warn / info / debug]

## Diagnostic tools we use here

[Sentry, Vercel Speed Insights, browser DevTools, custom tooling]
```

---

## Cross-references

- [`04-testing.md`](./04-testing.md) — when a bug is reproducible, a test prevents regression
- [`07-performance.md`](./07-performance.md) — performance debugging specifics
- [`08-accessibility.md`](./08-accessibility.md) — a11y bugs have their own diagnostic flow
- [`10-security.md`](./10-security.md) — security incidents have a separate response protocol

External:
- [Brian Kernighan: *The Practice of Programming*](https://www.cs.princeton.edu/~bwk/tpop.html) — debugging chapter is gold
- [Julia Evans: debugging guides](https://jvns.ca/) — practical, illustrated
- [Chrome DevTools docs](https://developer.chrome.com/docs/devtools/)
- [Firefox DevTools docs](https://firefox-source-docs.mozilla.org/devtools-user/)

---

## Maintenance cadence

- **Per incident:** if you debug something novel, add it to the stack-specific failure modes list.
- **Quarterly:** review the failure modes list. If something hasn't been seen in 6 months, demote or remove. If a new pattern is emerging, promote it.
- **On framework upgrade:** new framework versions introduce new failure modes; update accordingly.
- **Owner:** the project's most-senior contributor; everyone contributes failure modes they encounter.
