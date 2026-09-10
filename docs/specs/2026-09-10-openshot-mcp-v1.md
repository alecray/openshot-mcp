# Spec — openshot-mcp v1: file-level OpenShot project MCP with beat-grid placement

Date: 2026-09-10. Status: implemented v0.1.0 (Sol review + response in `docs/reviews/`). Owner: Alec. Author: Claude.

## Goal

A local MCP server (stdio, Python) that lets an LLM agent (Claude Code, Codex) build a game
trailer inside an **OpenShot 4.0** project file: import media, analyze a music wav into a beat
grid, place and trim clips on that grid, drop section markers, save. Alec then opens the project
in OpenShot and edits by hand. Reusable across every future trailer, not just Roomstack.

## Non-goals (v1)

- Driving the running OpenShot app (live edits). File-level only; OpenShot must be closed when
  the server writes (autosave every 3 min would clobber the file).
- Rendering/export. Alec exports from OpenShot. (v2 candidate: `export` via OpenShot's bundled
  `_openshot.pyd` Python 3.8.)
- Effects, transitions, titles, keyframe animation, audio mixing. Clips are placed with default
  transform (`scale: 1` best-fit) and default curves.
- Editorial judgment. The server exposes primitives and a beat grid; deciding *which* clip goes
  where stays with the agent/skill that calls it.
- Any OpenShot version other than 4.0.0 / libopenshot 1.0.0 (the installed one). Version is
  checked on open and refused otherwise.

## Source-verified current state

