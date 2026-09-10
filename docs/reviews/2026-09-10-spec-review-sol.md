**CRITICAL**

- **L169 — incorrect path model.** OpenShot stores same-drive media relatively and supports `@assets`; it resolves paths on load and re-relativizes them on save. Treating paths as forward-slash absolutes will misresolve existing projects and break media after Save As. Implement an OpenShot-compatible path codec for `path`, `image`, `resource`, `protobuf_data_path`, and `lut_path`, relative to source/destination `.osp` and companion assets directories. Test relative, cross-drive, and `@assets` cases. [OpenShot path handling](https://github.com/OpenShot/openshot-qt/blob/v4.0.0/src/classes/json_data.py#L228-L389)

- **L64–67, 73, 85, 162–166 — stale state can overwrite human edits.** Process-title/recent-project detection is heuristic, and the file can change after `open_project`. Record the source SHA-256 when opened; immediately before saving, refuse if the disk hash differs. For v1, refuse while *any* OpenShot process is live and remove `force`; an MCP lock only coordinates MCP instances, not OpenShot.

**MAJOR**

- **L85 — “temp, rename” is not a sufficient atomic-save contract.** On Windows, ordinary rename does not replace an existing destination. Specify: validate → copy original backup bytes → create temp in destination directory → write/flush/`fsync` → parse temp → `os.replace` → clean temp on failure. Add injected-failure tests proving the original remains intact.

- **L102–106, 171 — media duration is underdefined and wrong for c14 if container duration is used.** c14 reports 3.984 s but 239 frames at 60 fps; libopenshot rounds selected stream duration to frames, then stores `239/60 = 3.983333…`. Derive video duration as `video_length / fps` after rounded frame count, and validate trims against that value. [FFmpegReader duration logic](https://github.com/OpenShot/libopenshot/blob/v1.0.0/src/FFmpegReader.cpp#L796-L858)

- **L83 — marker schema/API is factually wrong.** OpenShot 4.0 creates `{id, position, icon:"blue.png", vector:"blue"}`. It has no displayed `title`, and a hex `color` is ignored. Make `title` caller metadata only—or omit it—and expose a validated OpenShot vector/icon palette. State explicitly that section labels will not appear in OpenShot. [Marker creation](https://github.com/OpenShot/openshot-qt/blob/v4.0.0/src/windows/main_window.py#L2115-L2125)

- **L73–85 — the workflow lacks discovery and safe derivation tools.** `open_project` returns counts, so an agent cannot obtain existing `file_id`s for `analyze_music` or sequencing. Add `list_media` and include `file_id` in `get_timeline`. Add `save_project(path=None)`/`save_as_project`; otherwise building from the existing music project requires overwriting it.

- **L76–78 — grid APIs are ambiguous.** “Same overrides” makes `set_grid` appear to require `file_id`, and beat-array extent is undefined. Define `set_grid(bpm, offset_s=0, beats_per_bar=4, end_s|beat_count)` independently of media; make `analyze_music` return a proposed grid rather than silently replacing the active one unless requested.

- **L90–95 — exact snapping is not actually specified.** Convert decimal inputs with `Fraction(str(value))`, define half-frame tie behavior, and calculate every absolute boundary as `F(n)=round((offset+n*60/bpm)*fps)`. `place_sequence` must use `F(n+k)-F(n)`, with positive integer `beats`, rather than rounded accumulated durations.

- **L94–98, 147 — automatic section detection and qualitative confidence are over-scoped.** They have no algorithmic thresholds or representative acceptance data. Keep deterministic explicit grids plus BPM/beat estimation in v1; defer change-point sections and confidence grading.

- **L124–139 — tests prove the serializer against itself, not OpenShot compatibility or preservation.** Add a mutation test with sentinel unknown keys asserting only intended nodes/history change, plus an OpenShot 4.0 load→save→reopen gate that reparses the result and verifies file references, clips, marker positions, and untouched music data. OpenShot merges missing defaults, so JSON self-roundtrip alone cannot validate editor behavior. [Loader behavior](https://github.com/OpenShot/openshot-qt/blob/v4.0.0/src/classes/project_data.py#L2878-L3003)

**MINOR**

- **L79, 86 — undeclared and incomplete validation.** `allow_overlap` is referenced but absent from arguments. Validate all-ID uniqueness, `reader.id == file_id`, finite/nonnegative times, `duration == end-start`, locked layers, paths, and project/layer existence.

- **L126–127 — brittle fixture assertion.** MP4 timescale is muxer-dependent. Either generate with `-video_track_timescale 15360` or assert that stored timebase equals the fixture’s own ffprobe result.