"""In-memory model of an OpenShot 4.0 ``.osp`` project with file-level load/save.

Path model mirrors OpenShot's own ``json_data.py`` codec: on disk, media paths on the same drive
as the project are stored relative to the project folder (forward slashes), paths under the
project's ``<stem>_assets`` folder are stored as ``@assets/...``, and cross-drive paths stay
absolute. In memory every path is absolute so idempotent import and ffprobe work.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import string
import time
from fractions import Fraction
from pathlib import Path

from . import lock
from .grid import BeatGrid
from .media import TEMPLATES, clip_from_file, file_entry, norm_path

SUPPORTED_VERSION = "4.0.0"
ID_CHARS = string.ascii_uppercase + string.digits
PATH_KEYS = ("image", "path", "resource", "protobuf_data_path", "lut_path")
MARKER_COLORS = ("blue", "red", "green", "yellow", "purple", "orange", "white")


def gen_id(existing: set[str]) -> str:
    while True:
        i = "".join(random.choice(ID_CHARS) for _ in range(10))
        if i not in existing:
            return i


def _walk_paths(node, fn):
    """Apply ``fn(value) -> value`` to every string under a PATH_KEYS key, recursively."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k in PATH_KEYS and isinstance(v, str):
                node[k] = fn(v)
            else:
                _walk_paths(v, fn)
    elif isinstance(node, list):
        for v in node:
            _walk_paths(v, fn)


def assets_dir(project_path: Path) -> Path:
    return project_path.with_name(project_path.stem + "_assets")


def to_absolute(path: str, project_path: Path) -> str:
    if path == "" or path.startswith(("@transitions", "@colors", "@emojis")):
        return path
    if path.startswith("@assets"):
        return norm_path(str(assets_dir(project_path)) + path[len("@assets"):])
    if os.path.isabs(path) or re.match(r"^[A-Za-z]:", path):
        return path.replace("\\", "/")
    return norm_path(project_path.parent / path)


def to_relative(path: str, project_path: Path) -> str:
    if path == "" or path.startswith("@"):
        return path
    ap = Path(path)
    if not ap.is_absolute():
        return path
    assets = assets_dir(project_path)
    try:
        return "@assets/" + ap.relative_to(assets).as_posix()
    except ValueError:
        pass
    if os.path.splitdrive(str(ap))[0].lower() != os.path.splitdrive(str(project_path.resolve()))[0].lower():
        return str(ap).replace("\\", "/")
    return os.path.relpath(ap, project_path.parent).replace("\\", "/")


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


