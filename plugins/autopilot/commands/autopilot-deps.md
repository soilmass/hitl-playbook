---
description: Autopilot for dependency work. Upgrade, add, remove, or audit packages. Pauses before major bumps, large lockfile churn, or any new top-level dependency.
argument-hint: "<dep task: bump X, add Y, audit Z, etc.>"
---

Enter autopilot mode for dependency work. Load the `autopilot` skill, then apply these deps-specific rules:

**Task type:** dependencies

**Brief:** $ARGUMENTS

## Deps-specific checkpoints (yellow)

Pause via AskUserQuestion when:

- About to perform a major-version bump on any package. Show the changelog highlights as part of the question.
- Lockfile diff touches more than ~50 transitive packages. Confirm before committing the churn.
- Peer-dep conflicts emerge. Don't auto-resolve.
- About to add any new top-level dependency, even small ones. Confirm with the human.

## Deps-specific red additions

Do not (without asking):

- Install any new top-level package (`npm install <new-pkg>`, `pnpm add <new-pkg>`, etc.). New deps are surface area decisions.
- Run `npm audit fix --force` — it can break things.
- Edit `resolutions` / `overrides` blocks.
- Delete or regenerate the lockfile.

## Deps-specific handback emphasis

- **Version deltas:** exact before/after for each package changed.
- **Changelog highlights:** for any major bump, the breaking-change items relevant to this project.
- **Build + test results:** must be green; report explicitly.
- **New transitive licenses:** if the dep tree gained packages with new license types, name them.
- **Anything pinned:** if you pinned a version (instead of taking latest), say why.

Proceed.
