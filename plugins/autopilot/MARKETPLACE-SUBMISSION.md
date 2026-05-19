# Marketplace submission notes

Reference material for submitting this plugin to the official Anthropic Claude Code marketplace at <https://platform.claude.com/plugins/submit> (or `claude.ai/settings/plugins/submit`). Not user-facing; remove or relocate after submission lands.

---

## Submission form copy

**Plugin name:** `autopilot`

**Tagline (one line):**

> High-autonomy mode for Claude Code with surgical human-in-the-loop gates: proceeds by default, pauses via AskUserQuestion at categorical branch points, hard-blocks destructive operations.

**Description:**

> A Claude Code plugin for running Claude on longer-horizon tasks with structured human supervision. The plugin classifies every action into three tiers — *green* (proceed silently), *yellow* (pause via structured `AskUserQuestion`), *red* (hard-stopped by a PreToolUse hook) — and ships a Node-based hook guard with 85-case regression coverage against destructive patterns (`rm -rf`, force-push, `npm publish`, SQL drops, writes outside `cwd`, etc.).
>
> Includes six task-type-specific commands (`/autopilot:autopilot-bugfix`, `-refactor`, `-feature`, `-deps`, `-tests`, `-chore`) plus a generic `/autopilot:autopilot`. Two read-only subagents (`scout` for research, `verifier` for second-opinion code review) handle questions that don't need human judgment. Per-session audit trail (`.claude/autopilot-logs/<session>.jsonl` + decision log markdown) plus tool-call budget tracking (`/budget`, configurable yellow/red thresholds).
>
> Methodology and design decisions documented as 17 ADRs in the source repo. Eval harness ships alongside the plugin so future changes can be measured against a canonical Sonnet baseline. Per-criterion bootstrap-CI scoring with judge calibration (Gwet's AC2 ≥ 0.7) per ADR-0017.

**Keywords:** `autopilot`, `hitl`, `human-in-the-loop`, `agent-governance`, `claude-code`

**License:** MIT

**Repository:** <https://github.com/soilmass/hitl-playbook>

**Homepage:** <https://github.com/soilmass/hitl-playbook/tree/main/plugins/autopilot>

**Author:** Edison Steele (`edisonsteele@gmail.com`)

**Minimum Claude Code version:** `>=2.0.0` (declared in `plugin.json` `engines`)

---

## Pre-submission checklist

| Requirement | Status |
|---|---|
| `.claude-plugin/plugin.json` parses + has `name`, `version`, `description`, `author`, `license` | ✅ |
| `LICENSE` file at repo root (GitHub auto-detects MIT) | ✅ |
| `plugins/autopilot/README.md` with install + first task + verify | ✅ |
| All skills are directory-format (`skills/<name>/SKILL.md`) with valid YAML frontmatter | ✅ verified by CI |
| All commands + agents have valid YAML frontmatter | ✅ verified by CI |
| All JSON parses (`plugin.json`, `hooks.json`) | ✅ verified by CI |
| Hook regression suite green on Linux + macOS | ✅ verified by CI |
| Link check clean | ✅ verified by CI |
| Markdown lint clean (advisory) | ✅ verified by CI |
| Public repo with CI history | ✅ green at <https://github.com/soilmass/hitl-playbook> |
| Known limitations documented | ✅ `docs/autopilot-plugin.md` Known Limitations + ADR-0014 |
| Defense-in-depth note (hook is not a security boundary) | ✅ |
| Empirical baseline scores published | ✅ v2 10-task per-criterion baseline in `evals/README.md`; overall pass-rate **94.7** across applicable criteria (was 71.2 under v1 composite). All 8 PRs of ADR-0017 methodology shift complete except PR-7 (handback judge migration, gated on user labels). |

---

## What to flag to the marketplace reviewer

1. **AskUserQuestion is non-functional in `claude --print` mode** (ADR-0014). The plugin is fundamentally an *interactive-mode* tool. CI / batch / eval use cases get degraded behavior. This is documented in the user-facing README + the canonical reference.
2. **Recommended model: Sonnet or stronger.** Verified empirically: Haiku reliably ignores categorical yellow-tier triggers. Plugin's HITL guarantees are model-dependent.
3. **Hook is not a security boundary against an adversarial / compromised model.** The Node guard stops accidents and well-behaved agents; novel indirection paths require OS-level sandboxing. ADR-0006.

These are stated up front, in user-facing docs, with workarounds where workarounds exist.

---

## After submission

1. Once approved, update `plugins/autopilot/README.md` install snippet to use the marketplace install command (`/plugin install autopilot@claude-plugins-official` or whatever Anthropic's canonical form is).
2. Bump version per `CHANGELOG.md` policy — adding a marketplace install path is user-visible and warrants a minor bump (currently at `0.3.0`).
3. Delete this file (or move to `docs/`); it has no post-submission value.

---

## What I am NOT submitting

- The `plugins/` directory's other potential plugins (none yet — this is a single-plugin repo).
- The eval harness, probes, postmortems infrastructure — that's project-specific repo content, not part of the plugin distribution.
- ADRs — they're maintained in the source repo; the plugin's homepage links to them.
