# Rubric: handback_done_quality_v1

**Returns:** binary {"label": "yes"|"no", "reason": "<one sentence>"}

**Question:** Does the handback's `Done:` section contain a SUBSTANTIVE, NON-TRIVIAL summary of what shipped — not just "Done." or "Task complete" or a one-word filler?

**Pass examples ("yes"):**
- `**Done:** Added send_confirmation(user) to handlers/notify.js with stubbed POST.`
- `**Done:** Fixed login.test.ts apostrophe handling by updating validator regex in src/auth/login.ts.`

**Fail examples ("no"):**
- `**Done:** ok.`
- `**Done:** Task complete.`
- `**Done:** -`
- (section missing entirely)
- `**Done:** Cleanup performed.` (substantive on the surface but says nothing about WHAT was cleaned)

**Edge cases:**
- One-sentence summaries that name a concrete file/function: **YES**
- Multi-sentence prose without naming anything specific: **NO**
- "Done: see Changed: section" — **NO** (the Done: line itself must summarize)

---

## Judge prompt template

System:

You evaluate the Done: section of a handback report from an AI coding agent. Output strict JSON only:

```
{"label": "yes" | "no", "reason": "<one short sentence>"}
```

The rubric is binary. The Done: section passes iff it contains a substantive, non-trivial summary that names what was actually shipped (file, function, behavior). Trivial phrasings like "ok", "Task complete", "-", or missing section all fail.

User:

Brief: {brief}

Handback (final agent response):

```
{handback}
```

Apply the rubric. Output only the JSON object.
