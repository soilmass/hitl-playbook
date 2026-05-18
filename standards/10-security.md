# 10 — Security

**Purpose:** OWASP Top 10 risks mitigated; secrets stay out of git; a disclosure path exists for external researchers.
**Anchors:** [OWASP Top 10 (2021)](https://owasp.org/Top10/) · [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/) · [RFC 9116 — security.txt](https://www.rfc-editor.org/rfc/rfc9116.html) · [Mozilla Observatory](https://observatory.mozilla.org/) · [OWASP Secure Headers Project](https://owasp.org/www-project-secure-headers/)
**Tier:** Operations

---

## Why this procedure exists

Security failures are catastrophic and asymmetric — months of work undone by one missed input validation or a leaked API key. They're also the failure mode most prone to silent decay: code that's secure today becomes vulnerable when a new dependency lands, a new endpoint is added without auth, or a CSP header gets relaxed "just for this feature."

A standard converts security from "we'll think about it later" to "we have checkpoints throughout."

**Failure modes when this procedure is missing:**

- API keys committed to git history; rotating them is now mandatory.
- A new `/api/<endpoint>` ships without input validation; SQL injection finds it.
- CSP is added with `unsafe-inline` "temporarily" for a widget; never removed.
- A vulnerable dependency ships for 6 months because nobody owns CVE triage.
- A researcher reports a bug but has no idea where to email; they post on Twitter instead.

---

## The standard

### Secret hygiene — never commit secrets

This is the most-violated and easiest-to-fix rule.

**What counts as a secret:**

- API keys (Resend, Sentry, Stripe, etc.)
- Database passwords, connection strings with credentials
- JWT signing keys
- OAuth client secrets
- Cookie signing keys
- Anything labeled "secret" or "token" by the issuing service

**Procedure:**

1. `.env.local` (or whatever your stack uses for local secrets) — gitignored. Always.
2. `.env.example` — committed; documents which env vars exist, not their values. Comment names the source/vendor.
3. Production secrets live in the hosting provider's env-var UI (Vercel, Netlify, AWS Secrets Manager, etc.) — never in code.
4. Pre-commit hook (optional but recommended): `git-secrets`, `detect-secrets`, or [Gitleaks](https://github.com/gitleaks/gitleaks) scans the diff for accidental secret patterns.

**If a secret is committed:**

1. **Rotate the secret immediately.** Git history is permanent; assume the secret is compromised.
2. Remove from new commits.
3. Optional: `git filter-repo` to scrub from history — but treat the secret as compromised regardless.

### OWASP Top 10 mitigations

The [OWASP Top 10 (2021)](https://owasp.org/Top10/) — every web project should defend against all 10.

#### A01 Broken Access Control

- Auth checks on every endpoint that requires them. Don't rely on "if the user can find this URL, they're authorized."
- Default to deny; explicitly allow.
- Don't expose internal IDs in URLs without authorization check.
- For form endpoints: method-not-allowed on non-POST when only POST is intended.

#### A02 Cryptographic Failures

- HTTPS everywhere. HSTS preload-eligible cert.
- Don't roll your own crypto.
- Hash passwords with bcrypt/argon2 + salt; never plain or MD5.
- Sensitive data encrypted at rest (DB encryption, S3 SSE).

#### A03 Injection

- All user input validated server-side. Client validation is UX, not security.
- Use Zod / Yup / Joi for typed input parsing.
- Parameterized queries (or an ORM) — never string concatenation.
- Escape HTML when rendering user content; React's JSX does this by default.
- Be wary of `dangerouslySetInnerHTML` / `v-html` / equivalents.

#### A04 Insecure Design

- Threat-model new features. Who could attack this? What's their gain?
- Rate-limit endpoints (Cloudflare, Vercel WAF, in-app counters).
- CAPTCHA / Turnstile on forms.
- Defense in depth — don't rely on one control.

#### A05 Security Misconfiguration

- Required security headers (see "Security headers" below).
- `Server` / `X-Powered-By` headers stripped (don't advertise stack version).
- Errors don't leak stack traces in production (`NODE_ENV=production`).
- Default credentials changed on any vendor account.

#### A06 Vulnerable and Outdated Components

- `pnpm audit --prod --audit-level=high` in CI; fail on findings.
- Dependabot configured; weekly review (see [`09-dependencies.md`](./09-dependencies.md)).
- CVE SLA: critical 24h, high 7d.

#### A07 Identification and Authentication Failures

- Bot protection on auth endpoints.
- Rate-limit login attempts.
- Strong password requirements (length matters more than complexity).
- MFA where possible.
- Session expiration; secure session cookies (`HttpOnly`, `Secure`, `SameSite=Lax`).

#### A08 Software and Data Integrity Failures

- CI from a trusted environment (GitHub Actions, not your laptop).
- Code signing where applicable.
- Dependency provenance (`npm provenance`) when available.
- Don't auto-update third-party scripts (analytics) — vendor pinning + integrity checks (`<script integrity="sha384-...">`).

#### A09 Security Logging and Monitoring

- Sentry or equivalent capturing exceptions.
- Failed auth attempts logged.
- Suspicious patterns (unexpected admin actions, mass-data-read) flagged.
- Logs include `traceId` for correlation; not the secret values themselves.

#### A10 Server-Side Request Forgery (SSRF)

- Don't fetch arbitrary user-provided URLs from your server.
- If you must, allowlist domains.
- Block internal IP ranges (169.254.169.254, 10.0.0.0/8, 192.168.0.0/16, 127.0.0.1).

### Security headers

Add via web server / framework middleware. Verify with [Mozilla Observatory](https://observatory.mozilla.org/):

```
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
Content-Security-Policy: <restrictive policy with nonce>
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: <deny features you don't use>
Cross-Origin-Resource-Policy: same-site
Cross-Origin-Opener-Policy: same-origin
```

**CSP discipline:**

- Use per-request `nonce` for inline scripts (preferred) or strict-dynamic + hashes.
- Never `'unsafe-inline'` or `'unsafe-eval'` unless absolutely necessary and time-limited with a ticket.
- Test in `Content-Security-Policy-Report-Only` first, then enforce.

### Vulnerability disclosure — `security.txt`

[RFC 9116](https://www.rfc-editor.org/rfc/rfc9116.html) defines `security.txt` at `/.well-known/security.txt`:

```
# /.well-known/security.txt
Contact: mailto:security@yourdomain.example
Contact: https://yourdomain.example/security
Expires: 2027-01-01T00:00:00.000Z
Preferred-Languages: en
Canonical: https://yourdomain.example/.well-known/security.txt
Policy: https://yourdomain.example/security-policy
```

`Expires` is required; refresh annually.

If someone reports a vulnerability:

1. Acknowledge within 48 hours.
2. Triage: confirm reproduction, assess severity.
3. Fix per SLA (critical 24h, high 7d).
4. Optionally: credit the reporter in the fix's release notes.
5. Optionally: bug bounty payment.

### CODEOWNERS for security-critical paths

Require additional review on changes to:

- Middleware / route handlers
- API endpoints
- Authentication code
- CSP / header configuration
- CI workflows (could leak secrets if misconfigured)
- `.github/workflows/`

GitHub's CODEOWNERS auto-requests review from designated reviewers when these paths change.

### Incident response

When (not if) something happens:

1. **Confirm.** Is this real? Get reproduction or evidence.
2. **Contain.** Stop the bleeding — disable the vulnerable feature, rotate the leaked secret, block the attacker IP.
3. **Fix.** Apply the actual repair, deploy.
4. **Communicate.** Notify affected users; comply with breach-notification laws (GDPR 72-hour clock for EU users; per-state laws in US).
5. **Post-mortem.** Within 48 hours: timeline, root cause, what we changed, what we'll change to prevent recurrence.

---

## PROJECT-SPECIFIC — fill these in

```markdown
## Secret management

- Local: <.env.local; gitignored>
- Production: <Vercel project env vars | AWS Secrets Manager | ...>
- Rotation cadence: <e.g., quarterly for non-customer-facing; immediate on compromise>

## CSP

[Paste current CSP header verbatim, with reasoning per directive.]
[Notes on any temporary exceptions, with expiry date.]

## Vulnerability disclosure

security.txt: <path>
Contact email: <address>
SLA acknowledged: <X hours>
SLA resolved (critical / high / medium): <Y / Z / N>

## CODEOWNERS — security-critical paths

[List paths + designated reviewer]

## CI security gates

- pnpm audit --prod --audit-level=high: <enforced as status check>
- Secret scanning: <Gitleaks | TruffleHog | GitHub's built-in>
- SAST: <Snyk Code | CodeQL | none>

## Compliance scope

[Any regulatory framework — GDPR, CCPA, HIPAA, SOC 2 — that applies]
```

---

## Cross-references

- [`02-git.md`](./02-git.md) — CODEOWNERS + branch protection
- [`04-testing.md`](./04-testing.md) — security tests as CI gates
- [`09-dependencies.md`](./09-dependencies.md) — CVE triage workflow
- [`11-adrs.md`](./11-adrs.md) — security architecture decisions belong in ADRs

External:
- [OWASP Top 10 (2021)](https://owasp.org/Top10/)
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/) — practical patterns per concern
- [RFC 9116 (security.txt)](https://www.rfc-editor.org/rfc/rfc9116.html)
- [Mozilla Observatory](https://observatory.mozilla.org/) — scan and grade your headers
- [SSL Labs](https://www.ssllabs.com/ssltest/) — TLS configuration test
- [OWASP Secure Headers Project](https://owasp.org/www-project-secure-headers/)
- [CSP Evaluator](https://csp-evaluator.withgoogle.com/) — Google's CSP analyzer
- [Have I Been Pwned](https://haveibeenpwned.com/) — check for credential exposure

---

## Maintenance cadence

- **Per PR:** security review for paths touched (auto via CODEOWNERS for sensitive areas).
- **Weekly:** Dependabot security PRs triaged.
- **Monthly:** Mozilla Observatory + SSL Labs scan; should grade A+.
- **Quarterly:** review CSP for `unsafe-*` debt; rotate non-customer-facing secrets; audit access lists.
- **Annually:** refresh `security.txt` Expires; consider external pen test.
- **On incident:** post-mortem within 48 hours; standard updated with lessons learned.
- **Owner:** the project's security reviewer (often same as tech lead in small teams).
