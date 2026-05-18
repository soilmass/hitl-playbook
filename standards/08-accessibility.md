# 08 — Accessibility

**Purpose:** every user can use the site, regardless of disability, device, or input modality.
**Anchors:** [WCAG 2.2 AA](https://www.w3.org/TR/WCAG22/) · [WAI-ARIA Authoring Practices Guide](https://www.w3.org/WAI/ARIA/apg/) · [axe-core rules](https://dequeuniversity.com/rules/axe/) · [WebAIM](https://webaim.org)
**Tier:** Quality

---

## Why this procedure exists

Accessibility is the quality concern most likely to be deferred to "we'll get to it." That's a mistake on every axis:

- **Ethical:** ~15% of the global population has some form of disability ([WHO World Report on Disability](https://www.who.int/teams/noncommunicable-diseases/sensory-functions-disability-and-rehabilitation/world-report-on-disability)). Inaccessible sites exclude them.
- **Legal:** the [ADA](https://www.ada.gov/) (US), [EAA](https://eur-lex.europa.eu/eli/dir/2019/882/oj) (EU starting 2025), [AODA](https://www.aoda.ca/) (Ontario), and similar laws make accessibility non-optional for public-facing sites. Lawsuits are common and lost defaults often.
- **SEO:** Google's algorithms favor accessible markup (semantic HTML, alt text, heading structure).
- **Business:** accessibility improvements consistently lift conversion for *all* users — not just those with disabilities.

It's also the quality concern with the highest ratio of unknown unknowns. Automated tools catch ~40% of WCAG issues per [WebAIM's automated-testing analysis](https://webaim.org/projects/million/). The other 60% require knowing the patterns.

---

## The standard

### Target: WCAG 2.2 AA

[WCAG 2.2](https://www.w3.org/TR/WCAG22/) is the current authoritative standard. AA is the legal-and-ethical floor for public sites; AAA is aspirational. New criteria in 2.2 (e.g., 2.5.8 Target Size, 2.4.11 Focus Not Obscured, 3.2.6 Consistent Help) catch real issues older standards missed.

The four POUR principles:

- **Perceivable** — users can see/hear content (alt text, captions, contrast)
- **Operable** — users can interact (keyboard, touch, voice; no time traps)
- **Understandable** — content is comprehensible (clear language, predictable navigation)
- **Robust** — content works with current and future assistive tech (valid HTML, ARIA where needed)

### The two-pronged workflow

#### Automated (catches ~40%)

Run on every PR via CI:

- **[axe-core](https://www.deque.com/axe/) via Playwright** — fails the test on any WCAG violation.
- **[pa11y-ci](https://github.com/pa11y/pa11y-ci)** — sitewide crawl.
- **Lighthouse Accessibility category** — score of 100 enforced.

Configure each to fail CI on findings. Don't ignore rules to make CI pass — that's how the [Coca-Cola pattern](https://www.deque.com/blog/web-accessibility-cocacola-pattern/) of "looks fine, fails real users" emerges.

#### Manual (catches the other ~60%)

Run before every release, or quarterly for ongoing sites:

1. **Keyboard pass** — disconnect the mouse. Can you reach every interactive element? Is focus visible? Does focus order match visual order? Are skip links present?
2. **Screen reader pass** — NVDA (Windows) + VoiceOver (macOS). Walk the primary user flows. Does the content read in order? Are form labels announced? Status changes announced?
3. **Zoom pass** — 200% browser zoom. Does anything break? Is content cut off?
4. **Reduced motion pass** — `prefers-reduced-motion: reduce` in DevTools. Are animations stopped?
5. **High contrast pass** — Windows High Contrast or forced colors mode. Is text still readable?

### Common patterns the automated tools miss

Document these on your project; the universal list:

#### Focus management

- Modal opens — focus moves *into* the modal.
- Modal closes — focus returns to the trigger.
- Route change — focus to the new page's `<h1>` or main landmark.
- Form error — focus to the first invalid field.

#### Semantic HTML

- Use the right element (`<button>` not `<div onclick>`).
- Headings in order (don't skip h2 → h4).
- Landmarks (`<main>`, `<nav>`, `<aside>`, `<footer>`).
- `<address>` for contact info; `<time>` for dates.

#### ARIA — only when HTML isn't enough

The first rule of ARIA: don't use ARIA when native HTML works. `<button>` already has `role="button"` — adding it explicitly is noise. `<input type="email">` already validates as email — `aria-invalid` is for runtime state, not declaration.

When ARIA IS necessary:

- Custom widgets (combobox, tabs, dialog) — follow [WAI-ARIA APG](https://www.w3.org/WAI/ARIA/apg/) patterns precisely.
- Live regions (`aria-live="polite"` / `aria-live="assertive"`) for dynamic content updates.
- `aria-describedby` linking errors to inputs.

#### Color contrast

- **4.5:1** for body text (WCAG 1.4.3)
- **3:1** for large text (≥ 18pt or ≥ 14pt bold)
- **3:1** for UI components and graphical objects (WCAG 1.4.11)
- Test all dynamic states: default, hover, focus, active, disabled, error.

Tools: [WebAIM contrast checker](https://webaim.org/resources/contrastchecker/), [Stark](https://www.getstark.co/), browser DevTools color picker (shows contrast ratio).

#### Focus indicators

- Visible on every focusable element (WCAG 2.4.7).
- Not obscured by sticky headers or modals (WCAG 2.4.11 — new in 2.2).
- Color difference + non-color signal (outline thickness, e.g., 2px minimum).

#### Touch targets

WCAG 2.2 SC 2.5.8: minimum 24×24 CSS pixels. iOS HIG and Material both recommend 44×44 — the higher floor is friendlier.

#### Motion

- `prefers-reduced-motion: reduce` respected on all animations.
- Auto-advancing carousels need pause/stop/hide (WCAG 2.2.2).
- Parallax / scroll-jacking — careful; can trigger vestibular reactions.

#### Forms

- Every `<input>` has an associated `<label>` (visible or sr-only).
- Required fields indicated by more than color (text "(required)" or aria-required).
- Error messages associated with their field via `aria-describedby`.
- Autocomplete attributes per WCAG 1.3.5.
- Don't disable submit until valid — confusing for screen reader users.

### The PR review checklist

When reviewing a PR that touches UI, check:

- [ ] All interactive elements reachable by keyboard
- [ ] Focus visible on every focusable element
- [ ] Headings in order; no h2 → h4 skips
- [ ] Images have meaningful `alt` (or `alt=""` if decorative)
- [ ] Form controls have labels
- [ ] Color isn't the only signal for required/error states
- [ ] Contrast ratios pass for all dynamic states
- [ ] Touch targets ≥ 24×24px (preferably 44×44)
- [ ] Motion respects `prefers-reduced-motion`
- [ ] If a custom widget — does it follow APG?

### Failure modes that bite repeatedly

#### "Looks fine, fails real users"

- Image with `aria-label="Logo"` AND `alt="Logo"` — double-announced.
- `<div role="button" onclick>` without keyboard handler — mouse-only.
- Modal that traps focus — but doesn't return on close.
- Form error shown visually but not announced.

#### "Automated passes, real users blocked"

- Page reads in a non-linear order because CSS positioning overrides DOM order.
- Disabled buttons with `opacity: 0.6` — contrast drops below 3:1.
- Skip link target (`#main`) doesn't exist or isn't focusable.
- ARIA-live region updates too rapidly (announces every keystroke).

### Legal exposure

Public-facing sites in regulated jurisdictions need:

- **An accessibility statement** at a discoverable URL (often `/accessibility`).
- A **disclosure path** for users to report issues — typically an email address with a response SLA.
- **Conformance level** stated (usually "WCAG 2.2 AA").
- **Last review date.**

Template: [W3C accessibility statement generator](https://www.w3.org/WAI/planning/statements/generator/).

---

## PROJECT-SPECIFIC — fill these in

```markdown
## Conformance target

WCAG 2.2 AA

## Automated tooling

- axe-core: integrated via <Playwright | Cypress | other>
- pa11y-ci: <URLs covered>
- Lighthouse Accessibility: score ≥ 100

## Manual cadence

- Pre-release: <keyboard + SR pass on primary flows>
- Quarterly: <full a11y audit>
- Annually: <hands-on external review (Deque, Level Access, etc.)>

## Project-specific patterns we use

- Focus management: <describe how dialogs return focus, route-change focus, etc.>
- Live regions: <when we use polite vs assertive>
- Skip link: <where, target id>

## Accessibility statement

URL: <e.g., /legal/accessibility>
Last reviewed: <date>
Contact: <email for reports>
SLA: <e.g., 5 business days>
```

---

## Cross-references

- [`04-testing.md`](./04-testing.md) — axe + pa11y as automated tests
- [`05-style.md`](./05-style.md) — semantic HTML conventions
- [`07-performance.md`](./07-performance.md) — Lighthouse covers both
- [`03-code-review.md`](./03-code-review.md) — review checklist

External:
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/) — the standard
- [WAI-ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/) — patterns for custom widgets
- [axe-core rules reference](https://dequeuniversity.com/rules/axe/)
- [WebAIM](https://webaim.org) — practical accessibility guides; the WebAIM Million report
- [The A11y Project](https://www.a11yproject.com/) — checklist + patterns
- [Deque University](https://dequeuniversity.com/) — training + reference
- [W3C accessibility statement generator](https://www.w3.org/WAI/planning/statements/generator/)

---

## Maintenance cadence

- **Per PR:** automated checks run in CI; review checklist applied.
- **Pre-release:** manual keyboard + screen-reader pass on primary flows.
- **Quarterly:** full audit; update accessibility statement; check for new WCAG criteria (2.2 → 2.3?).
- **Annually:** consider an external audit (Deque, Level Access) if budget allows; their findings tend to surface what your team can't see.
- **On WCAG update:** new criteria added → assess gap → plan remediation.
- **Owner:** every contributor for their changes; one designated a11y-lead for the audit cadence + external relationships.
