# 05 — Code Style

**Purpose:** the codebase reads as if one person wrote it — naming, structure, comment conventions are consistent.
**Anchors:** [Google Style Guides](https://google.github.io/styleguide/) · [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript) · framework-specific guides (React, Vue, Astro, etc.)
**Tier:** Quality

---

## Why this procedure exists

Linters and formatters (Prettier, ESLint, stylelint) catch ~70% of style decisions automatically. Everything they don't catch is what this standard covers — naming, file organization, when to extract a component, when to write a comment, when to add a helper.

Without a written convention:

- Naming drifts (`handleSubmit` vs `onSubmit` vs `submit` vs `doSubmit` in the same codebase)
- File organization fragments (some features in `features/`, some in `lib/`, some at root)
- Code review burns cycles on style every PR
- New contributors infer convention from whichever file they happened to read first

A style guide is a one-time investment that pays back on every subsequent line of code.

---

## The standard

### Automated first

Use formatters and linters before any human style discussion:

- **Prettier** (or equivalent) — formats every file on save / commit. Run in CI as a status check.
- **ESLint** with shared config (e.g., `eslint:recommended`, `plugin:@typescript-eslint/recommended`, framework-specific like `eslint-plugin-react`, `eslint-plugin-astro`).
- **TypeScript** with `strict: true` and `noUncheckedIndexedAccess: true`.
- **stylelint** for CSS / SCSS if applicable.

Anything a tool can enforce shouldn't be a human discussion.

### Naming

**Variables and functions:** `camelCase`, descriptive.

- ❌ `data`, `info`, `obj`, `handleClick`, `myFunction`
- ✅ `currentUser`, `parseInvoiceLineItems`, `handleSubmitContact`

**Constants:** `SCREAMING_SNAKE_CASE` for module-level immutable values intended as configuration:

- ❌ `const TIMEOUT_MS = 5000;` for a one-line use
- ✅ `const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;` when referenced in multiple places

**Booleans:** prefix with `is`, `has`, `should`, `can`:

- ❌ `let open = false;`
- ✅ `let isOpen = false;`

**Functions returning a result:** verb + noun:

- ❌ `function user(id)`
- ✅ `function getUser(id)`, `function buildUserSummary(user)`

**Components:** `PascalCase`. File matches component name: `UserProfile.tsx` exports `<UserProfile />`.

**Files:** kebab-case is most common (`user-profile.tsx`), but PascalCase matches the component (`UserProfile.tsx`). Pick one, document it.

**Folders:** `kebab-case` for multi-word.

**CSS classes:**

- Tailwind / utility-first: don't worry about class names
- BEM: `.user-profile__avatar--active` (block__element--modifier)
- CSS Modules: use camelCase in JSX, `.userProfile` in CSS
- Project-local utility classes: prefix to avoid collision (e.g., `.u-section`, `.app-button`)

### File organization

**By feature, not by file type.** Co-locate related code:

```
src/
├── features/
│   ├── contact/
│   │   ├── ContactForm.tsx
│   │   ├── ContactForm.test.tsx
│   │   ├── contact.api.ts
│   │   └── contact.types.ts
│   └── portfolio/
│       └── ...
├── components/        ← shared UI primitives
├── lib/               ← stack-agnostic helpers
└── pages/             ← routes
```

Not:

```
src/
├── components/        ← every component here, mixing concerns
├── api/               ← every API call
├── types/             ← every type
└── ...                ← coupling spread across folders
```

Exception: very small projects (a personal site) can keep everything in `src/components/`, `src/pages/`, `src/lib/` without feature folders.

### When to extract

A function: when the same logic appears **twice** with minor variation. Once is "specific to this place"; twice is "abstract this."

A component: when:

- The same JSX/template appears in 2+ places, OR
- A piece of UI has internal state that doesn't belong to its parent, OR
- A function component grows past ~150 lines

A module: when a feature has 4+ files. Split into a subdirectory.

**Don't extract prematurely.** Code that's used once is easier to read inline. Premature abstraction is harder to undo than duplication.

### Comments

**Rule of thumb:** comments explain *why*, code explains *what*.

❌ Bad — restates the code:

```ts
// Increment the counter
counter++;
```

❌ Bad — explains what the function does (use a JSDoc or the function name):

```ts
// This function takes a user and returns their full name
function fullName(user) { ... }
```

✅ Good — explains a non-obvious decision:

```ts
// useState batches updates but we need synchronous read in the form-submit
// handler before the next render. useRef bypasses the batch.
const submitting = useRef(false);
```

✅ Good — warns about a hidden constraint:

```ts
// Don't change this regex without coordinating with the analytics team —
// the backend ingestion pipeline matches the same pattern.
const EVENT_NAME_RE = /^[a-z_][a-z0-9_]*$/;
```

✅ Good — points to context the diff doesn't have:

```ts
// Workaround for https://github.com/vercel/next.js/issues/12345
// Remove when Next 15 ships with the fix.
```

**JSDoc/TSDoc** on exported functions and types is encouraged. Inline comments are for the inside-function "why."

### When to write a function vs. inline

If the inline expression has:

- 1 line of pure code: inline it.
- 2-3 lines, used once: inline.
- 2-3 lines, used twice: extract.
- 4+ lines: extract (mostly).
- Conditional with >2 branches: extract for readability.

### Errors

- Throw `Error` with a message that explains the *context*, not just the symptom:

  ❌ `throw new Error("not found");`
  ✅ `throw new Error(\`User ${id} not found in tenant ${tenantId}\`);`

- Catch errors as `unknown` (TypeScript), narrow before handling.
- Don't swallow errors silently. If you can't handle, re-throw or log.

### Async

- Prefer `async/await` over raw promise chains.
- `Promise.all` for parallelizable work.
- Always handle rejection (try/catch or `.catch()`).
- Don't fire-and-forget (top-level `await` or explicit `void promise` to silence the lint warning).

### TypeScript

- `any` is a code smell. Use `unknown` for untyped inputs; narrow with type guards.
- Avoid type assertions (`as Foo`) unless you've done the narrowing yourself.
- Prefer discriminated unions over boolean flags:
  - ❌ `{ loading: boolean, error: string | null, data: T | null }`
  - ✅ `{ status: "loading" } | { status: "error", error: string } | { status: "ok", data: T }`

### Framework-specific

Defer to the framework's own style guide:

- React: [React docs / Thinking in React](https://react.dev/learn/thinking-in-react), [Airbnb React/JSX](https://github.com/airbnb/javascript/tree/master/react)
- Vue: [Vue Style Guide](https://vuejs.org/style-guide/)
- Astro: [Astro best practices](https://docs.astro.build) — keep islands small, prefer `.astro` over `.tsx`, hydrate with the lightest directive
- Next: [Next.js conventions](https://nextjs.org/docs)

---

## PROJECT-SPECIFIC — fill these in

```markdown
## Tools

- Formatter: <Prettier version + config>
- Linter: <ESLint version + extended configs>
- Type checker: <TypeScript version + strict flags>

## File / folder naming

- Components: <PascalCase | kebab-case>
- Other source files: <kebab-case | camelCase>
- Folders: <kebab-case>

## Project-specific conventions beyond defaults

- [List any deviations from this standard with reasoning]
- e.g., "We use lowercase MDX filenames for content collection entries."

## When to extract a component vs. inline

[Project-specific heuristics if your stack has them — e.g., Astro islands cost
to hydrate, prefer .astro when possible.]
```

---

## Cross-references

- [`02-git.md`](./02-git.md) — formatter runs in CI as a status check
- [`03-code-review.md`](./03-code-review.md) — what review looks for in style (and what it doesn't, because the linter handles it)
- [`11-adrs.md`](./11-adrs.md) — style decisions worth preserving (e.g., "we chose feature folders over type folders") become ADRs

External:
- [Google Style Guides](https://google.github.io/styleguide/) — multiple languages
- [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)
- [Testing Library: Guiding Principles](https://testing-library.com/docs/guiding-principles) — naming conventions for tests
- [Tom MacWright on code style](https://macwright.com/2017/03/24/practical-static-site-generators) — pragmatic philosophy

---

## Maintenance cadence

- **Per PR:** style violations not caught by lint are surfaced in review.
- **On framework upgrade:** check for new lint rules / style conventions.
- **Quarterly:** review whether the style guide matches the codebase. If 20+ files violate a rule consistently, the rule is wrong — fix the rule.
- **Owner:** the project's tech lead.
