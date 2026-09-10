---
description: Create a new Architecture Decision Record (MADR format)
argument-hint: "[decision title]"
allowed-tools: Read, Write, Bash, Glob
---

## Context
- Existing ADRs: !`ls docs/adr/ 2>/dev/null || echo "none yet"`

## Task
Create a new ADR for: **$ARGUMENTS**

1. Find the next number from `docs/adr/` (zero-padded, e.g. `0002`).
2. Create `docs/adr/NNNN-<kebab-case-title>.md` using the MADR shape:
   ```
   # ADR-NNNN: <Title>

   **Date:** <today>
   **Status:** Proposed

   ## Context
   ## Decision
   ## Consequences
   ```
3. Fill in what you know from the current conversation; leave clear TODOs for the rest.
4. Report the path and ask the user to review before marking it Accepted.
