# ADR-0000: Record architecture decisions using MADR

**Date:** 2026
**Status:** Accepted

## Context

Solo, AI-assisted development across many stacks. Months later (or in a fresh Claude session)
the *why* behind a deliberate tradeoff is easy to lose â€” and an agent may "fix" an intentional
choice. `docs/DESIGN.md` captures the overall vision; it doesn't capture each fork-in-the-road
decision well.

## Decision

Record each consequential architectural decision as a short Markdown file in `docs/adr/`, using
the lightweight **MADR** shape: **Context / Decision / Consequences**. Files are numbered and
kebab-cased: `NNNN-short-title.md`. Status is one of Proposed / Accepted / Superseded. Create new
ones with `/adr`.

Write an ADR when you consciously reject a reasonable alternative (storage choice, networking
model, library, pattern). Don't write one for routine implementation details.

## Consequences

- âœ… Future-you and the agent can see *why* the code looks the way it does.
- âœ… Decisions are versioned alongside the code, no external tool.
- âž– A little discipline required to write them at the moment of decision.
