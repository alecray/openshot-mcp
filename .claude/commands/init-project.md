---
description: Bootstrap a new project from this template (interview + fill placeholders + first commit)
argument-hint: "[optional project name]"
allowed-tools: Read, Edit, Write, Bash, Glob
---

You are initializing a brand-new project that was copied from Alec's project template.
This is the **single** bootstrap path. Do it carefully and idempotently.

## 1. Interview (ask, then wait for answers)

Ask Alec these, concisely, in one message:
1. **Project name** (kebab-case)? — default to `$ARGUMENTS` if provided.
2. **One-sentence description** — what is this?
3. **Stack** — one of: `unreal | godot | flutter | react | java | generic`.
4. **First milestone** — what does "done" look like for v0.1?
5. **Explicit non-goals** — what should this project deliberately NOT become?
6. **Publish as an open tool/plugin?** (y/n) — if yes, we'll add an MIT LICENSE; if no
   (e.g. a game), ship no LICENSE.

## 2. Apply mechanical changes

Run the bootstrap script for the mechanical composition (one shot, via the shell):
`powershell -ExecutionPolicy Bypass -File setup.ps1 -ProjectName <name> -Stack <stack>`. It:
- copies the stack `justfile` (and a `mise.toml` for software stacks — react/flutter/java only),
- appends the stack `CLAUDE.md` section (`meta/claude/<stack>.md`) and `.gitignore`,
- copies the stack optional-enable bundle if any (e.g. `unreal/` → `.mcp.json`,
  `docs/UNREALMCP_SETUP.md`, `.claude/unreal-mcp-lessons/`) and enables `unreal-mcp` in
  `.claude/settings.local.json`,
- replaces `{{PROJECT_NAME}}` / `{{AUTHOR}}` / `{{YEAR}}` across the docs **and** the composed
  justfile/bundle docs (written UTF-8 **without** BOM),
- enables the git hooks, seeds a `VERSION` file for non-node/non-unreal stacks, and **deletes
  `meta/`**.

Then finish the parts the script intentionally leaves to you:
- **Unreal:** ensure `Config/DefaultGame.ini` has `ProjectVersion=0.1.0` under
  `[/Script/EngineSettings.GeneralProjectSettings]` (the script doesn't touch engine config).
  Confirm the justfile's `*Editor` target and `.uproject` name match the real project (UE projects
  are usually PascalCase, not the kebab name).
- **Publishing:** if publishing as an open tool/plugin, write an MIT `LICENSE` (year/author);
  otherwise leave none and note "proprietary" in the README.
- **Delete `setup.ps1`** — template-only, no longer needed once it has run.

## 3. Fill the documentation

- `CLAUDE.md` → fill the `## Project specifics` section from the interview (what it is, stack,
  initial architecture sketch, common tasks if known, what NOT to do).
- `docs/DESIGN.md` → fill philosophy, stack rationale, the v0.1 milestone, and the explicit
  non-goals. Leave deeper sections as clearly-marked TODO.
- `docs/adr/0001-stack-choice.md` → create from the MADR format recording why this stack was
  chosen over alternatives.
- `docs/CURRENT_TASK.md` → seed: phase = "v0.1 — project setup", next action = first real slice.

## 4. First commit

```
git add -A
git commit -m "chore: initialize project from template"
```

(The pre-commit hook will stamp the version; the commit-msg hook will accept this Conventional
Commit.)

## 5. Report

Summarize what was created, confirm `meta/` is gone and the hook is enabled, and suggest the
first real working session prompt (the first vertical slice toward the v0.1 milestone). Then stop.
