# justfile â€” the one command interface for this project.
# Install just: https://github.com/casey/just  (winget install Casey.Just)
# Run `just --list` to see everything. CI, /verify, and /ship all call these recipes,
# so the same commands work regardless of stack â€” only this file knows the real command.
#
# CONTRACT recipes (implement for every stack):  run, build
# ADVISORY recipes (optional for engine stacks):  test, lint
#   An unimplemented advisory recipe prints "SKIP: ..." and is treated as a skip, not a
#   failure, by `just check`, CI, and the slash commands.

# Show the command list by default.
default:
    @just --list

# --- CONTRACT: implement these for every stack ---

# Launch/run the project (app, game, dev server...).
run:
    python -m openshot_mcp

# Produce a build/package artifact.
build:
    python -m pip install -e ".[dev]"

# --- ADVISORY: optional for engine stacks without a clean CLI ---

# Run automated tests. Leave as the SKIP stub if the stack has no CLI tests (e.g. some Unreal/Godot projects).
test:
    python -m pytest -q

# Run the linter/formatter check. Leave as the SKIP stub if N/A.
lint:
    python -m ruff check src tests

# --- Aggregate / utility (stack-agnostic) ---

# Run lint then test. SKIP stubs pass; real failures fail.
check: lint test
    @echo "check complete"

# Scan for committed secrets (optional: needs gitleaks; skips gracefully if absent).
scan-secrets:
    @command -v gitleaks >/dev/null 2>&1 && gitleaks detect --no-banner --source=. || echo "SKIP: gitleaks not installed"

# Regenerate CHANGELOG.md from Conventional Commits (optional: needs git-cliff).
changelog:
    @command -v git-cliff >/dev/null 2>&1 && git-cliff --output CHANGELOG.md || echo "SKIP: git-cliff not installed (edit CHANGELOG.md by hand)"

# Run checks, refresh changelog, and open a PR.
ship: check changelog
    gh pr create --fill
