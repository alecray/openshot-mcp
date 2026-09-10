---
description: Load project context for a new session and state the next step
allowed-tools: Read, Bash, Glob
---

Read and summarize, briefly:
1. @CLAUDE.md (the project-specifics section especially)
2. @docs/DESIGN.md (current milestone + non-goals)
3. @docs/CURRENT_TASK.md
4. Recent work: !`git log --oneline -15`
5. Working tree: !`git status --short`

Then state, in a few lines: the **current phase**, what was **last** worked on, the **next logical
step**, and any **blockers**. End by asking what to work on.
