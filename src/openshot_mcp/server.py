"""MCP tool surface. Thin: every tool maps to one Project/BeatGrid call."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from mcp.server.mcpserver import MCPServer

from .grid import BeatGrid, Section, analyze_wav
from .project import Project

mcp = MCPServer("openshot", version=__import__("openshot_mcp").__version__, instructions=(
    "File-level editor for OpenShot 4.0 .osp projects. Workflow: open_project -> import_media -> "
    "analyze_music (or set_grid) -> place_sequence/add_clip -> get_timeline -> save_project. "
    "OpenShot must NOT have the project open when you save (its autosave overwrites the file)."
))

_state: dict[str, Optional[Project]] = {"project": None}


def _p() -> Project:
    p = _state["project"]
    if p is None:
        raise RuntimeError("no project open; call open_project or new_project first")
    return p


@mcp.tool()
def open_project(path: str) -> dict:
    """Load an existing OpenShot 4.0 .osp project into memory. Returns a summary."""
    _state["project"] = Project.load(path)
    return _p().summary()


@mcp.tool()
def new_project(path: str) -> dict:
    """Create a new HD 720p 30 fps project in memory at ``path`` (written on save_project)."""
    _state["project"] = Project.new(path)
    return _p().summary()


@mcp.tool()
def import_media(paths: list[str]) -> list[dict]:
    """ffprobe each file and add it to the project's files list. Idempotent per absolute path."""
    out = []
    for p in paths:
        f = _p().import_media(p)
        out.append({k: f[k] for k in ("id", "path", "media_type", "duration", "fps", "width", "height", "has_audio")})
    return out


@mcp.tool()
def list_media() -> list[dict]:
    """List imported files with their ids (needed for analyze_music / add_clip / place_sequence)."""
    return _p().list_media()


@mcp.tool()
def analyze_music(file_id: str, bpm: Optional[float] = None, offset_s: Optional[float] = None,
                  sections: Optional[list[float]] = None, n_sections: int = 6,
                  add_markers: bool = True, apply: bool = True) -> dict:
    """Detect tempo/offset of an imported audio file with librosa (onset-grid search, ~0.1 BPM) plus a
    ROUGH section-change guess, and (apply=True) set it as the active beat grid. Explicit
    bpm/offset_s/sections override detection. Adds one marker per section by default.
    Markers show as icons in OpenShot; their titles are not displayed."""
    p = _p()
    f = p.file(file_id)
    g = analyze_wav(f["path"], p.fps, bpm=bpm, offset_s=offset_s, sections=sections, n_sections=n_sections)
    if not apply:
        return g.as_dict(total_s=float(f["duration"]))
    p.grid = g
    if add_markers:
        for s in g.sections:
            p.add_marker(s.start_s, title=f"Section {s.label}")
    return g.as_dict(total_s=float(f["duration"]))


@mcp.tool()
def set_grid(bpm: float, offset_s: float = 0.0, sections: Optional[list[float]] = None,
             beats_per_bar: int = 4, add_markers: bool = True, total_s: Optional[float] = None) -> dict:
    """Set the beat grid explicitly (e.g. from the DAW's known BPM) without analyzing audio."""
    p = _p()
    starts = sorted(set([0.0] + [float(s) for s in (sections or [])]))
    g = BeatGrid(bpm=bpm, offset_s=offset_s, fps=p.fps, beats_per_bar=beats_per_bar,
                 sections=[Section(s, "ABCDEFGHIJ"[i] if i < 10 else str(i)) for i, s in enumerate(starts)])
    p.grid = g
    if add_markers:
        for s in g.sections:
            p.add_marker(s.start_s, title=f"Section {s.label}")
    return g.as_dict(total_s=total_s)


@mcp.tool()
def get_grid(total_s: Optional[float] = None) -> dict:
    """Return the active beat grid, with beat times up to total_s if given."""
    p = _p()
    if p.grid is None:
        raise RuntimeError("no grid set")
    return p.grid.as_dict(total_s=total_s)


@mcp.tool()
def add_clip(file_id: str, layer: int, position_s: float, start_s: float = 0.0,
             end_s: Optional[float] = None, snap: str = "beat", title: Optional[str] = None,
             allow_overlap: bool = False) -> dict:
    """Place one clip. snap = beat | bar | none quantizes position_s to the grid (frame-exact).
    end_s=None ends the clip at the next grid line (or file end). Refuses same-layer overlap."""
    c = _p().add_clip(file_id, layer, position_s, start_s, end_s, snap, title, allow_overlap)
    return _row(c)


@mcp.tool()
def place_sequence(layer: int, items: list[dict], from_s: float = 0.0, default_beats: float = 4,
                   allow_overlap: bool = False) -> list[dict]:
    """Lay clips back-to-back on the beat grid. items: [{file_id, beats?, start_s?, title?}].
    Each item lasts `beats` beats (default default_beats); cuts are frame-contiguous."""
    return [_row(c) for c in _p().place_sequence(layer, items, from_s, "beat", default_beats, allow_overlap)]


@mcp.tool()
def update_clip(clip_id: str, position_s: Optional[float] = None, start_s: Optional[float] = None,
                end_s: Optional[float] = None, layer: Optional[int] = None, title: Optional[str] = None) -> dict:
    """Change a clip's timeline position, in/out points, layer, or title."""
    return _row(_p().update_clip(clip_id, position_s=position_s, start_s=start_s, end_s=end_s, layer=layer, title=title))


@mcp.tool()
def remove_clip(clip_id: str) -> dict:
    """Delete a clip from the timeline (the file stays imported)."""
    _p().remove_clip(clip_id)
    return {"removed": clip_id}


@mcp.tool()
def add_marker(position_s: float, title: str = "", color: str = "blue") -> dict:
    """Add a timeline marker (OpenShot shows an icon; the title is stored but not displayed). Use color=blue."""
    return _p().add_marker(position_s, title, color)


@mcp.tool()
def clear_markers() -> dict:
    """Remove all timeline markers."""
    return {"removed": _p().clear_markers()}


@mcp.tool()
def get_timeline(layer: Optional[int] = None) -> dict:
    """List clips (sorted by layer, position) plus gaps/overlaps per layer, markers, and end time."""
    return _p().timeline(layer)


@mcp.tool()
def validate_project() -> dict:
    """Check ids, references, bounds, layers, and overlaps. Empty list = valid."""
    return {"problems": _p().validate()}


@mcp.tool()
def save_project(path: Optional[str] = None, backup: bool = True, force: bool = False) -> dict:
    """Validate and atomically write the .osp (timestamped .bak beside it). Refuses while OpenShot has it
    open (force=True bypasses that heuristic only) and refuses if the file changed on disk since open_project."""
    return _p().save(path, backup=backup, force=force)


def _row(c: dict) -> dict:
    return {"id": c["id"], "title": c["title"], "layer": c["layer"], "position": c["position"],
            "start": c["start"], "end": c["end"], "duration": c["duration"],
            "ends_at": c["position"] + c["duration"], "file_id": c["file_id"]}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
