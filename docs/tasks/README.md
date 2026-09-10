# Tasks — file-based work board

These markdown files **are** the backlog. One `.md` per task, numbered so the folder reads as a
roadmap; the table below is the index. This is the **default, non-Linear** tracker — it lives in
the repo, diffs in PRs, and needs no external service. (`docs/CURRENT_TASK.md` is different: it's
the tiny "where we left off *right now*" pointer. This board is the whole backlog.)

> Use `/task` to add a task or flip a status — it creates the next-numbered file from the template
> and updates this index.

## How it works
- **One file per task:** `NNNN-kebab-title.md` (zero-padded). Copy `0000-example-task.md`.
- **Status** lives in each file's header *and* this table — keep them in sync (`/task` does).
  Statuses: `Not started` · `In progress` · `Blocked` · `Done` · `Shelved`.
- **Group by milestone** (the `M` column ties back to `docs/DESIGN.md` §6). Optional.
- Close a task when its acceptance criteria pass; reference the commit/tag that did it.

## Index
| # | Task | M | Status | Priority | Depends on |
|---|------|---|--------|----------|------------|
| 0000 | [Example task (template — copy me)](0000-example-task.md) | — | Not started | — | none |

<!-- Add rows as you add task files. Keep newest milestones grouped together. -->
