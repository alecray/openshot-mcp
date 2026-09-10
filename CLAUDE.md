# CLAUDE.md â€” openshot-mcp

> Stack-agnostic working conventions for this project. The `## Project specifics`
> section at the bottom is filled in per-project by `/init-project`. Everything above
> it is shared across all of Alec's projects â€” edit only if the convention itself changes.

## How we work

- **Design-doc first.** Non-trivial work starts from `docs/DESIGN.md`. If a decision isn't
  captured there yet, capture it before building. Record consequential choices as ADRs in
  `docs/adr/` (use `/adr`); keep the through-line and ADR index in `docs/DECISIONS.md`. Capture
  repeatable "how to add X" recipes in `docs/guides/`.
- **Vertical slices, one phase at a time.** Build the smallest end-to-end slice that proves a
  piece of the design. **Stop after each phase** and report â€” do not chain phases unless told to.
- **Plan before acting.** For any multi-step task, outline the plan and the files you'll touch
  before editing. Explain what changed and why after each step.
- **Token control.** Don't dump the whole project in one response. Scope each response to the
  current phase: phase name â†’ files to change â†’ the change â†’ a short test checklist â†’ the next step.
  This sits **on top of** the global token-discipline + model-routing rules in `~/.claude/CLAUDE.md`
  (cap noisy command/build output to a log + filter, read narrow, delegate big read-heavy sweeps with
  summary-only return). Game projects under `E:\Game Projects` also inherit that workspace
  `CLAUDE.md`, including the UE build-log redirect+filter pattern.
- **Keep `docs/CURRENT_TASK.md` current.** At the end of a session (and during `/ship`), update it
  with the active phase, last action, next action, and open questions. Read it at session start.
- **Backlog lives in `docs/tasks/`.** One markdown file per task â€” a file-based board (use `/task`),
  indexed by `docs/tasks/README.md`. This is the default, non-Linear tracker; a project that uses an
  external tracker ignores it. `docs/CURRENT_TASK.md` is the "right now" pointer; `docs/tasks/` is the
  whole backlog.

## Subagent delegation

- Orchestrate with Opus; delegate focused implementation to **Sonnet** subagents (see
  `.claude/agents/implementer.md`). Per the global model-routing rules, run mechanical work
  (search, summarize, commit/PR text, formatting) on **Haiku** sessions and keep judgment work
  (architecture, debugging, multi-file refactors, anything correctness-critical) on Opus/Sonnet.
- When delegating, pass **explicit context** about what's already been tried and decided. Never let
  a subagent re-research something the parent already resolved.
- Preserve the full list of modified files and the exact test commands when context is compacted.

## Versioning

- Every project carries a **commit-count version stamp**, bumped by `.githooks/pre-commit`:
  - Node: bump the `package.json` patch.
  - Engine (Unreal): `Config/DefaultGame.ini` â†’ `ProjectVersion=0.1.<commit count>`.
  - Anything else: a top-level `VERSION` file (`0.1.<commit count>`).
- Enable the hook once per fresh clone: `git config core.hooksPath .githooks`.
- **Display the version on-screen** (title screen / HUD / about box) by reading it at runtime.

## Verification (never claim success blind)

- After a change, actually run it: `just test`, launch the app, and/or check logs â€” then report
  the real result. If something is skipped or failing, say so plainly with the output.
- If a code path isn't logged, add a temporary log line to confirm the fix, then remove it.
- If something repeatedly fails to verify, flag it for the user to test manually rather than
  guessing.

## Commits & PRs

- **Conventional Commits**: `type: subject` where type is one of
  `feat | fix | docs | style | refactor | perf | test | build | ci | chore`.
  Keep the subject plain English and human-readable ("feat: add pause menu with settings").
  The `.githooks/commit-msg` hook enforces the prefix.
- Commit per logical task. Tag shippable milestones (`git tag v0.2.0`).
- PR titles are plain English describing what changed â€” no class names or jargon.

## The `just` command interface

All automation goes through `just` so it's identical across stacks. CI, `/verify`, and `/ship`
call these â€” only the `justfile` knows the real stack command.

- **Contract recipes** (implement for every stack): `run`, `build`.
- **Advisory recipes** (optional for engine stacks with no clean CLI): `test`, `lint`. An
  unimplemented advisory recipe prints `SKIP: not implemented for this stack` and is treated as a
  skip (not a failure) by CI and the slash commands.

## Protected paths

Never modify without explicit instruction: `legacy/`, `generated/`, vendored/third-party dirs,
`.env*`, and `docs/DESIGN.md`. The `.claude/hooks/protect-files.ps1` hook blocks edits to these.

## Placeholder-first

Keep gameplay/business logic asset-agnostic so real art, data, or content can drop in over
placeholders (graybox primitives, stub data) without code changes.

## Licensing

Games ship **no LICENSE** by default (proprietary). Only add a LICENSE (MIT) for tools/plugins
intended to be published.

---

## Project specifics

> Filled in by `/init-project`. Until then this is a TODO.

- **What this is:** TODO â€” one-sentence description.
- **Stack / engine:** TODO.
- **Architecture:** TODO â€” key systems and how they fit together.
- **Common tasks:** TODO â€” e.g. "add an X: subclass Y, add a row to Z".
- **What NOT to do:** TODO â€” out-of-scope systems, things to protect.
- **Run/build/test commands:** see `justfile` (`just --list`).
