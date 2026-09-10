# ADR-0001: Edit the .osp file, not the running OpenShot app

**Date:** 2026-09-10
**Status:** Accepted

## Context
OpenShot 4.0 ships as a frozen cx_Freeze bundle with no plugin API, no HTTP/socket control surface,
and a CLI that crashes on `--help`. Live edits would require patching the bundle's Python and
re-patching on every release. The project file is plain JSON that OpenShot fully reloads.

## Decision
The server edits the `.osp` JSON in memory and writes it atomically while OpenShot is closed. It
refuses to write if OpenShot has the project open (window-title heuristic) or if the file's hash
changed since it was opened.

## Consequences
- ✅ Survives OpenShot updates; testable with pytest; no GUI automation.
- ➖ Alec closes and reopens the project to see agent edits.
- ➖ Anything OpenShot computes lazily (thumbnails, waveforms) is regenerated on open.
