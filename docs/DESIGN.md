# openshot-mcp — Design

## 1. Product philosophy
A file-level MCP server that lets an LLM agent build the rough cut of a game trailer inside an
OpenShot 4.0 project: import clips and a music wav, derive a beat grid, place clips on it, save.
Alec finishes the edit by hand in OpenShot. Goal: any future trailer starts from "drop in a wav
and the clips" instead of a hand-built timeline. Spec: `docs/specs/2026-09-10-openshot-mcp-v1.md`.

## 2. Core principles
1. **Never lose a human edit.** Refuse to save if OpenShot has the project open or the file changed
   on disk since it was opened. Backup before every write. Atomic replace.
2. **Frame-exact, never accumulated.** Every timeline position is derived from an integer project
   frame on the beat grid via exact fractions.
3. **Primitives, not opinions.** The server exposes grid + clip operations; editorial choices stay
   in the calling skill/agent.
4. **Mirror OpenShot, don't reinvent it.** Path codec, marker shape, file/clip keys copied from the
   installed 4.0 sources and a real project, not guessed.
5. **Cheap to verify.** `pytest` in 3 s; the only manual gate is opening the result in OpenShot.

## 3. Tech stack & rationale
- Python 3.12, `mcp` 2.x (`MCPServer`, stdio), `librosa` for tempo/onset, `ffprobe` for media metadata.
- Why file-level, not live: OpenShot has no plugin/API surface; patching its frozen bundle would break
  on every update. See ADR-0001.

## 4. Architecture
`server.py` (tools) → `project.py` (in-memory `.osp` model, load/save/validate, path codec, lock+hash
guards) → `media.py` (ffprobe → `files[]` entry, clip factory from `templates/clip_defaults.json`) and
`grid.py` (`BeatGrid`: bpm/offset/sections, snapping; `analyze_wav`). `lock.py` detects an open
OpenShot window.

## 5. Data / persistence model
The OpenShot `.osp` JSON itself is the store. In memory all paths are absolute; on save, same-drive
paths are relativized and `<stem>_assets` paths become `@assets/...`, matching OpenShot. `history`
is reset on save. No other state persists.

## 6. Milestones
| Tag | Goal | Done when |
|-----|------|-----------|
| `v0.1.0` | 15 tools, beat-grid placement, Roomstack trailer placed through it | tests green + project opens in OpenShot (2026-09-10) |
| `v0.2` | `game-trailer-editor` skill re-pointed at this server; effects/transitions; export via bundled libopenshot | skill produces a rough cut end-to-end on a second trailer |

## 7. Explicit non-goals
- Driving the running OpenShot app.
- Rendering/export (v1).
- Editorial decisions (which clip where).
- OpenShot versions other than 4.0.0 without a template refresh.

## 8. Open questions
- Marker icons other than `blue.png`: which colors actually ship in the 4.0 timeline webview?
- Section detection: keep the rough guess or replace with a DAW sidecar export?