class Project:
    def __init__(self, data: dict, path: Path | None, source_hash: str | None = None):
        self.data = data
        self.path = path
        self.source_hash = source_hash
        self.grid: BeatGrid | None = None
        for k in ("files", "clips", "markers", "layers", "effects"):
            self.data.setdefault(k, [])
        if path is not None:
            _walk_paths(self.data, lambda s: to_absolute(s, path))

    # ---- lifecycle ---------------------------------------------------------
    @classmethod
    def load(cls, path: str | Path) -> "Project":
        p = Path(path).resolve()
        data = json.loads(p.read_text(encoding="utf-8"))
        ver = (data.get("version") or {}).get("openshot-qt")
        if ver != SUPPORTED_VERSION:
            raise ValueError(f"Unsupported openshot-qt project version {ver!r}; this server supports {SUPPORTED_VERSION}")
        return cls(data, p, _sha256(p))

    @classmethod
    def new(cls, path: str | Path, template: str = "empty_720p30.osp") -> "Project":
        data = json.loads((TEMPLATES / template).read_text(encoding="utf-8"))
        return cls(data, Path(path).resolve())

    def save(self, path: str | Path | None = None, backup: bool = True, force: bool = False,
             check_lock: bool = True) -> dict:
        target = Path(path).resolve() if path else self.path
        if target is None:
            raise ValueError("no path to save to")
        same_file = self.path is not None and target == self.path
        if check_lock and not force and lock.is_open_in_openshot(target):
            raise RuntimeError(
                f"OpenShot has {target.name} open; its autosave would overwrite this write. "
                "Close the project in OpenShot (or pass force=True if you are sure it is not open)."
            )
        if same_file and self.source_hash and target.exists() and _sha256(target) != self.source_hash:
            raise RuntimeError(
                f"{target.name} changed on disk since open_project (someone saved it). "
                "Refusing to overwrite; re-open the project and redo the edits."
            )
        problems = self.validate()
        if problems:
            raise ValueError("project invalid, refusing to save: " + "; ".join(problems))
        backup_path = None
        if backup and target.exists():
            backup_path = target.with_name(f"{target.stem}.{time.strftime('%Y%m%d-%H%M%S')}.osp.bak")
            backup_path.write_bytes(target.read_bytes())
        out = json.loads(json.dumps(self.data))  # deep copy
        out["history"] = {"undo": [], "redo": []}
        _walk_paths(out, lambda s: to_relative(s, target))
        text = json.dumps(out, indent=1)
        tmp = target.with_name(target.name + ".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                fh.write(text)
                fh.flush()
                os.fsync(fh.fileno())
            json.loads(tmp.read_text(encoding="utf-8"))  # parse back before replacing
            os.replace(tmp, target)
        finally:
            if tmp.exists():
                tmp.unlink()
        self.path = target
        self.source_hash = _sha256(target)
        return {"path": str(target), "backup": str(backup_path) if backup_path else None}

    # ---- accessors ---------------------------------------------------------
    @property
    def fps(self) -> dict:
        return self.data["fps"]

    @property
    def fps_frac(self) -> Fraction:
        return Fraction(int(self.fps["num"]), int(self.fps["den"]))

    def _ids(self) -> set[str]:
        return {x["id"] for k in ("files", "clips", "markers", "effects") for x in self.data.get(k, [])}

    def file(self, file_id: str) -> dict:
        for f in self.data["files"]:
            if f["id"] == file_id:
                return f
        raise KeyError(f"no file {file_id}")

    def clip(self, clip_id: str) -> dict:
        for c in self.data["clips"]:
            if c["id"] == clip_id:
                return c
        raise KeyError(f"no clip {clip_id}")

    def summary(self) -> dict:
        return {
            "path": str(self.path) if self.path else None,
            "fps": self.fps,
            "width": self.data.get("width"),
            "height": self.data.get("height"),
            "profile": self.data.get("profile"),
            "layers": [{"id": l["id"], "number": l["number"], "label": l.get("label", "")} for l in self.data["layers"]],
            "files": self.list_media(),
            "clips": len(self.data["clips"]),
            "markers": len(self.data["markers"]),
            "grid": self.grid.as_dict() if self.grid else None,
            "open_in_openshot": lock.is_open_in_openshot(self.path) if self.path else False,
        }

    def list_media(self) -> list[dict]:
        return [{k: f.get(k) for k in ("id", "path", "media_type", "duration", "fps", "width", "height", "has_audio")}
                for f in self.data["files"]]

    # ---- media -------------------------------------------------------------
    def import_media(self, path: str | Path) -> dict:
        np_ = norm_path(path)
        for f in self.data["files"]:
            if f["path"].lower() == np_.lower():
                return f
        entry = file_entry(path, gen_id(self._ids()))
        self.data["files"].append(entry)
        return entry

    # ---- clips -------------------------------------------------------------
    def _layer_ok(self, layer: int) -> None:
        if not any(int(l["number"]) == int(layer) for l in self.data["layers"]):
            raise ValueError(f"layer {layer} does not exist; layers: {[l['number'] for l in self.data['layers']]}")

    def _overlaps(self, layer: int, pos: float, dur: float, ignore: str | None = None) -> list[str]:
        out = []
        for c in self.data["clips"]:
            if c["id"] == ignore or int(c["layer"]) != int(layer):
                continue
            a0, a1 = c["position"], c["position"] + c["duration"]
            if pos < a1 - 1e-9 and pos + dur > a0 + 1e-9:
                out.append(c["id"])
        return out

    def _frame(self, t) -> int:
        return int(round(Fraction(str(t)) * self.fps_frac))

    def _s(self, frame: int) -> float:
        return float(Fraction(frame) / self.fps_frac)

    def add_clip(self, file_id: str, layer: int, position_s: float, start_s: float = 0.0,
                 end_s: float | None = None, snap: str = "beat", title: str | None = None,
                 allow_overlap: bool = False) -> dict:
        self._layer_ok(layer)
        f = self.file(file_id)
        if snap not in ("beat", "bar", "none"):
            raise ValueError("snap must be beat | bar | none")
        if snap != "none" and self.grid is None:
            raise ValueError("no beat grid set; call analyze_music/set_grid or use snap='none'")
        if self.grid is not None:
            pos_frame, pos = self.grid.snap(position_s, snap)
        else:
            pos_frame = self._frame(position_s)
            pos = self._s(pos_frame)
        file_dur = float(f["duration"])
        start = self._s(self._frame(start_s))
        if end_s is None:
            if self.grid is not None and snap != "none":
                end = start + (self.grid.next_line_after(pos, snap) - pos)
            else:
                end = file_dur
        else:
            end = self._s(self._frame(end_s))
        end = min(end, file_dur)
        if end <= start:
            raise ValueError(f"empty clip: start {start} >= end {end} (file duration {file_dur})")
        dur = end - start
        hits = self._overlaps(layer, pos, dur)
        if hits and not allow_overlap:
            raise ValueError(f"overlaps clip(s) {hits} on layer {layer} at {pos:.3f}s; pass allow_overlap=True to force")
        clip = clip_from_file(f, gen_id(self._ids()), layer, pos, start, end, title)
        self.data["clips"].append(clip)
        return clip

    def place_sequence(self, layer: int, items: list[dict], from_s: float = 0.0, snap: str = "beat",
                       default_beats: float = 4, allow_overlap: bool = False) -> list[dict]:
        """Lay items back-to-back; boundary k is frame F(n_k) = round(beat_time(n_k) * fps), never accumulated."""
        if self.grid is None:
            raise ValueError("no beat grid set; call analyze_music/set_grid first")
        g = self.grid
        n = Fraction(g.nearest_beat(from_s))
        out = []
        for it in items:
            beats = Fraction(str(it.get("beats", default_beats)))
            if beats <= 0:
                raise ValueError("beats must be positive")
            f0 = g.to_frame(g.beat_time_frac(n))
            f1 = g.to_frame(g.beat_time_frac(n + beats))
            pos, dur = g.frame_to_s(f0), g.frame_to_s(f1) - g.frame_to_s(f0)
            start = self._s(self._frame(it.get("start_s", 0.0)))
            f = self.file(it["file_id"])
            end = min(start + dur, float(f["duration"]))
            c = self.add_clip(it["file_id"], layer, pos, start, end, snap="none",
                              title=it.get("title"), allow_overlap=allow_overlap)
            out.append(c)
            n += beats
        return out

    def update_clip(self, clip_id: str, **kw) -> dict:
        c = self.clip(clip_id)
        f = self.file(c["file_id"])
        if kw.get("layer") is not None:
            self._layer_ok(kw["layer"])
            c["layer"] = int(kw["layer"])
        if kw.get("position_s") is not None:
            c["position"] = self._s(self._frame(kw["position_s"]))
        if kw.get("start_s") is not None:
            c["start"] = self._s(self._frame(kw["start_s"]))
        if kw.get("end_s") is not None:
            c["end"] = min(self._s(self._frame(kw["end_s"])), float(f["duration"]))
        if kw.get("title"):
            c["title"] = kw["title"]
        c["duration"] = c["end"] - c["start"]
        if c["duration"] <= 0:
            raise ValueError("clip would be empty")
        return c

    def remove_clip(self, clip_id: str) -> None:
        self.clip(clip_id)
        self.data["clips"] = [c for c in self.data["clips"] if c["id"] != clip_id]

    # ---- markers -----------------------------------------------------------
    def add_marker(self, position_s: float, title: str = "", color: str = "blue") -> dict:
        """OpenShot 4.0 markers are {id, position, icon, vector}. ``title`` is stored for the agent's
        benefit only; OpenShot does not display it. Only ``blue`` is verified to have an icon."""
        if color not in MARKER_COLORS:
            raise ValueError(f"color must be one of {MARKER_COLORS}")
        m = {"id": gen_id(self._ids()), "position": self._s(self._frame(position_s)),
             "icon": f"{color}.png", "vector": color}
        if title:
            m["title"] = title
        self.data["markers"].append(m)
        return m

    def clear_markers(self) -> int:
        n = len(self.data["markers"])
        self.data["markers"] = []
        return n

    # ---- inspection --------------------------------------------------------
    def timeline(self, layer: int | None = None) -> dict:
        rows = []
        for c in sorted(self.data["clips"], key=lambda c: (int(c["layer"]), c["position"])):
            if layer is not None and int(c["layer"]) != int(layer):
                continue
            rows.append({"id": c["id"], "title": c["title"], "layer": c["layer"], "position": c["position"],
                         "start": c["start"], "end": c["end"], "duration": c["duration"],
                         "ends_at": c["position"] + c["duration"], "file_id": c["file_id"]})
        gaps, overlaps = [], []
        by_layer: dict[int, list] = {}
        for r in rows:
            by_layer.setdefault(int(r["layer"]), []).append(r)
        for lay, rs in by_layer.items():
            for a, b in zip(rs, rs[1:]):
                d = b["position"] - a["ends_at"]
                if d > 1e-6:
                    gaps.append({"layer": lay, "after": a["id"], "gap_s": d})
                elif d < -1e-6:
                    overlaps.append({"layer": lay, "a": a["id"], "b": b["id"], "overlap_s": -d})
        return {"clips": rows, "gaps": gaps, "overlaps": overlaps,
                "markers": self.data["markers"],
                "end_s": max((r["ends_at"] for r in rows), default=0.0)}

    def validate(self) -> list[str]:
        problems = []
        ids = [x["id"] for k in ("files", "clips", "markers", "effects") for x in self.data.get(k, [])]
        if len(ids) != len(set(ids)):
            problems.append("duplicate ids")
        fids = {f["id"] for f in self.data["files"]}
        layers = {int(l["number"]) for l in self.data["layers"]}
        for c in self.data["clips"]:
            if c["file_id"] not in fids:
                problems.append(f"clip {c['id']} has dangling file_id {c['file_id']}")
                continue
            f = self.file(c["file_id"])
            for k in ("position", "start", "end", "duration"):
                v = c.get(k)
                if not isinstance(v, (int, float)) or v != v or v < 0:
                    problems.append(f"clip {c['id']} {k} is not a finite non-negative number")
            if c["start"] >= c["end"]:
                problems.append(f"clip {c['id']} start>=end")
            if c["end"] > float(f["duration"]) + 1e-6:
                problems.append(f"clip {c['id']} end {c['end']} exceeds file duration {f['duration']}")
            if int(c["layer"]) not in layers:
                problems.append(f"clip {c['id']} on unknown layer {c['layer']}")
            if abs(c["duration"] - (c["end"] - c["start"])) > 1e-6:
                problems.append(f"clip {c['id']} duration != end-start")
            if c.get("reader", {}).get("id") != c["file_id"]:
                problems.append(f"clip {c['id']} reader.id != file_id")
        for o in self.timeline()["overlaps"]:
            problems.append(f"overlap on layer {o['layer']}: {o['a']} / {o['b']} ({o['overlap_s']:.3f}s)")
        return problems
