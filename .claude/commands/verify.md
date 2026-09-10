---
description: Run the checks and actually exercise the change; report honestly
allowed-tools: Read, Bash, Glob
---

## Context
- Branch: !`git branch --show-current`
- Changed: !`git diff --stat`

## Task
Verify the current change really works. Do not claim success without evidence.

1. Run `just lint` and `just test`. A `SKIP: ...` line means the recipe isn't implemented for
   this stack — treat that as a skip, not a pass or a failure, and note it.
2. Exercise the change for real: run the app (`just run`) / trigger the code path / check logs.
   If a path isn't logged, add a temporary log line, confirm, then remove it.
3. Report a plain-spoken result: what passed, what was skipped, what failed (with output). If you
   couldn't verify something, say so and suggest the user test it manually.
