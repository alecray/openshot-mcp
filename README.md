# openshot-mcp

<!-- One-sentence description of what this project is. -->
TODO â€” short description.

<!-- Uncomment once the repo exists on GitHub and CI is on:
![CI](https://github.com/Alec/openshot-mcp/actions/workflows/ci.yml/badge.svg)
-->

## Quickstart

```sh
cp .env.example .env       # then fill in any values
just run                   # see `just --list` for all commands
```

> Commands go through [`just`](https://github.com/casey/just). Run `just --list` for the full set
> (`run`, `build`, `test`, `lint`, `check`, `ship`, ...). The recipes wrap whatever this project's
> stack actually uses, so the interface is the same across projects.

## Project structure

```
.
â”œâ”€â”€ CLAUDE.md            # How Claude should work in this repo
â”œâ”€â”€ docs/
â”‚   â”œâ”€â”€ DESIGN.md        # Vision / architecture (read first)
â”‚   â”œâ”€â”€ CURRENT_TASK.md  # Where we left off (right now)
â”‚   â”œâ”€â”€ DECISIONS.md     # Narrative baseline + ADR index
â”‚   â”œâ”€â”€ tasks/           # File-based backlog (one .md per task; /task)
â”‚   â”œâ”€â”€ guides/          # Repeatable "how to add X" recipes
â”‚   â””â”€â”€ adr/             # Architecture decision records
â”œâ”€â”€ justfile            # The command interface
â”œâ”€â”€ .githooks/          # Version-bump + commit-msg hooks
â””â”€â”€ src/                # TODO â€” source
```

## Development

- See `CLAUDE.md` for conventions (vertical slices, Conventional Commits, verification).
- Enable git hooks once per clone: `git config core.hooksPath .githooks`
  (the bootstrap does this for you).
- **Unreal projects:** the bootstrap instead points `core.hooksPath` at the shared
  `E:\dev-toolbox\hooks` (Conventional Commits + conf-driven clang-format/version-bump + LFS
  pass-throughs) when `dev-toolbox` is present on this machine, falling back to this repo's own
  `.githooks` otherwise. If `dev-toolbox` lives somewhere other than `E:\dev-toolbox`, set the
  `UE_CENTRAL` environment variable to its path before running `setup.ps1`.

## License

TODO â€” proprietary by default. (For a published tool/plugin, this section names the license.)
