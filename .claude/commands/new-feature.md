---
description: Scaffold a new vertical slice (stubs + one failing test), then stop
argument-hint: "[feature name]"
allowed-tools: Read, Edit, Write, Bash, Glob
---

## Context
- Design / milestones: @docs/DESIGN.md
- Where we left off: @docs/CURRENT_TASK.md
- Recent commits: !`git log --oneline -10`

## Task
Scaffold a new vertical slice for: **$ARGUMENTS**

1. Locate where this fits in the `docs/DESIGN.md` milestone plan.
2. Create the **minimal** scaffold only — placeholder files and stub functions wired end-to-end.
3. Add **one failing test** that defines the acceptance criteria for the slice
   (skip only if this stack has no CLI test harness — say so).
4. Update `docs/CURRENT_TASK.md` (phase, next action).
5. **STOP.** Report what was created and what the next step is. Do **not** implement the full
   feature — scaffolding only.
