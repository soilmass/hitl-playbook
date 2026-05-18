---
description: Autopilot for new features. Builds an end-to-end capability within a scoped brief. Pauses after planning, on architectural forks, and before new dependencies or schema changes.
argument-hint: <feature description with explicit scope + constraints>
---

Enter autopilot mode for a feature build. Load the `autopilot` skill, then apply these feature-specific rules:

**Task type:** new feature

**Brief:** $ARGUMENTS

## Feature-specific checkpoints (yellow)

Pause via AskUserQuestion:

- **After producing a plan, before writing code.** Surface the plan as an option set if there are forks; otherwise confirm the plan and proceed.
- **On any architectural fork:** state shape, API shape, where the code lives, naming of new surfaces. These are exactly the choices the human wants input on.
- **Before adding any new top-level dependency.** Even small ones — they accumulate.
- **Before adding a new route, new DB column, new env var, new config key.** These are surface area decisions.

## Feature-specific red additions

Do not (without asking):

- Run database migrations.
- Write to schema files.
- Edit authentication, authorization, or permission code.
- Add a new top-level dependency without surfacing the alternatives.

## Feature-specific handback emphasis

- **Built:** the capability shipped, one paragraph.
- **Deliberately deferred:** what's not in this PR and why.
- **New surface area:** routes, env vars, configs, schema columns, top-level deps — itemized.
- **Test coverage:** at least the happy path + one edge case; name them.
- **Follow-ups:** small concrete TODOs that would round out the feature, for a future PR.

Proceed.
