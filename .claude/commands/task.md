---
description: Add or update a task on the file-based board in docs/tasks/
argument-hint: "[new task title | NNNN status=Done | NNNN note]"
allowed-tools: Read, Edit, Write, Bash, Glob
---

## Context
- Board index: @docs/tasks/README.md
- Task template: @docs/tasks/0000-example-task.md
- Existing task files: !`ls docs/tasks/ 2>/dev/null || echo "none yet"`

## Task
Interpret **$ARGUMENTS** and do exactly one of:

**A) Create a new task** (arguments are a title, no leading number):
1. Find the next zero-padded number from `docs/tasks/` (e.g. `0007`).
2. Create `docs/tasks/NNNN-<kebab-title>.md` from the `0000-example-task.md` shape. Fill the
   title and Goal from the conversation; leave acceptance criteria as TODO checkboxes if unknown.
3. Add a row to the index table in `docs/tasks/README.md` (status `Not started`).
4. Report the path. Do **not** start implementing it.

**B) Update an existing task** (arguments start with a task number):
1. Open `docs/tasks/NNNN-*.md`. Update its **Status** header (and add a dated note if one was given).
2. Update the matching row in `docs/tasks/README.md` so the header and index agree.
3. Report what changed.

Keep the per-file header and the index table in sync — that consistency is the whole point of the
board. This is the non-Linear default; projects that use an external tracker (e.g. Linear) ignore
this command.
