# Docs

Project-specific reference docs that build on the playbook's 12 standards. The standards themselves live at [`../standards/`](../standards/).

## Contents

- **[`hitl-framework.md`](./hitl-framework.md)** — Human-in-the-loop development methodology. Extends standard 12 (AI Agent Collaboration) with the in-task supervision loop.
- **[`autopilot-plugin.md`](./autopilot-plugin.md)** — Canonical reference for the autopilot plugin. The plugin source lives at [`../plugins/autopilot/`](../plugins/autopilot/); this doc explains what it implements and why.
- **[`adr/`](./adr/)** — Architecture Decision Records, one per significant decision. Append-only per [`../standards/11-adrs.md`](../standards/11-adrs.md).

## Reading order

For someone new to the HITL extension:

1. [`../standards/12-agents.md`](../standards/12-agents.md) — baseline for AI agent collaboration.
2. [`hitl-framework.md`](./hitl-framework.md) — the methodology.
3. [`autopilot-plugin.md`](./autopilot-plugin.md) — the concrete implementation.
4. [`adr/`](./adr/) — the decisions, in numerical order, when a particular choice needs context.

## Scope

These docs cover *this project's* HITL extension. Projects adopting the playbook should treat them as a reference, not a requirement — the 12 standards are the playbook's contract; HITL is an opt-in extension for teams running high-autonomy agent workflows.
