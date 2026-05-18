# 07 — Performance

**Purpose:** Core Web Vitals stay green; regressions are caught before users feel them.
**Anchors:** [web.dev/vitals](https://web.dev/vitals) · [Lighthouse CI](https://github.com/GoogleChrome/lighthouse-ci) · [Chrome User Experience Report](https://developer.chrome.com/docs/crux/) · [INP](https://web.dev/inp)
**Tier:** Quality

---

## Why this procedure exists

Performance affects every business metric that matters: conversion, bounce rate, SEO ranking, and user-reported satisfaction. Google's [Chrome UX Report data](https://developer.chrome.com/docs/crux/) consistently shows ~30%+ bounce-rate degradation when LCP slips past 4 seconds.

Performance is also one of the quality concerns most prone to silent decay — every feature you add costs some milliseconds; the cumulative drift over months adds seconds. Without explicit budgets and CI enforcement, the team only notices when users complain.

**Failure modes when this procedure is missing:**

- LCP regresses 800ms over a quarter; no single PR is "the cause."
- A new third-party script (analytics, chat widget) ships and tanks INP.
- An image-heavy gallery launches without `loading="lazy"`; mobile users see 5+ MB downloads.
- Fonts cause CLS at load; nobody knows because nobody profiles.
- A "small change" ships a 200KB library to do work that didn't need it.

---

## The standard

### Core Web Vitals — the three metrics that matter most

Per [web.dev/vitals](https://web.dev/vitals), measured at P75 of real user data over 28 days:

| Metric | Good | Needs improvement | Poor | What it measures |
|---|---|---|---|---|
| **LCP** Largest Contentful Paint | ≤ 2.5s | 2.5–4.0s | > 4.0s | Time until the main content is visible |
| **INP** Interaction to Next Paint | ≤ 200ms | 200–500ms | > 500ms | Latency of the worst-case user interaction |
| **CLS** Cumulative Layout Shift | ≤ 0.1 | 0.1–0.25 | > 0.25 | Visual stability — does content jump around? |

INP replaced FID in March 2024. If your tooling still references FID, upgrade.

Supporting metrics (useful but not deal-breakers):

- **FCP** First Contentful Paint: ≤ 1.8s good
- **TTFB** Time to First Byte: ≤ 800ms good
- **TBT** Total Blocking Time (lab proxy for INP): ≤ 200ms good

### Budgets — set them per project

Define explicit budgets in CI. Lighthouse CI enforces these as hard PR gates:

```json
{
  "ci": {
    "assert": {
      "assertions": {
        "categories:performance": ["error", { "minScore": 0.9 }],
        "largest-contentful-paint": ["error", { "maxNumericValue": 2500 }],
        "cumulative-layout-shift": ["error", { "maxNumericValue": 0.1 }],
        "total-blocking-time": ["error", { "maxNumericValue": 200 }],
        "resource-summary:script:size": ["error", { "maxNumericValue": 200000 }],
        "resource-summary:image:size": ["error", { "maxNumericValue": 500000 }]
      }
    }
  }
}
```

A PR that breaks the budget can't merge. The team negotiates the budget; the code follows it.

### Bundle size budgets

Per [size-limit](https://github.com/ai/size-limit) (or webpack-bundle-analyzer, rollup-plugin-visualizer, etc.):

- **Per route initial JS**: ≤ 150 KB gzipped is a good upper bound for most sites.
- **Per third-party widget**: ≤ 50 KB gzipped.
- **Per image**: ≤ 500 KB; serve responsive sizes.

Enforce in CI. Budgets that aren't enforced will drift.

### The optimization toolkit

#### Images (often the biggest LCP win)

- Explicit `width` and `height` to prevent CLS.
- `loading="eager"` only on the LCP image; `loading="lazy"` on everything else.
- `fetchpriority="high"` on the LCP image; default on others.
- `decoding="async"` to keep decode off the main thread.
- Modern formats (AVIF, WebP) with `<picture>` fallback.
- Responsive `srcset` for breakpoints.
- For CDN-hosted images: use query-param sizing (e.g., Squarespace `?format=1500w`, Cloudinary `c_scale,w_1500`).

#### Fonts

- Self-host or use CDN with `preconnect`.
- `font-display: swap` to avoid FOIT.
- Subset to the characters actually used (Google Fonts does this automatically; with self-hosted, use tools like [glyphhanger](https://github.com/zachleat/glyphhanger)).
- Limit weight/style variations to what's used.
- Variable fonts when supported — one file, multiple axes.

#### JavaScript

- Code split — only ship what's needed for the current route.
- Lazy-load below-the-fold interactivity (`client:visible` in Astro, dynamic `import()` in React/Vue).
- Tree-shake imports (`import { only } from "lib"` not `import * as Lib from "lib"`).
- Audit dependencies for size cost — Bundlephobia, [`size-limit`](https://github.com/ai/size-limit), or your bundler's analyzer.
- Defer non-critical third-party scripts (`<script async defer>` or web workers via [Partytown](https://partytown.builder.io/)).

#### CSS

- Inline critical CSS for above-the-fold rendering.
- Defer non-critical CSS.
- Avoid CSS-in-JS for SSR (extra runtime, extra bundle); prefer compile-time solutions or utility-first (Tailwind).
- Watch for `@import` chains in CSS that block render.

#### Server

- Render at the edge when content is dynamic but cacheable.
- Static-generate (SSG) what doesn't change per-user.
- Cache HTTP responses appropriately (`Cache-Control: public, max-age=N, immutable` for fingerprinted assets).
- HTTP/2 or HTTP/3 — most CDNs do this by default.
- Reduce TTFB via CDN edge + warm caches.

### Measurement workflow

**Lab data** (synthetic, reproducible):

- Lighthouse CI on every PR (preview deployment).
- WebPageTest for deeper analysis (waterfall, filmstrip).

**Field data** (real users):

- Chrome UX Report (CrUX) — public; available for any indexed URL.
- Web Analytics tool's CWV reporting (Vercel Speed Insights, Google PageSpeed Insights, Cloudflare Web Analytics).
- RUM (Real User Monitoring) — Sentry Performance, Datadog RUM, etc.

**Lab vs. field** — they diverge. Lab tells you what the code could be; field tells you what users actually experience. Optimize for field; use lab for regression detection.

### Regression triage workflow

When field CWV degrades:

1. **Confirm the trend.** One bad data point is noise; a week of degradation is a trend.
2. **Bisect by deploy.** When did it start? Match to a deploy timestamp.
3. **Profile the suspect commit.** Lighthouse on prod vs. lab.
4. **Identify the regression's character.** Bundle bloat? New script? Image change? Render-blocking resource?
5. **Fix or revert.** If the cause is clear and the fix is small, ship the fix. If unclear, revert the deploy and investigate offline.

### Common performance anti-patterns

- **Hydrating everything** — components that don't need interactivity should render server-side and stop.
- **Loading the entire icon library** for two icons.
- **CSS-in-JS at runtime** on SSR — pay the runtime cost on every request.
- **Polyfills shipped to modern browsers** — use differential serving.
- **Synchronous third-party scripts** (analytics, chat) in `<head>` blocking render.
- **Web fonts loaded after CSS parses** — preload them.
- **Animations on `top` / `left`** instead of `transform` — triggers layout instead of just composite.

---

## PROJECT-SPECIFIC — fill these in

```markdown
## Targets

Field-data P75 budgets:
- LCP: ≤ 2.5s
- INP: ≤ 200ms
- CLS: ≤ 0.1
- TTFB: ≤ 800ms

Lab CI thresholds (lighthouserc.json):
- Performance score: ≥ 0.9
- LCP: ≤ 2500ms
- TBT: ≤ 200ms
- CLS: ≤ 0.1

Bundle budgets (size-limit):
- [list per entry, e.g., "main route initial JS: 80KB gzipped"]

## Measurement tooling

- Lab: <Lighthouse CI / WebPageTest>
- Field: <Vercel Speed Insights / Google PageSpeed Insights / RUM tool>

## Review cadence

- Weekly: review field CWV; flag any P75 regression
- Per deploy: Lighthouse CI runs; PR blocked if budgets fail
- Quarterly: full performance audit, re-evaluate budgets

## Optimization priorities for this stack

[Project-specific: which optimization moves give the most LCP/INP improvement.]
```

---

## Cross-references

- [`04-testing.md`](./04-testing.md) — Lighthouse CI is a perf test
- [`06-debugging.md`](./06-debugging.md) — perf regression diagnosis
- [`09-dependencies.md`](./09-dependencies.md) — every dep has a perf cost
- [`08-accessibility.md`](./08-accessibility.md) — Lighthouse audits both at once

External:
- [web.dev/vitals](https://web.dev/vitals) — definitions + thresholds
- [Lighthouse CI](https://github.com/GoogleChrome/lighthouse-ci)
- [INP guide](https://web.dev/inp)
- [Patrick Meenan's WebPageTest](https://www.webpagetest.org/)
- [Chrome UX Report](https://developer.chrome.com/docs/crux/)
- [Addy Osmani: image optimization](https://images.guide/)

---

## Maintenance cadence

- **Per PR:** Lighthouse CI runs; failure blocks merge.
- **Weekly:** review field data; flag regressions before they're chronic.
- **Quarterly:** full performance audit; re-evaluate budgets; check if new metrics matter (INP replaced FID — what's next?).
- **Owner:** every contributor for their changes; one designated perf-lead for the budget + measurement infrastructure.
