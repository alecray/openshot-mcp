---
description: Run pre-ship checks, update changelog/state, and open a PR
allowed-tools: Read, Edit, Write, Bash, Glob
---

## Context
- Branch: !`git branch --show-current`
- Diff vs main: !`git diff main --stat`

## Task
1. Run `just check`. A `SKIP: ...` from an advisory recipe is fine; a real failure **stops** the
   ship — report it and halt.
2. Run `just scan-secrets` (skips gracefully if gitleaks isn't installed). If it flags anything
   real, stop and report.
3. Update `docs/CURRENT_TASK.md` (what shipped, next action).
4. Run `just changelog` to refresh `CHANGELOG.md` (or update it by hand if git-cliff is absent).
5. Commit any doc/changelog updates with a Conventional Commit message.
6. Open the PR: `gh pr create --fill`. Report the PR URL.