| Fact | Evidence |
|---|---|
| OpenShot 4.0.0 / libopenshot 1.0.0 installed at `E:\OpenShot Video Editor\`, frozen cx_Freeze Python 3.8 bundle, no HTTP/socket API, no plugin API | `E:\OpenShot Video Editor\lib\_openshot.pyd`, `classes/*.py`; `openshot-qt-cli.exe --help` crashes |
| No open-source OpenShot MCP exists | `gh search repos "openshot mcp"` → `[]` (2026-09-10); web search: only viaSocket's paid connector |
| `.osp` is plain JSON. Top-level keys: `id fps display_ratio pixel_ratio width height sample_rate channels channel_layout settings clips effects files duration scale tick_pixels playhead_position profile export_settings layers markers progress history version` | `E:\OpenShot-Video-Editor-Projects\roomstack-trailer.osp` |
| `files[]` entry keys (flat, no nesting): `acodec audio_bit_rate audio_stream_index audio_timebase channel_layout channels display_ratio duration duration_strategy file_size fps has_audio has_single_image has_video height id interlaced_frame media_type metadata path pixel_format pixel_ratio sample_rate top_field_first type vcodec video_bit_rate video_length video_stream_index video_timebase width` (+ optional `ui`, `image`) | same file |
| `clips[]` entry: scalars `anchor composite display duration effects end file_id gravity id layer mixing parentObjectId position reader_orientation_mode scale start title waveform waveform_mode`, a `reader` object with the same keys as a `files[]` entry, `wave_color` (4 curves), and 26 property curves (`alpha channel_filter channel_mapping corner_radius has_audio has_video location_x location_y margin origin_x origin_y perspective_c1..c4_x/y rotation scale_x scale_y shear_x shear_y time volume`) | same file |
| Curve shape: `{"Points":[{"co":{"X":1.0,"Y":<v>},"handle_left":{"X":0.5,"Y":1.0},"handle_right":{"X":0.5,"Y":0.0},"handle_type":0,"interpolation":0}]}` | same file |
| IDs are 10-char uppercase alphanumeric (`2BRLK63IRW`) | same file |
| Layers: `[{"id":"L1","number":1000000,"label":""}, … L5 5000000]` | same file |
| Project `duration` is 300 (timeline capacity), `scale` is zoom, `history` is `{undo:[],redo:[]}` shape | same file; Astra review 2026-09-10 (`E:\claude_scratch\roomstack-trailer\openshot\astra_answer.md`) |
| OpenShot autosaves every 3 min while open (`enable-auto-save: true`, `autosave-interval: 3`), writes recovery zips to `~/.openshot_qt/recovery/` | `~\.openshot_qt\openshot.settings` |
| Unsaved-changes marker: window title starts with `*` | `Get-Process openshot-qt` MainWindowTitle |
| librosa 1.0.0 on the trailer wav: tempo 89.1 (true 88), first tracked beat at 2.763 s (true grid starts at 0; section A is too sparse for onsets), bar-energy section detection lands within ±1 bar of 4 of 6 true section changes | `/tmp/beat_probe.py` run 2026-09-10 |
| ffprobe for the 20 capture clips: h264, 1920x1080, 60/1 fps, 240 frames (c14: 239), no audio, time_base 1/15360 | `E:\claude_scratch\roomstack-trailer\openshot\clip_probe.json` |

## Design

### Package layout

```
E:\openshot-mcp\
  pyproject.toml            # name openshot-mcp, deps: mcp>=2, librosa, soundfile, numpy
  src\openshot_mcp\
    __init__.py
    server.py               # MCP tool definitions only (thin)
    project.py              # Project: load/validate/save .osp, id gen, layers, markers
    media.py                # ffprobe → files[] entry + clip reader; clip factory with default curves
    grid.py                 # BeatGrid: bpm, offset, beats, bars, sections; snap; from wav or explicit
    lock.py                 # is_open_in_openshot(path) via process title / recent_projects + lock file
  tests\                    # pytest; fixtures: minimal .osp, 1-second synthetic mp4 + wav
  docs\specs\               # this file
```

Runs as `E:\openshot-mcp\.venv\Scripts\python.exe -m openshot_mcp` (stdio). Registered in a
project's `.mcp.json` as `"openshot": {"command": "E:/openshot-mcp/.venv/Scripts/python.exe", "args": ["-m","openshot_mcp"]}`.

### Server state

One open project at a time, held in memory after `open_project`. Every mutating tool edits the
in-memory model; nothing touches disk until `save_project`. `get_timeline` reads memory.

### Tools (v1)

| Tool | Args | Returns | Notes |
|---|---|---|---|
| `open_project` | `path` | summary: fps, size, layers, file count, clip count, markers, `open_in_openshot` bool | Refuses if version ≠ 4.0.0. Warns (does not refuse) if OpenShot has it open. |
| `new_project` | `path`, `profile="HD 720p 30 fps"` | same | Writes nothing until save. Built from a committed minimal template (`templates/empty_720p30.osp`, captured from OpenShot). |
| `import_media` | `paths: list[str]` | per file: id, media_type, duration, fps, w×h | ffprobe → `files[]` entry. Idempotent: same absolute path returns the existing id. |
| `analyze_music` | `file_id`, `bpm: float\|None`, `offset_s: float\|None`, `sections: list[float]\|None` | grid: bpm, offset, beat count, bar length, sections `[{start_s, label}]`, `confidence` | Auto-detects with librosa when args are None; explicit args override. Sets the project's active grid. Also adds a marker per section (`add_markers=True` default). |
| `set_grid` | same overrides | grid | Alias for `analyze_music` without audio analysis (for Ableton-known values). |
| `get_grid` | — | grid + helper: `beat_time(n)`, `bar_time(n)` values as arrays | Agents plan against this. |
| `add_clip` | `file_id`, `layer`, `position_s`, `start_s=0`, `end_s=None`, `snap="beat"\|"bar"\|"none"`, `title=None` | clip id, resolved position/start/end, frame numbers | `end_s=None` → to next grid line or file end. Snap quantizes `position_s` to the project fps frame nearest the grid line (Astra's `round(beat*fps*60/bpm)` rule, done in `Fraction`). Refuses overlap on the same layer unless `allow_overlap=True`. |
| `place_sequence` | `layer`, `items: [{file_id, start_s?, beats?}]`, `from_s=0`, `snap="beat"` | clip ids + table | Convenience: lays items back-to-back, each `beats` long (default 4), on the grid. This is the one-call path for "place 15 clips on the beat structure". |
| `update_clip` | `clip_id`, any of `position_s start_s end_s layer title` | clip | |
| `remove_clip` | `clip_id` | ok | |
| `add_marker` | `position_s`, `title`, `color="#e2ba21"` | marker | Uses OpenShot `markers[]` shape `{id, position, title, icon, vector}` (verify against a marker created in OpenShot before implementing; see traps). |
| `get_timeline` | `layer=None` | table of clips sorted by position: id, title, layer, position, start, end, duration, ends_at | Plus gaps/overlaps report. |
| `save_project` | `backup=True`, `force=False` | path, backup path | Refuses if OpenShot has the project open unless `force`. Atomic: write temp, rename. Backup = `<name>.<timestamp>.osp.bak` beside the file. Resets `history` to empty. |
| `validate_project` | — | list of problems | Unique ids, dangling `file_id`, clip `end ≤ file duration`, `start < end`, overlap per layer, layer numbers exist. Run automatically before save. |

### Beat grid rules

- `beat_len = 60/bpm`, `bar_len = 4*beat_len` (4/4 only in v1; `beats_per_bar` arg reserved).
- `beat_time(n) = offset + n*beat_len`. Frame quantization: `frame = round(t*fps)` using
  `fractions.Fraction` for exact arithmetic; `position = frame/fps`. Adjacent clips placed by
  `place_sequence` are frame-contiguous by construction (each end frame = next start frame).
- Auto-detect: `librosa.beat.beat_track` → bpm rounded to nearest 0.5; offset = phase of the first
  tracked beat modulo `beat_len` (so a late first beat still yields a grid anchored near 0).
  Sections: bar-averaged RMS + onset-density change points, top-N (N=6 default), snapped to bar
  lines. `confidence` is low/medium/high from tempo stability (`librosa.feature.tempo` spread).
  Always report what was detected so the agent can override with Ableton's real numbers.

### Media rules

- `files[]`/`reader`: `fps` and `video_timebase` come from the *source stream* (`r_frame_rate`,
  `time_base`), not the project. `video_length` = stream `nb_frames` (fallback
  `round(duration*fps)`). `duration_strategy: "VideoPreferred"`. Video-only mp4: `has_audio false`,
  `acodec ""`, `channels 0`, `sample_rate 0`, `audio_stream_index -1`. Audio-only wav mirrors the
  existing project's wav entry.
- Clip defaults: copied verbatim from the captured template (all 26 curves at their default `Y`,
  `wave_color`, `gravity 4`, `scale 1`, `waveform false`), `has_audio`/`has_video` curves at -1.
  `title` = basename. `duration = end - start`. Omit `ui` and `image` (OpenShot regenerates
  thumbnails; waveform cache is optional).
- `media_type` from streams: video stream present → `video`; audio only → `audio`; single image → `image`.

### Skill layer (out of this repo, but the consumer)

The existing `game-trailer-editor` skill (`~\.claude\skills\game-trailer-editor\`)
gets a new stage: after the clip inventory and beat analysis, call `place_sequence` instead of
writing an ffmpeg EDL, then hand the `.osp` to Alec. That rewrite is a follow-up task, not v1.

## Red-first gate (executable checks)

`E:\openshot-mcp\.venv\Scripts\python.exe -m pytest tests -q` must fail before implementation and
pass after. Tests:

1. `test_load_save_roundtrip`: load the committed fixture `.osp`, save to temp, reload; JSON equal
   except `history`.
2. `test_import_video_file_entry`: ffprobe a generated 1 s 60 fps mp4 (made by ffmpeg in a fixture);
   entry has `fps 60/1`, `video_timebase 1/15360`, `video_length 60`, `has_audio false`.
3. `test_add_clip_snaps_to_beat`: grid bpm 88 offset 0 fps 30; `add_clip(position_s=4.0, snap="beat")`
   → position `4.1` (frame 123); `end` defaults to next beat frame.
4. `test_place_sequence_contiguous`: 5 items × 4 beats → 5 clips, each `position + duration ==`
   next `position` exactly, all frames integers.
5. `test_validate_catches_overlap_and_dangling`.
6. `test_save_refuses_when_open` (lock check mocked true; `force=True` bypasses).
7. `test_analyze_music_known_click`: synthetic 88 BPM click track wav (generated in fixture) →
   detected bpm within ±1, offset within ±20 ms.

Manual gate (not automatable here): after `save_project` on the real Roomstack project, open it in
OpenShot 4.0; every clip appears on L3 with the right thumbnail and plays; section markers show;
save from OpenShot and reopen keeps the arrangement. Expected: no "missing file" dialogs, no crash.

## Execution order

1. Scaffold `pyproject.toml`, package skeleton, test fixtures (ffmpeg-generated mp4 + click wav,
   template `.osp` captured from the real project with the audio clip stripped). Tests red.
2. `project.py` + `media.py` (load/save/validate/import/add/update/remove). Tests 1, 2, 5, 6 green.
3. `grid.py` (explicit grid, snap, place_sequence). Tests 3, 4 green.
4. `analyze_music` (librosa). Test 7 green.
5. `server.py` MCP wiring; register in roomstack `.mcp.json`; smoke-call each tool from Claude Code.
6. Apply Astra's 15-shot plan to the real project through the MCP (OpenShot closed, backup taken).
   Manual gate in OpenShot. Commit; tag `v0.1.0`.

## Definition of Done

- [x] All 10 tests pass via the command above (output pasted in the PR/commit).
- [x] Roomstack trailer project has the 15 clips + 7 section markers placed through the MCP (2026-09-10 12:38, backup `roomstack-trailer.20260910-123821.osp.bak`); opens
      in OpenShot without dialogs; Alec confirms visually.
- [x] `README.md` documents install (`uv venv` + `uv pip install -e .`), `.mcp.json` snippet, tool
      list, and the "close OpenShot before save" rule.
- [x] `docs/DESIGN.md` and `docs/CURRENT_TASK.md` updated; ADR 0001 records "file-level, not live".
- [ ] Repo pushed to `git@github.com:alecray/openshot-mcp.git` (create with `gh repo create --private`).

## Known traps

- **Autosave clobber.** OpenShot writes the project every 3 min while open. `save_project` must
  check and refuse. Detection: window title contains the project stem (PowerShell
  `Get-Process openshot-qt`), or `recent_projects[0] == path` plus a live `openshot-qt` process.
- **`markers[]` shape unverified.** No marker exists in the real project yet. Before step 2, create
  one in OpenShot on a scratch project, save, and copy the exact shape into the template.
- **Windows paths.** OpenShot stores forward-slash absolute paths (`Z:/Ableton Exports/…`). Normalize.
- **Frame rounding drift.** Never accumulate floats; derive every position from an integer frame.
- **c14 is 239 frames.** `end_s` must clamp to file duration, and validation must catch overrun.
- **librosa on sparse intros.** Beat phase can lock late (2.76 s on Roomstack). Offset must be
  reduced modulo beat length; always surface `confidence` and the raw first-beat time.
- **`ui.audio_data` on the wav clip.** Leave the existing wav clip untouched byte-for-byte; only
  append new entries.
- **Disk.** C: has 5 GB free; venv and `UV_CACHE_DIR` live on E:.
