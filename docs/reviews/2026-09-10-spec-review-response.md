# Response to Sol's spec review (2026-09-10)

Review: `2026-09-10-spec-review-sol.md` (GPT-5.6, high). Each finding, what was done, where.

| Finding | Action | Where |
|---|---|---|
| CRITICAL path model (OpenShot stores same-drive paths relative, `@assets`, cross-drive absolute) | Verified in the installed `classes/json_data.py` (`path_regex`, `replace_string_to_relative/absolute`). Implemented the same codec: absolute in memory, relativized on save for keys `image path resource protobuf_data_path lut_path`. Test: `test_unknown_keys_and_relative_paths_survive_roundtrip`. | `project.py` `to_absolute` / `to_relative` / `_walk_paths` |
| CRITICAL stale-state overwrite | SHA-256 of the file recorded at `open_project`; `save_project` to the same path refuses if the on-disk hash differs, and `force` does NOT bypass that. `force` only bypasses the OpenShot-window heuristic. Test: `test_save_refuses_if_changed_on_disk`. | `project.py` `Project.load` / `save` |
| MAJOR atomic save contract | write temp in the target dir → flush → `fsync` → parse the temp back → `os.replace` (which does replace on Windows) → temp cleaned on failure. Backup copied before any of that. | `project.py` `save` |
| MAJOR media duration must be frame-rounded (c14: 239/60) | `duration = video_length / fps` for every file (audio-only uses 30 fps, matching the existing wav entry `1145/30`). Test: `test_duration_is_frame_rounded`. | `media.py` |
| MAJOR marker schema | Verified: OpenShot creates `{position, icon:"blue.png", vector:"blue"}` + `id`. `title` kept as agent metadata; docstring and README state it is not displayed. `color` validated against a small palette; only `blue` is verified to ship an icon. | `project.py` `add_marker`, `server.py` |
| MAJOR discovery tools | `list_media` tool added; `open_project` summary now lists files with ids; `get_timeline` rows include `file_id`; `save_project(path)` is save-as. | `server.py`, `project.py` |
| MAJOR grid API ambiguity | `set_grid(bpm, offset_s, sections, beats_per_bar, total_s)` is media-independent; `analyze_music(apply=False)` returns a proposal without replacing the active grid. | `server.py` |
| MAJOR exact snapping | Inputs converted with `Fraction(str(v))`; every boundary is `round(beat_time(n) * fps)` from the grid, never accumulated (`beat_time_frac` handles fractional beat counts); `beats` must be positive. Python `round` = banker's rounding on exact .5 ties (documented here; ties are astronomically rare with 88 BPM / 30 fps). | `grid.py`, `project.py` `place_sequence` |
| MAJOR section detection over-scoped | Kept, but demoted: README and tool docstring call it a rough guess; explicit `sections` override is the recommended path. Confidence grading kept as an advisory string. Not removed because it costs nothing and gives the agent a starting point. | `grid.py`, README |
| MAJOR tests prove serializer against itself | Added the sentinel-unknown-key mutation test. The OpenShot load→save→reopen gate stays manual (needs the GUI); it is the DoD's human step on the Roomstack project. | `tests/test_project.py`, spec DoD |
| MINOR validation completeness | `reader.id == file_id`, finite non-negative times, duration consistency, effects ids in uniqueness check. `allow_overlap` is a declared arg. | `project.py` `validate` |
| MINOR brittle timebase fixture | Test asserts against the fixture's own ffprobe `time_base`. | `tests/test_project.py` |

Not done (deliberately): removing `force` entirely. Kept for the case where the window-title heuristic misfires (e.g. another OpenShot project with a similar name); the hash check still protects against real clobbering.
